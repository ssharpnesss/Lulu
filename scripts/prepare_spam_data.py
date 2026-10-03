"""Build reproducible text-only, template-disjoint train/validation/test splits."""
import collections
import hashlib
import json
import random
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def template(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    fallback = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'https?://\S+|(?:t\.me/|www\.)\S+', ' URL ', text)
    text = re.sub(r'@[\w]+', ' USER ', text)
    text = re.sub(r'\d+', ' NUM ', text)
    return re.sub(r'[\W_]+', ' ', text).strip() or fallback


def main():
    groups = {}
    counts = {}
    sources = [('result.json', 'text', 0), ('info_result.json', 'spam', 1)]
    for filename, field, label in sources:
        path = ROOT / filename
        records = json.loads(path.read_text(encoding='utf-8'))
        counts[filename] = {'raw': len(records), 'empty': 0,
                            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        for record_id, row in records.items():
            text = row.get(field)
            if not isinstance(text, str) or not text.strip():
                counts[filename]['empty'] += 1
                continue
            key = template(text)
            if not key:
                counts[filename]['empty'] += 1
                continue
            # Retain one original text per template, not the normalized text.
            if key not in groups:
                groups[key] = {'text': text.strip(), 'label': label,
                               'source': filename, 'id': record_id,
                               'group': hashlib.sha256(key.encode()).hexdigest()}
            elif groups[key]['label'] != label:
                groups[key]['label'] = -1
    conflict_count = sum(r['label'] == -1 for r in groups.values())
    splits = {s: [] for s in ['train', 'validation', 'test']}
    for row in groups.values():
        if row['label'] == -1:
            continue
        bucket = int(row['group'][:8], 16) % 100
        split = 'test' if bucket < 10 else 'validation' if bucket < 20 else 'train'
        splits[split].append(row)
    rng = random.Random(42)
    # Fixed balanced subsets make this local GPU run practical and comparisons interpretable.
    limits = {'train': 12000, 'validation': 2000, 'test': 4000}
    audit = {'sources': counts, 'conflicting_templates_removed': conflict_count,
             'templates_before_conflict_removal': len(groups), 'seed': 42, 'splits': {}}
    output = ROOT / 'training/data'
    output.mkdir(parents=True, exist_ok=True)
    for split, rows in splits.items():
        available = collections.Counter(r['label'] for r in rows)
        chosen = []
        for label in [0, 1]:
            candidates = sorted((r for r in rows if r['label'] == label), key=lambda r:r['group'])
            rng.shuffle(candidates)
            chosen.extend(candidates[:limits[split] // 2])
        rng.shuffle(chosen)
        audit['splits'][split] = {'available': dict(available), 'selected': dict(collections.Counter(r['label'] for r in chosen))}
        with (output / f'{split}.jsonl').open('w', encoding='utf-8') as f:
            for row in chosen:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
    assert not ({r['group'] for r in splits['train']} & {r['group'] for r in splits['test']})
    (ROOT / 'training/data_audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    print(json.dumps(audit, indent=2), flush=True)


if __name__ == '__main__':
    main()
