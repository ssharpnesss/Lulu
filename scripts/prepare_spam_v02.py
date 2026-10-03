"""Prepare deterministic, template-disjoint text-only data from three local sources."""
import collections
import hashlib
import json
import random
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'training/v02'


def template(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    text = ''.join(c for c in text if unicodedata.category(c) != 'Cf')
    fallback = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'https?://\S+|(?:t\.me/|www\.)\S+', ' URL ', text)
    text = re.sub(r'@\w+', ' USER ', text)
    text = re.sub(r'\d+', ' NUM ', text)
    return re.sub(r'[\W_]+', ' ', text).strip() or fallback


def main():
    groups = {}
    audit = {'seed': 42, 'sources': {}, 'splits': {}}
    for name, field, label in [('result.json','text',0), ('data_result.json','messages',0), ('info_result.json','spam',1)]:
        raw = (ROOT/name).read_bytes()
        obj = json.loads(raw)
        if name == 'data_result.json':
            records = enumerate(obj[field])
            count = len(obj[field])
        else:
            records = ((key, row[field]) for key, row in obj.items())
            count = len(obj)
        stats = {'raw':count, 'empty':0, 'sha256':hashlib.sha256(raw).hexdigest()}
        for record_id, text in records:
            if not isinstance(text,str):
                raise TypeError(f'{name}: non-string message {record_id}')
            key = template(text)
            if not key:
                stats['empty'] += 1
                continue
            if key not in groups:
                groups[key] = {'text':text.strip(), 'label':label, 'source':name, 'id':str(record_id),
                               'group':hashlib.sha256(key.encode()).hexdigest()}
            elif groups[key]['label'] != label:
                groups[key]['label'] = -1
        audit['sources'][name] = stats
    audit['conflicting_groups_removed'] = sum(r['label']==-1 for r in groups.values())
    audit['usable_unique_groups'] = len(groups)-audit['conflicting_groups_removed']
    splits = {s:[] for s in ['train','validation','test']}
    for row in groups.values():
        if row['label'] == -1:
            continue
        bucket = int(row['group'][:8],16)%100
        split = 'test' if bucket<10 else 'validation' if bucket<20 else 'train'
        splits[split].append(row)
    rng = random.Random(42)
    limits = {'train':40000,'validation':4000,'test':10000}
    (OUT/'data').mkdir(parents=True,exist_ok=True)
    selected_groups = {}
    for split, rows in splits.items():
        chosen = []
        for label in [0,1]:
            candidates = sorted((r for r in rows if r['label']==label),key=lambda r:r['group'])
            rng.shuffle(candidates)
            assert len(candidates)>=limits[split]//2
            chosen.extend(candidates[:limits[split]//2])
        rng.shuffle(chosen)
        selected_groups[split] = {r['group'] for r in chosen}
        audit['splits'][split] = {'available_by_label':dict(collections.Counter(r['label'] for r in rows)),
                                  'selected_by_label':dict(collections.Counter(r['label'] for r in chosen)),
                                  'selected_by_source':dict(collections.Counter(r['source'] for r in chosen))}
        with (OUT/f'data/{split}.jsonl').open('w',encoding='utf-8') as f:
            for row in chosen:
                f.write(json.dumps(row,ensure_ascii=False)+'\n')
    for a,b in [('train','validation'),('train','test'),('validation','test')]:
        assert not selected_groups[a]&selected_groups[b]
    (OUT/'data_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(json.dumps(audit,indent=2),flush=True)


if __name__ == '__main__':
    main()
