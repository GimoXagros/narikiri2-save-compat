"""Reproduce v0.9a from exact FFR via the frozen v0.9 product baseline."""
import argparse,json
from pathlib import Path
from build_banked_font import SOURCE_SIZE,FFR_HASH,collect,prepare_fonts,build
from save_fix_spec import EXPECTED_WRITES,EXPECTED_OUTPUT_SHA256
from build_ffr_v09 import TARGET_HASH as BASELINE_HASH
from reviewed_v09a import build as review_build,sha,ROOT
from bps import create_bps,apply_bps

NAME='NARIKIRI2_AN9J_K_DALMOORI_v0.9a'
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ffr',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--candidate',action='store_true',help='Local validation candidate; never authorizes packaging/publication')
    a=p.parse_args()
    if a.output_dir.exists():raise ValueError('Choose a new output directory')
    ffr=a.ffr.read_bytes()
    if len(ffr)!=SOURCE_SIZE or sha(ffr)!=FFR_HASH:raise ValueError('Exact FFR required')
    candidate=bytearray(ffr)
    for w in EXPECTED_WRITES:
        if ffr[w.offset:w.end]!=w.expected_source:raise ValueError('Save-fix guard')
        candidate[w.offset:w.end]=w.final_bytes
    source=bytes(candidate)
    if sha(source)!=EXPECTED_OUTPUT_SHA256:raise ValueError('Candidate A identity')
    rows,unresolved=collect(source)
    if unresolved:raise ValueError('Unresolved v0.9 text')
    a.output_dir.mkdir(parents=True)
    chars,clear,solid,codes=prepare_fonts(rows,a.output_dir/'font')
    baseline,_=build(source,rows,chars,clear,solid,codes)
    if sha(baseline)!=BASELINE_HASH:raise ValueError('Frozen v0.9 changed')
    target,review=review_build(baseline)
    second,_=review_build(baseline)
    if target!=second:raise ValueError('Non-deterministic review build')
    patch=create_bps(ffr,target)
    if apply_bps(ffr,patch)!=target:raise ValueError('Cumulative BPS round trip')
    report=dict(version='v0.9a',release_type='prerelease',source_sha256=FFR_HASH,source_size=len(ffr),
        baseline_sha256=BASELINE_HASH,target_sha256=sha(target),target_size=len(target),
        patch_sha256=sha(patch),patch_size=len(patch),format='BPS',
        application='Apply this single cumulative patch to the exact original FFR input',
        reviewed_unique_texts=review['reviewed'],full_text_pointer_bindings=review['bindings'],
        corrected_unique_texts=review['changed'],review_ledger_sha256=sha((ROOT/'translation/v09a_reviewed_deltas.json').read_bytes()),
        deterministic=True,bps_roundtrip=True,save_fix_preserved=True,sound_preserved=True,original_large_font_preserved=True,
        publication_status='LOCAL_VALIDATION_CANDIDATE' if a.candidate else 'VERIFIED_LOCAL_PRODUCT_NOT_PUBLISHED')
    if not a.candidate:
        gate=json.loads((ROOT/'verification/v0.9a.json').read_text(encoding='utf-8'))
        if not gate['release_ready'] or any(gate[k]!=report[k] for k in ('target_sha256','patch_sha256','review_ledger_sha256')):raise ValueError('Artifact-bound v0.9a gate not satisfied')
    (a.output_dir/(NAME+'.gba')).write_bytes(target)
    (a.output_dir/(NAME+'_FROM_FFR.bps')).write_bytes(patch)
    (a.output_dir/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
