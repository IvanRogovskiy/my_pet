#!/usr/bin/env python3
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import sys
import uuid

import stand
from templates import ASSIGNMENTS, BAD, GOOD


def safe(root, name):
    p = root / name
    if p.is_symlink() or (p.exists() and p.is_file() and p.stat().st_nlink != 1):
        raise ValueError('unsafe file: ' + name)
    if root.resolve() not in p.resolve().parents:
        raise ValueError('path escaped workspace')
    return p


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['prepare', 'check', 'reference', 'reset', 'audit'])
    p.add_argument('root', type=Path)
    p.add_argument('--case', choices=list(BAD))
    p.add_argument('--stand', type=Path)
    a = p.parse_args()
    try:
        if a.action == 'audit':
            if not a.stand: p.error('--stand required')
            if a.root.exists() or a.root.is_symlink(): raise ValueError('audit requires a new directory')
            a.root.mkdir(parents=True, mode=0o700)
            result = {}
            for case in ([a.case] if a.case else BAD):
                target = a.root / case
                subprocess.run([sys.executable, __file__, 'prepare', target, '--case', case], check=True)
                result[case] = []
                for variant in ('broken', 'reference', 'reset'):
                    if variant != 'broken':
                        subprocess.run([sys.executable, __file__, variant, target], check=True)
                    with stand.lock(a.stand):
                        code = stand.run(a.stand, stand.load(a.stand), target.resolve(), case)
                    result[case].append(code)
                print(json.dumps({'case': case, 'exits': result[case]}), flush=True)
            (a.root / 'audit.json').write_text(json.dumps(result, indent=2)+'\n')
            return 0 if all(v == [1,0,1] for v in result.values()) else 1
        if a.action == 'prepare':
            if not a.case: p.error('--case required')
            if a.root.exists() or a.root.is_symlink(): raise ValueError('requires a new directory')
            a.root.mkdir(parents=True, mode=0o700)
            state = {'case': a.case, 'id': uuid.uuid4().hex, 'root': str(a.root.resolve())}
            safe(a.root, 'lab.json').write_text(json.dumps(state))
            safe(a.root, 'submission.py').write_text(BAD[a.case])
            safe(a.root, 'evidence').mkdir()
            safe(a.root, 'ASSIGNMENT.md').write_text(f'# {a.case} — {ASSIGNMENTS[a.case][0]}\n\n{ASSIGNMENTS[a.case][1]}\n')
            return 0
        if a.root.is_symlink(): raise ValueError('symlink root refused')
        state = json.loads(safe(a.root, 'lab.json').read_text())
        if state['root'] != str(a.root.resolve()) or state['case'] not in BAD: raise ValueError('wrong workspace')
        with stand.lock(a.root):
            if a.action in ('reference', 'reset'):
                safe(a.root, 'submission.py').write_text((GOOD if a.action == 'reference' else BAD)[state['case']])
                return 0
            if not a.stand: p.error('--stand required')
            safe(a.root, 'submission.py')
            safe(a.root, 'evidence').mkdir(exist_ok=True)
            with stand.lock(a.stand):
                return stand.run(a.stand, stand.load(a.stand), a.root.resolve(), state['case'])
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr); return 2


if __name__ == '__main__':
    raise SystemExit(main())
