"""Reproduce the frozen v0.9 ROM and cumulative BPS from the exact FFR input."""
import argparse,hashlib,json
from pathlib import Path
from build_banked_font import ROOT,FFR_HASH,SOURCE_SIZE,collect,prepare_fonts,build
from save_fix_spec import EXPECTED_WRITES,EXPECTED_OUTPUT_SHA256
from bps import create_bps,apply_bps

NAME='NARIKIRI2_AN9J_K_DALMOORI_v0.9'
TARGET_HASH='560535ba5dce7246a4c1b210a082b93a08091b8f9e2bfa96467e44adbbf65c81'
PATCH_HASH='38cba8fbf0fee41af02859df1a607eda2dbedee17f37afbb05fac05316449866'
def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    gate=json.loads((ROOT/'verification/v0.9.json').read_text(encoding='utf-8'))
    if not gate['release_ready'] or gate['target_sha256']!=TARGET_HASH or gate['patch_sha256']!=PATCH_HASH:
        raise ValueError('Artifact-bound v0.9 verification gate is not satisfied')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ffr',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True)
    a=p.parse_args()
    if a.output_dir.exists():raise ValueError('Choose a new output directory; existing work is never overwritten')
    ffr=a.ffr.read_bytes()
    if len(ffr)!=SOURCE_SIZE or sha(ffr)!=FFR_HASH:raise ValueError('Unsupported input: exact FFR SHA-256 required')
    candidate=bytearray(ffr)
    for w in EXPECTED_WRITES:
        if ffr[w.offset:w.end]!=w.expected_source:raise ValueError('FFR save-repair source mismatch')
        candidate[w.offset:w.end]=w.final_bytes
    source=bytes(candidate)
    if sha(source)!=EXPECTED_OUTPUT_SHA256:raise ValueError('Candidate A restoration identity mismatch')
    rows,unresolved=collect(source)
    if unresolved:raise ValueError('Unresolved authored text')
    a.output_dir.mkdir(parents=True)
    chars,clear,solid,codes=prepare_fonts(rows,a.output_dir/'font')
    target,writes=build(source,rows,chars,clear,solid,codes)
    second,_=build(source,[dict(r)for r in rows],chars,clear,solid,codes)
    if target!=second or sha(target)!=TARGET_HASH:raise ValueError('Frozen target identity or determinism failed')
    patch=create_bps(ffr,target)
    if sha(patch)!=PATCH_HASH or apply_bps(ffr,patch)!=target:raise ValueError('Frozen BPS identity or application failed')
    (a.output_dir/(NAME+'.gba')).write_bytes(target)
    (a.output_dir/(NAME+'_FROM_FFR.bps')).write_bytes(patch)
    report=dict(version='v0.9',release_type='prerelease',source_sha256=FFR_HASH,source_size=len(ffr),
        target_sha256=sha(target),target_size=len(target),patch_sha256=sha(patch),patch_size=len(patch),
        format='BPS',application='One cumulative patch applied directly to the exact FFR ROM',
        deterministic=True,bps_roundtrip=True,save_fix_guard=True,unexpected_diff=0,
        original_large_font_preserved=True,sound_assets_preserved=True,private_glyphs=len(chars),
        compact_text_fields=len(rows),publication_status='LOCAL_BUILD_NOT_PUBLISHED',
        verification='See the artifact-bound v0.9 verification report; hardware and full playthrough remain v1.0 gates')
    (a.output_dir/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
