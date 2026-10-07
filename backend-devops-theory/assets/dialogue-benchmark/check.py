#!/usr/bin/env python3
"""Validate transcript completeness, not pedagogical correctness."""
import argparse
import hashlib
import json
from pathlib import Path


def check(path):
    prompts = json.loads((Path(__file__).parent / 'prompts.json').read_text())
    errors = []
    hashes = {}
    for expected in prompts:
        file = path / f'{expected["turn"]:02}.json'
        if not file.is_file():
            errors.append(f'missing turn {expected["turn"]}'); continue
        data = json.loads(file.read_text())
        if data.get('turn') != expected['turn'] or data.get('prompt') != expected['prompt']:
            errors.append(f'prompt mismatch {file.name}')
        if not isinstance(data.get('response'), str) or not data['response'].strip():
            errors.append(f'empty response {file.name}')
        if set(data.get('snapshot', {})) != {'PROGRESS.md', 'NOTES.md'}:
            errors.append(f'incomplete snapshot {file.name}')
        hashes[file.name] = hashlib.sha256(file.read_bytes()).hexdigest()
    return {'transcript_complete': not errors, 'errors': errors, 'turns': len(hashes),
            'sha256': hashes, 'semantic_assessment': 'required separately; not computed here'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    args = parser.parse_args()
    report = check(args.path)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['transcript_complete'] else 1)
