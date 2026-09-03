"""Package an explicit UTF-8 source-only inventory; never traverse local outputs."""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from restore import V05, digest

PUBLIC_FILES = (
    '.gitattributes', '.gitignore', 'LICENSE', 'README.md', 'RIGHTS.md',
    'CHANGELOG.md', 'RELEASE_NOTES.md', 'VERIFICATION.md', 'restore.py',
    'tests/test_restore.py', 'tools/verify_local.py', 'tools/package_release.py',
    'verification/v0.5.json',
)


def source_inventory():
    result = {}
    for name in PUBLIC_FILES:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing or symlinked public source: ' + name)
        data = path.read_text(encoding='utf-8').replace('\r\n', '\n').encode('utf-8')
        if b'\0' in data or len(data) > 100_000:
            raise ValueError('Non-text or oversized source: ' + name)
        if path.suffix == '.py':
            for node in ast.walk(ast.parse(data, filename=name)):
                if isinstance(node, ast.Constant) and isinstance(node.value, bytes) and len(node.value) > 32:
                    raise ValueError('Unexpected embedded byte array: ' + name)
        result[name] = data
    result['SHA256SUMS'] = ''.join(f'{digest(data)}  {name}\n' for name, data in sorted(result.items())).encode('ascii')
    return result


def make_zip(members):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 3, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return stream.getvalue()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--korean', type=Path, required=True)
    parser.add_argument('--japanese', type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise ValueError('Choose a new local output directory')
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
    log = io.StringIO()
    tests = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    if not tests.wasSuccessful() or tests.skipped or tests.testsRun == 0:
        raise RuntimeError(log.getvalue())
    members = source_inventory()
    encoded = make_zip(members)
    if make_zip(members) != encoded:
        raise RuntimeError('Non-deterministic ZIP')
    args.output_dir.mkdir(parents=True)
    unpacked = args.output_dir / 'private-application-check'
    unpacked.mkdir()
    with zipfile.ZipFile(io.BytesIO(encoded)) as archive:
        if archive.testzip() is not None or set(archive.namelist()) != set(members):
            raise RuntimeError('ZIP integrity failed')
        for name, expected in members.items():
            data = archive.read(name)
            if data != expected:
                raise RuntimeError('ZIP member mismatch')
            path = unpacked / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    sums = (unpacked / 'SHA256SUMS').read_text(encoding='ascii').splitlines()
    for line in sums:
        expected, name = line.split('  ', 1)
        if digest((unpacked / name).read_bytes()) != expected:
            raise RuntimeError('Packaged source checksum mismatch')
    output_rom = unpacked / 'local-only.gba'
    command = [sys.executable, '-X', 'utf8', str(unpacked / 'restore.py'),
               '--korean', str(args.korean.resolve()), '--japanese', str(args.japanese.resolve()),
               '--output', str(output_rom.resolve())]
    process = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
    if process.returncode or digest(output_rom.read_bytes()) != V05.result.sha256:
        raise RuntimeError('Packaged CLI failed: ' + process.stderr)
    blocked = subprocess.run(command, capture_output=True)
    if blocked.returncode == 0 or digest(output_rom.read_bytes()) != V05.result.sha256:
        raise RuntimeError('Packaged output overwrite protection failed')
    name = 'NARIKIRI2_SAVE_COMPAT_v0.5_SOURCE_ONLY.zip'
    (args.output_dir / name).write_bytes(encoded)
    (args.output_dir / 'SHA256SUMS').write_text(f'{digest(encoded)}  {name}\n', encoding='ascii')
    report = {'version': '0.5', 'zip': name, 'sha256': digest(encoded), 'size': len(encoded),
              'members': sorted(members), 'source_files': len(PUBLIC_FILES),
              'tests_passed': tests.testsRun, 'tests_skipped': len(tests.skipped),
              'two_archives_identical': True, 'packaged_cli_output_sha256': V05.result.sha256,
              'packaged_cli_overwrite_blocked': True,
              'all_members_utf8_text': True, 'game_or_patch_binaries_in_archive': False}
    (args.output_dir / 'package_verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
