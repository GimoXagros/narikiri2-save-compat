"""Package only the explicit FFR patch/applicator inventory, never a ROM."""
import argparse, hashlib, json, zipfile
from pathlib import Path
from apply_ffr_v09b import NAME, PATCH, SOURCE, TARGET

ROOT = Path(__file__).resolve().parents[1]
TEXT = {
    **{f'docs/history/v0.9a/{n}': f'docs/history/v0.9a/{n}' for n in ('README.md','BUILDING.md','VERIFICATION.md','RELEASE_NOTES.md','RELEASE_POLICY.md')},
    'docs/V05_RETIREMENT.md': 'docs/V05_RETIREMENT.md',
    'docs/BETA3_MIGRATION.md': 'docs/BETA3_MIGRATION.md',
    **{f'docs/history/v0.9/{n}': f'docs/history/v0.9/{n}' for n in ('README.md','BUILDING.md','VERIFICATION.md','RELEASE_NOTES.md','RELEASE_POLICY.md')},
    'apply_ffr_v09b.py': 'tools/apply_ffr_v09b.py',
    'bps.py': 'tools/bps.py',
    'README.md': 'README.md',
    'LICENSE': 'LICENSE',
    'RIGHTS.md': 'RIGHTS.md',
    'VERIFICATION.md': 'VERIFICATION.md',
    'RELEASE_NOTES.md': 'RELEASE_NOTES.md',
    'THIRD_PARTY_NOTICES.md': 'THIRD_PARTY_NOTICES.md',
    'BUILDING.md': 'BUILDING.md',
    'MIGRATION.md': 'MIGRATION.md',
    'RELEASE_POLICY.md': 'RELEASE_POLICY.md',
    'requirements-dev.txt': 'requirements-dev.txt',
    'docs/history/v0.5/README.md': 'docs/history/v0.5/README.md',
    'docs/history/v0.5/RIGHTS.md': 'docs/history/v0.5/RIGHTS.md',
    'docs/history/v0.5/VERIFICATION.md': 'docs/history/v0.5/VERIFICATION.md',
    'docs/history/v0.5/RELEASE_NOTES.md': 'docs/history/v0.5/RELEASE_NOTES.md',
    'third_party/dalmoori-font/LICENSE': 'third_party/dalmoori-font/LICENSE',
    'third_party/dalmoori-font/SOURCE_MANIFEST.json': 'third_party/dalmoori-font/SOURCE_MANIFEST.json',
    'verification/v0.9b.json': 'verification/v0.9b.json',
}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build-dir', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    a = p.parse_args()
    if a.output_dir.exists():
        raise ValueError('Choose a new package directory')
    manifest = json.loads((a.build_dir/'manifest.json').read_text(encoding='utf-8'))
    if (manifest['source_sha256'], manifest['target_sha256'], manifest['patch_sha256']) != (SOURCE, TARGET, PATCH):
        raise ValueError('Product manifest identity mismatch')
    gate = json.loads((ROOT/'verification/v0.9b.json').read_text(encoding='utf-8'))
    if not gate['release_ready'] or manifest['publication_status'] != 'VERIFIED_LOCAL_PRODUCT_NOT_PUBLISHED':
        raise ValueError('Unverified candidate cannot be packaged')
    if any(gate[k] != manifest[k] for k in ('target_sha256','patch_sha256','japanese_review')):
        raise ValueError('Verification gate identity mismatch')
    rom = (a.build_dir/(NAME+'.gba')).read_bytes()
    if len(rom) != manifest['target_size'] or digest(rom) != TARGET:
        raise ValueError('Local product ROM identity mismatch')
    patch_name = NAME + '_FROM_BETA3.bps'
    patch = (a.build_dir/patch_name).read_bytes()
    if digest(patch) != PATCH:
        raise ValueError('Patch hash mismatch')
    files = {patch_name: patch}
    for name, relative in TEXT.items():
        path = ROOT/relative
        if path.is_symlink():
            raise ValueError('Public input must not be a link')
        data = path.read_text(encoding='utf-8').replace('\r\n', '\n').encode('utf-8')
        if b'\0' in data:
            raise ValueError('Unexpected binary text input')
        files[name] = data
    manifest['package_files'] = {n: {'size': len(b), 'sha256': digest(b)} for n, b in files.items()}
    manifest['rom_included'] = False
    files['manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    files['SHA256SUMS.txt'] = ''.join(f'{digest(b)}  {n}\n' for n,b in sorted(files.items())).encode('ascii')
    a.output_dir.mkdir(parents=True)
    archive = a.output_dir/(NAME+'_BETA3_PACKAGE.zip')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 9, 7, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, data)
    with zipfile.ZipFile(archive) as z:
        if set(z.namelist()) != set(files) or any(z.read(n) != b for n,b in files.items()):
            raise ValueError('ZIP read-back mismatch')
    for name in (patch_name, 'manifest.json'):
        (a.output_dir/name).write_bytes(files[name])
    assets = {f.name: {'size': f.stat().st_size, 'sha256': digest(f.read_bytes())} for f in a.output_dir.iterdir()}
    (a.output_dir/'SHA256SUMS.txt').write_text(''.join(f"{v['sha256']}  {n}\n" for n,v in sorted(assets.items())), encoding='ascii')
    print(json.dumps({'rom_included': False, 'assets': assets}, indent=2))

if __name__ == '__main__':
    main()
