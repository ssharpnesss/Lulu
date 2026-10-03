"""Local fine-tuning and paired evaluation; never overwrite the source model."""
import argparse
import hashlib
import json
import math
import os
import random
import time
from pathlib import Path

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
import numpy as np
import torch
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'assets/ruspam_model'
OUT = ROOT / 'assets/ruspam_model_finetuned'
REPORT = ROOT / 'training'


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def metrics(y, probs):
    pred = (np.asarray(probs) >= .5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    n = len(y)
    acc = accuracy_score(y, pred)
    z = 1.96
    center = (acc + z*z/(2*n))/(1+z*z/n)
    half = z*math.sqrt(acc*(1-acc)/n+z*z/(4*n*n))/(1+z*z/n)
    return {'n': n, 'accuracy': float(acc), 'accuracy_wilson_95': [center-half, center+half],
            'spam_precision': float(precision_score(y, pred, zero_division=0)),
            'spam_recall': float(recall_score(y, pred, zero_division=0)),
            'spam_f1': float(f1_score(y, pred, zero_division=0)),
            'roc_auc': float(roc_auc_score(y, probs)),
            'false_positive_rate': float(fp/(tn+fp)), 'tn':int(tn), 'fp':int(fp), 'fn':int(fn), 'tp':int(tp)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', type=int, default=1)
    parser.add_argument('--batch-size', type=int, default=4)
    parser.add_argument('--max-length', type=int, default=256)
    args = parser.parse_args()
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    torch.set_num_threads(4)
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA GPU required for this local training run')
    device = 'cuda'
    tokenizer = AutoTokenizer.from_pretrained(BASE, local_files_only=True)
    model, loading = AutoModelForSequenceClassification.from_pretrained(BASE, local_files_only=True, output_loading_info=True)
    if loading['missing_keys'] or loading['unexpected_keys'] or loading.get('mismatched_keys'):
        raise RuntimeError(f'Checkpoint did not load exactly: {loading}')
    model.to(device)
    rows = {split: [json.loads(line) for line in (REPORT / f'data/{split}.jsonl').read_text(encoding='utf-8').splitlines()]
            for split in ['train', 'validation', 'test']}
    group_sets = {s: {r['group'] for r in rr} for s, rr in rows.items()}
    assert not group_sets['train'] & group_sets['validation']
    assert not group_sets['train'] & group_sets['test']
    assert not group_sets['validation'] & group_sets['test']
    encoded = {}
    truncation = {}
    for split, rr in rows.items():
        enc = tokenizer([r['text'] for r in rr], truncation=False)
        truncation[split] = sum(len(ids)>args.max_length for ids in enc['input_ids'])
        encoded[split] = tokenizer([r['text'] for r in rr], truncation=True, max_length=args.max_length)
    def batch(split, indices):
        features = [{k:v[i] for k,v in encoded[split].items()} for i in indices]
        return {k:v.to(device) for k,v in tokenizer.pad(features, padding=True, return_tensors='pt').items()}
    def predict(split, spam_index):
        model.eval()
        probs = np.zeros(len(rows[split]), dtype=np.float64)
        order = sorted(range(len(rows[split])), key=lambda i:len(encoded[split]['input_ids'][i]))
        started = time.time()
        with torch.inference_mode():
            for start in range(0, len(rows[split]), 16):
                ids = order[start:start+16]
                inputs = batch(split, ids)
                logits = model(**inputs).logits.float()
                probs[ids] = logits.softmax(-1)[:,spam_index].cpu().numpy()
                if start and start % 1024 == 0:
                    print(f'eval {split} {start}/{len(rows[split])} elapsed={time.time()-started:.0f}s', flush=True)
        if not np.isfinite(probs).all():
            raise RuntimeError('Nonfinite predictions')
        return probs.tolist()
    labels = {s: np.array([r['label'] for r in rr]) for s, rr in rows.items()}
    # Original config has no semantic label names: infer orientation using validation only.
    initial_val = predict('validation', 1)
    spam_index = 1 if roc_auc_score(labels['validation'], initial_val) >= .5 else 0
    base_val_probs = np.array(initial_val) if spam_index == 1 else 1-np.array(initial_val)
    base_val = metrics(labels['validation'], base_val_probs)
    print('baseline validation', json.dumps(base_val), 'spam_index',spam_index,flush=True)
    baseline_probs = predict('test', spam_index)
    baseline = metrics(labels['test'], baseline_probs)
    save_json(REPORT / 'baseline.json', {'validation':base_val,'test':baseline,'spam_index':spam_index})
    print('baseline test',json.dumps(baseline),flush=True)
    model.config.id2label = {spam_index:'spam', 1-spam_index:'ham'}
    model.config.label2id = {'spam':spam_index, 'ham':1-spam_index}
    model.gradient_checkpointing_enable()
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5, weight_decay=.01)
    accumulation = max(1,16//args.batch_size)
    steps_per_epoch = math.ceil(math.ceil(len(rows['train'])/args.batch_size)/accumulation)
    scheduler = get_linear_schedule_with_warmup(optimizer, max(1,steps_per_epoch*args.epochs//10), steps_per_epoch*args.epochs)
    best_f1 = -1.
    history = []
    started = time.time()
    optimizer.zero_grad(set_to_none=True)
    for epoch in range(args.epochs):
        indices = np.random.permutation(len(rows['train']))
        # Random local length buckets minimize padding while mixing both classes.
        indices = np.concatenate([sorted(indices[i:i+64], key=lambda j:len(encoded['train']['input_ids'][j]))
                                  for i in range(0,len(indices),64)])
        model.train()
        losses = []
        batches = math.ceil(len(indices)/args.batch_size)
        for bi, start in enumerate(range(0,len(indices),args.batch_size)):
            ids = indices[start:start+args.batch_size]
            inputs = batch('train',ids)
            target = labels['train'][ids] if spam_index == 1 else 1-labels['train'][ids]
            loss = model(**inputs, labels=torch.tensor(target,device=device)).loss
            if not torch.isfinite(loss):
                raise RuntimeError('Nonfinite loss')
            losses.append(loss.item())
            (loss/accumulation).backward()
            if (bi+1)%accumulation == 0 or bi+1 == batches:
                torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
            if (bi+1)%50 == 0:
                print(f'epoch={epoch+1} samples={min(start+args.batch_size,len(indices))}/{len(indices)} loss={np.mean(losses[-50:]):.4f} elapsed={time.time()-started:.0f}s gpu_peak_mb={torch.cuda.max_memory_allocated()/1024**2:.0f}',flush=True)
            if (bi+1)%750 == 0 or bi+1 == batches:
                val = metrics(labels['validation'],predict('validation',spam_index))
                entry = {'epoch':epoch+1,'samples':min(start+args.batch_size,len(indices)), 'validation':val}
                history.append(entry)
                save_json(REPORT / 'history.json',history)
                print('validation',json.dumps(entry),flush=True)
                if val['spam_f1'] > best_f1:
                    best_f1 = val['spam_f1']
                    model.save_pretrained(OUT)
                    tokenizer.save_pretrained(OUT)
                model.train()
    del optimizer, scheduler, model
    torch.cuda.empty_cache()
    model = AutoModelForSequenceClassification.from_pretrained(OUT,local_files_only=True).to(device)
    tuned_probs = predict('test',spam_index)
    tuned = metrics(labels['test'],tuned_probs)
    base_correct = (np.array(baseline_probs)>=.5) == labels['test']
    tuned_correct = (np.array(tuned_probs)>=.5) == labels['test']
    result = {'baseline':baseline, 'finetuned':tuned, 'accuracy_change_percentage_points':100*(tuned['accuracy']-baseline['accuracy']),
              'paired':{'fixed_errors':int((~base_correct&tuned_correct).sum()),'new_errors':int((base_correct&~tuned_correct).sum())},
              'settings':vars(args)|{'seed':42,'learning_rate':2e-5,'effective_batch':accumulation*args.batch_size,'spam_index':spam_index,
              'device':torch.cuda.get_device_name(),'precision':'float32','selection':'best validation spam F1 at fixed 0.5 threshold', 'truncated_messages':truncation},
              'training_seconds':time.time()-started, 'history':history,
              'source_model_sha256':hashlib.sha256((BASE/'model.safetensors').read_bytes()).hexdigest()}
    save_json(REPORT/'comparison.json',result)
    with (REPORT/'data/test_predictions.jsonl').open('w',encoding='utf-8') as f:
        for row,b,t in zip(rows['test'],baseline_probs,tuned_probs):
            f.write(json.dumps(row|{'baseline_spam_probability':b,'finetuned_spam_probability':t},ensure_ascii=False)+'\n')
    print('RESULT',json.dumps(result),flush=True)


if __name__ == '__main__':
    main()
