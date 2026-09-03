"""Verify exact local inputs without exporting their contents or filenames."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from restore import V05, check_image, digest, restore_files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--korean', type=Path, required=True)
    parser.add_argument('--japanese', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True, help='Locally retained verified v0.5 ROM')
    parser.add_argument('--work-dir', type=Path, required=True, help='NEW private local directory')
    args = parser.parse_args()
    baseline = args.baseline.read_bytes()
    check_image(baseline, V05.result, 'Verification baseline')
    args.work_dir.mkdir(parents=True, exist_ok=False)
    reports = []
    for name in ('first.gba', 'second.gba'):
        path = args.work_dir / name
        reports.append(restore_files(args.korean, args.japanese, path))
        if path.read_bytes() != baseline:
            raise RuntimeError('Full output does not equal the runtime-verified baseline')
    if reports[0] != reports[1]:
        raise RuntimeError('Build reports differ')
    if digest(args.korean.read_bytes()) != V05.korean.sha256 or digest(args.japanese.read_bytes()) != V05.japanese.sha256:
        raise RuntimeError('Inputs changed')
    report = {'version': '0.5', 'python': sys.version.split()[0],
              'korean_sha256': V05.korean.sha256, 'japanese_sha256': V05.japanese.sha256,
              **reports[0], 'two_local_builds_identical': True,
              'byte_identical_to_runtime_verified_baseline': True, 'inputs_unchanged': True,
              'new_runtime_test': False,
              'runtime_basis': 'Existing v0.5 evidence transferred only through full byte identity'}
    (args.work_dir / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
