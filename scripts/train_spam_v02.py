"""Fine-tune the local v0.2 checkpoint and compare it with its unchanged source."""
import argparse
import collections
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
BASE = ROOT/'assets/spam-detector-v0.2'
OUT = ROOT/'assets/spam-detector-v0.2-finetuned'
REPORT = ROOT/'training/v02'


def save(path, value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def metrics(y, probs):
    pred = np.asarray(probs)>=.5
    tn,fp,fn,tp = confusion_matrix(y,pred,labels=[0,1]).ravel()
    acc = float(accuracy_score(y,pred))
    n,z = len(y),1.96
    center = (acc+z*z/(2*n))/(1+z*z/n)
    half = z*math.sqrt(acc*(1-acc)/n+z*z/(4*n*n))/(1+z*z/n)
    return {'n':n,'accuracy':acc,'accuracy_wilson_95':[center-half,center+half],
            'spam_precision':float(precision_score(y,pred,zero_division=0)),
            'spam_recall':float(recall_score(y,pred,zero_division=0)),
            'spam_f1':float(f1_score(y,pred,zero_division=0)),
            'roc_auc':float(roc_auc_score(y,probs)), 'false_positive_rate':float(fp/(tn+fp)),
            'tn':int(tn),'fp':int(fp),'fn':int(fn),'tp':int(tp)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs',type=int,default=1)
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error('epochs must be positive')
    if OUT.exists():
        raise RuntimeError(f'Output already exists; preserve or move it before another run: {OUT}')
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    torch.set_num_threads(4)
    if not torch.cuda.is_available():
        raise RuntimeError('This run requires CUDA')
    source_hashes = {p.name:sha(p) for p in BASE.iterdir() if p.is_file()}
    save(REPORT/'source_hashes.json',source_hashes)
    tokenizer = AutoTokenizer.from_pretrained(BASE,local_files_only=True)
    model, loading = AutoModelForSequenceClassification.from_pretrained(BASE,local_files_only=True,output_loading_info=True)
    assert not any(loading.get(k) for k in ['missing_keys','unexpected_keys','mismatched_keys','error_msgs']),loading
    assert model.config.num_labels==2
    model.to('cuda')
    rows = {s:[json.loads(line) for line in (REPORT/f'data/{s}.jsonl').read_text(encoding='utf-8').splitlines()]
            for s in ['train','validation','test']}
    encoded = {s:tokenizer([r['text'] for r in rr],truncation=True,max_length=256) for s,rr in rows.items()}
    # Also exclude identical model inputs caused by tokenization or truncation.
    owners = collections.defaultdict(set)
    for s,rr in rows.items():
        for row,ids in zip(rr,encoded[s]['input_ids']):
            owners[tuple(ids)].add((s,row['label']))
    data_stats = {}
    for s,rr in rows.items():
        seen,keep = set(),[]
        for i,ids in enumerate(encoded[s]['input_ids']):
            signature = tuple(ids)
            if len(owners[signature])==1 and signature not in seen:
                keep.append(i)
                seen.add(signature)
        data_stats[s] = {'excluded_token_collisions':len(rr)-len(keep)}
        rows[s] = [rr[i] for i in keep]
        encoded[s] = {k:[v[i] for i in keep] for k,v in encoded[s].items()}
        lengths = tokenizer([r['text'] for r in rows[s]],truncation=False,verbose=False)['input_ids']
        data_stats[s].update({'n':len(keep),'by_label':dict(collections.Counter(r['label'] for r in rows[s])),
                             'by_source':dict(collections.Counter(r['source'] for r in rows[s])),
                             'truncated':sum(len(ids)>256 for ids in lengths)})
        with (REPORT/f'data/{s}_effective.jsonl').open('w',encoding='utf-8') as f:
            for row in rows[s]:
                f.write(json.dumps(row,ensure_ascii=False)+'\n')
    for a,b in [('train','validation'),('train','test'),('validation','test')]:
        assert not {r['group'] for r in rows[a]} & {r['group'] for r in rows[b]}
        assert not set(map(tuple,encoded[a]['input_ids'])) & set(map(tuple,encoded[b]['input_ids']))
    save(REPORT/'effective_data.json',data_stats)
    print('DATA',json.dumps(data_stats),flush=True)
    labels = {s:np.array([r['label'] for r in rr]) for s,rr in rows.items()}
    def batch(split,ids):
        features = [{k:v[i] for k,v in encoded[split].items()} for i in ids]
        return {k:v.to('cuda') for k,v in tokenizer.pad(features,padding=True,return_tensors='pt').items()}
    def predict(split,spam_index):
        model.eval()
        probs = np.empty(len(rows[split]),dtype=np.float64)
        order = sorted(range(len(probs)),key=lambda i:len(encoded[split]['input_ids'][i]))
        with torch.inference_mode():
            for start in range(0,len(order),16):
                ids = order[start:start+16]
                probs[ids] = model(**batch(split,ids)).logits.softmax(-1)[:,spam_index].cpu().numpy()
        assert np.isfinite(probs).all()
        return probs
    initial_val = predict('validation',1)
    # Semantic labels are absent from the source config. Resolve on validation only.
    spam_index = 1 if roc_auc_score(labels['validation'],initial_val)>=.5 else 0
    baseline_val = metrics(labels['validation'],initial_val if spam_index==1 else 1-initial_val)
    baseline_probs = predict('test',spam_index)
    baseline = metrics(labels['test'],baseline_probs)
    save(REPORT/'baseline.json',{'validation':baseline_val,'test':baseline,'spam_index':spam_index})
    print('BASELINE VALIDATION',json.dumps(baseline_val),'spam_index',spam_index,flush=True)
    model.config.id2label = {spam_index:'spam',1-spam_index:'ham'}
    model.config.label2id = {'spam':spam_index,'ham':1-spam_index}
    best = {'epoch':0,'samples':0,'validation':{'spam_f1':-1.0}}
    model.gradient_checkpointing_enable()
    optimizer = torch.optim.AdamW(model.parameters(),lr=2e-5,weight_decay=.01)
    batches = math.ceil(len(rows['train'])/4)
    steps = math.ceil(batches/4)*args.epochs
    scheduler = get_linear_schedule_with_warmup(optimizer,max(1,steps//10),steps)
    optimizer.zero_grad(set_to_none=True)
    history = []
    started = time.monotonic()
    for epoch in range(args.epochs):
        order = np.random.permutation(len(rows['train']))
        order = np.concatenate([sorted(order[i:i+64],key=lambda j:len(encoded['train']['input_ids'][j]))
                                for i in range(0,len(order),64)])
        model.train()
        losses = []
        for bi,start in enumerate(range(0,len(order),4)):
            ids = order[start:start+4]
            target = labels['train'][ids] if spam_index==1 else 1-labels['train'][ids]
            loss = model(**batch('train',ids),labels=torch.tensor(target,device='cuda')).loss
            if not torch.isfinite(loss):
                raise RuntimeError('Nonfinite loss')
            # Correct weighting even for an incomplete final accumulation window.
            window_start = (bi//4)*16
            window_size = min(16,len(order)-window_start)
            (loss*len(ids)/window_size).backward()
            losses.append(loss.item())
            if (bi+1)%4==0 or bi+1==batches:
                torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
            if (bi+1)%125==0:
                progress = {'epoch':epoch+1,'samples':start+len(ids),'total':len(order),
                            'loss':float(np.mean(losses[-125:])),'elapsed_seconds':round(time.monotonic()-started)}
                save(REPORT/'progress.json',progress)
                print('PROGRESS',json.dumps(progress),flush=True)
            # Evaluate only after an optimizer step (5,008 examples per interval).
            if (bi+1)%1252==0 or bi+1==batches:
                val = metrics(labels['validation'],predict('validation',spam_index))
                entry = {'epoch':epoch+1,'samples':start+len(ids),'validation':val}
                history.append(entry)
                if val['spam_f1']>best['validation']['spam_f1']:
                    best = entry
                    model.save_pretrained(OUT)
                    tokenizer.save_pretrained(OUT)
                save(REPORT/'history.json',history)
                save(REPORT/'best_checkpoint.json',best)
                print('VALIDATION',json.dumps(entry),flush=True)
                model.train()
    del optimizer,scheduler,model
    torch.cuda.empty_cache()
    model = AutoModelForSequenceClassification.from_pretrained(OUT,local_files_only=True).to('cuda')
    tuned_probs = predict('test',spam_index)
    tuned = metrics(labels['test'],tuned_probs)
    old_ok = (baseline_probs>=.5)==labels['test']
    new_ok = (tuned_probs>=.5)==labels['test']
    by_source = {}
    for source in sorted({r['source'] for r in rows['test']}):
        mask = np.array([r['source']==source for r in rows['test']])
        by_source[source] = {'n':int(mask.sum()),'label':int(labels['test'][mask][0]),
                             'baseline_errors':int((~old_ok[mask]).sum()),
                             'finetuned_errors':int((~new_ok[mask]).sum()),
                             'baseline_accuracy':float(old_ok[mask].mean()),
                             'finetuned_accuracy':float(new_ok[mask].mean())}
    # Bootstrap the paired accuracy difference, not two independent samples.
    delta = new_ok.astype(int)-old_ok.astype(int)
    rng = np.random.default_rng(42)
    delta_ci = np.quantile([rng.choice(delta,len(delta),replace=True).mean()*100 for _ in range(2000)],[.025,.975]).tolist()
    assert source_hashes=={p.name:sha(p) for p in BASE.iterdir() if p.is_file()}
    result = {'baseline':baseline,'finetuned':tuned,'accuracy_change_percentage_points':100*(tuned['accuracy']-baseline['accuracy']),
              'paired_change_95_bootstrap_pp':delta_ci,
              'paired':{'fixed_errors':int((~old_ok&new_ok).sum()),'new_errors':int((old_ok&~new_ok).sum())},
              'best_checkpoint':best,'data':data_stats,'by_source':by_source,'history':history,'source_unchanged':True,
              'source_weights_sha256':source_hashes['model.safetensors'],'output_weights_sha256':sha(OUT/'model.safetensors'),
              'settings':{'epochs':args.epochs,'seed':42,'max_length':256,'batch_size':4,'effective_batch':16,
                          'learning_rate':2e-5,'weight_decay':.01,'warmup_fraction':.1,'precision':'float32',
                          'spam_index':spam_index,'threshold':.5,'selection':'validation spam F1',
                          'device':torch.cuda.get_device_name(),'torch':torch.__version__},
              'training_and_final_evaluation_seconds':time.monotonic()-started}
    with (REPORT/'data/test_predictions.jsonl').open('w',encoding='utf-8') as f:
        for row,b,t in zip(rows['test'],baseline_probs,tuned_probs):
            f.write(json.dumps(row|{'baseline_spam_probability':float(b),'finetuned_spam_probability':float(t)},ensure_ascii=False)+'\n')
    save(REPORT/'comparison.json',result)
    print('RESULT',json.dumps(result),flush=True)


if __name__ == '__main__':
    main()
