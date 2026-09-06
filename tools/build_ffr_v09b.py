"""Port authored changes to exact BETA3; BETA2 is a build-time review fixture.

End users apply a single cumulative BPS to BETA3 only. Historical builders stay
frozen. Each transferred pointer is rechecked against the BETA3 string, and
every other transferred writer requires identical source bytes. Unowned BETA3
bytes are preserved, including its own code, graphics and translation updates.
"""
import argparse
import copy
import difflib
import json
import struct
from pathlib import Path

from build_banked_font import collect, prepare_fonts, build as build_banked, FFR_HASH
from build_ffr_v09 import TARGET_HASH as V09_HASH
from confirmed_text_edits import normalized
from inspect_text_fix import plans as inspect_plans
from narikiri2_text_spec import read_c_string, decode_game_text
from reviewed_v09a import build as frozen_review, build_bound, sha, ROOT
from save_fix_spec import EXPECTED_WRITES, EXPECTED_OUTPUT_SHA256
from verify_save_fix_guard import verify_save_fix_bytes
from bps import create_bps, apply_bps
from reviewed_v09b import build as japanese_review
from source_profiles import source_profile

BETA3_HASH = source_profile('AN9J_FFR_BETA3_071102').sha256
BETA3_SIZE = source_profile('AN9J_FFR_BETA3_071102').size
V09A_HASH = 'faa2f0ebe1f7bbd9f4a7e1d38b7d35ca2349bfed1d8c2a5d8ae45feb0f7631f6'
NAME = 'NARIKIRI2_AN9J_K_DALMOORI_v0.9b'


def pointed(source, storage):
    pointer = struct.unpack_from('<I', source, storage)[0] - 0x08000000
    return pointer, read_c_string(source, pointer, len(source))


def transfer_writes(beta3, historical, writes, size):
    """No differing instruction/data writer may silently cross a revision."""
    image = beta3 + b'\xff' * (size - len(beta3))
    result = bytearray(image)
    previous = 0
    pointer_count = 0
    for w in sorted(writes, key=lambda w: w.offset):
        if w.offset < previous or w.end > size or len(w.expected) != len(w.final):
            raise ValueError('Overlapping or out-of-bounds port: ' + w.identity)
        text_pointer = (w.category == 'pointer' and not w.identity.endswith('_relative_pointer')
                        and not w.identity.startswith('ascii_loader_'))
        if text_pointer and w.offset < len(beta3):
            if len(w.final) != 4 or historical[w.offset:w.end] != w.expected:
                raise ValueError('Historical pointer ownership mismatch: ' + w.identity)
            old_pos, old_raw = pointed(historical, w.offset)
            new_pos, new_raw = pointed(beta3, w.offset)
            # BETA3 restores the Japanese half-width source for Lightning at
            # these two aliases. The reviewed Korean label remains 라이트닝.
            lightning = (w.identity, old_pos, new_pos, old_raw, new_raw) in (
                (name, 0x2BE414, 0x2BE414, b'LIGHT', 'ﾗｲﾄﾆﾝｸﾞ'.encode('cp932'))
                for name in ('ARTE_058_pointer', 'ARTE_211_pointer'))
            if old_raw != new_raw and not lightning:
                raise ValueError('BETA3 changed a first-stage authored source: ' + w.identity)
            pointer_count += 1
        elif image[w.offset:w.end] != w.expected:
            raise ValueError('BETA3 code/data writer conflict: ' + w.identity)
        if result[previous:w.offset] != image[previous:w.offset]:
            raise ValueError('Unowned BETA3 modification')
        result[w.offset:w.end] = w.final
        previous = w.end
    if result[previous:] != image[previous:]:
        raise ValueError('Unowned trailing modification')
    return bytes(result), pointer_count


def rebind_review(source):
    ledger = json.loads((ROOT/'translation/v09a_reviewed_deltas.json').read_text(encoding='utf-8'))
    decisions = json.loads((ROOT/'translation/v09b_beta3_decisions.json').read_text(encoding='utf-8'))
    decisions = {r['id']: r for r in decisions}
    seen = set()
    for row in ledger['rows']:
        pos, raw = pointed(source, int(row['bindings'][0], 16))
        for storage in row['bindings']:
            if pointed(source, int(storage, 16))[1] != raw:
                raise ValueError('Split BETA3 alias needs separate review: ' + row['id'])
        if sha(raw) != row['source_sha256']:
            decision = decisions.get(row['id'])
            if not decision or (sha(raw), row['source_sha256']) != (decision['beta3_sha256'], decision['beta2_sha256']):
                raise ValueError('Unreviewed BETA3 text difference: ' + row['id'])
            text = normalized(decode_game_text(source, raw))
            row['spans'] = [[a, b, decision['final'][c:d]] for op, a, b, c, d in
                            difflib.SequenceMatcher(None, text, decision['final'], autojunk=False).get_opcodes() if op != 'equal']
            seen.add(row['id'])
        row['source_offset'] = f'{pos:08X}'
        row['source_sha256'] = sha(raw)
    if seen != set(decisions):
        raise ValueError('BETA3 reviewed-difference population changed')
    ledger['baseline_sha256'] = sha(source)
    ledger['changed'] = sum(bool(r['spans']) for r in ledger['rows'])
    return ledger


def build(beta2, beta3, japanese, font_dir, review_intermediate=None):
    if len(beta2) != 0xC00000 or sha(beta2) != FFR_HASH:
        raise ValueError('Exact BETA2 build-time review fixture required')
    if len(beta3) != BETA3_SIZE or sha(beta3) != BETA3_HASH:
        raise ValueError('Exact BETA3(071102) input required')
    verify_save_fix_bytes(beta3, expected_size=BETA3_SIZE)
    candidate = bytearray(beta2)
    for w in EXPECTED_WRITES:
        if beta2[w.offset:w.end] != w.expected_source:
            raise ValueError('Historical EEPROM fixture mismatch')
        candidate[w.offset:w.end] = w.final_bytes
    candidate = bytes(candidate)
    if sha(candidate) != EXPECTED_OUTPUT_SHA256:
        raise ValueError('Historical Candidate A identity mismatch')
    rows, unresolved = collect(candidate)
    if unresolved:
        raise ValueError('Unresolved source names')
    chars, clear, solid, codes = prepare_fonts(rows, font_dir)
    old_baseline, writes = build_banked(candidate, copy.deepcopy(rows), chars, clear, solid, codes)
    if sha(old_baseline) != V09_HASH or sha(frozen_review(old_baseline)[0]) != V09A_HASH:
        raise ValueError('Frozen release reproduction failed')
    baseline, pointer_count = transfer_writes(beta3, candidate, writes, len(old_baseline))
    # The affine consumer's resources must also be identical before inheriting
    # its original assembly plan, not just its short hook prefix.
    for start, end in ((0x302684, 0x30268C), (0x3AFB82, 0x3AFD82), (0x71FDD0, 0x721E38)):
        if baseline[start:end] != old_baseline[start:end]:
            raise ValueError('BETA3 inspection resource changed')
    ledger = rebind_review(baseline)
    target, review = build_bound(baseline, ledger, inspect_plans(old_baseline))
    second, _ = build_bound(baseline, ledger, inspect_plans(old_baseline))
    if target != second:
        raise ValueError('Non-deterministic review build')
    if review_intermediate is not None:
        with review_intermediate.open('xb') as stream:
            stream.write(target)
    target, jp_review = japanese_review(target, japanese)
    for start, end in ((0xA601C, 0xA6800), (0xAC3F4, 0x2B2CAC)):
        if target[start:end] != beta3[start:end]:
            delta = [hex(i) for i in range(start, end) if target[i] != beta3[i]]
            raise ValueError('Protected BETA3 region changed: ' + str(delta[:24]))
    verify_save_fix_bytes(target, expected_size=len(target))
    patch = create_bps(beta3, target)
    if apply_bps(beta3, patch) != target or create_bps(beta3, target) != patch:
        raise ValueError('BPS reproducibility failure')
    report = dict(version='v0.9b', source_revision='FFR BETA3(071102)', source_sha256=BETA3_HASH,
                  source_size=len(beta3), build_reference_sha256=FFR_HASH,
                  target_sha256=sha(target), target_size=len(target), patch_sha256=sha(patch), patch_size=len(patch),
                  baseline_sha256=sha(baseline), first_stage_pointer_bindings=pointer_count,
                  reviewed_unique_texts=review['reviewed'], full_text_pointer_bindings=review['bindings'],
                  japanese_text_records_compared=8037, corrected_nontext_records=1,
                  compact_name_fields_compared=1227,
                  corrected_unique_texts=review['changed'], beta3_changed_texts_reviewed=2,
                  japanese_review=jp_review,
                  deterministic=True, bps_roundtrip=True, save_code_preserved=True,
                  publication_status='LOCAL_VALIDATION_CANDIDATE', runtime_status='NOT_VERIFIED')
    return target, patch, report, ledger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--beta2-reference', type=Path, required=True)
    parser.add_argument('--beta3', type=Path, required=True)
    parser.add_argument('--japanese-reference', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--candidate', action='store_true', help='Build a local candidate without authorizing release')
    args = parser.parse_args()
    if args.output_dir.exists():
        raise ValueError('Output directory must be new')
    beta2, beta3 = args.beta2_reference.read_bytes(), args.beta3.read_bytes()
    args.output_dir.mkdir(parents=True)
    target, patch, report, ledger = build(beta2, beta3, args.japanese_reference.read_bytes(), args.output_dir/'font',
                                         args.output_dir/'review_intermediate.gba')
    if not args.candidate:
        gate = json.loads((Path(__file__).resolve().parents[1]/'verification/v0.9b.json').read_text(encoding='utf-8'))
        if not gate['release_ready'] or any(gate[k] != report[k] for k in
                ('source_sha256', 'target_sha256', 'patch_sha256', 'japanese_review')):
            raise ValueError('Artifact-bound v0.9b verification gate not satisfied')
        report['publication_status'] = 'VERIFIED_LOCAL_PRODUCT_NOT_PUBLISHED'
        report['runtime_status'] = 'VERIFIED_WITH_DOCUMENTED_LIMITS'
    (args.output_dir/(NAME+'.gba')).write_bytes(target)
    (args.output_dir/(NAME+'_FROM_BETA3.bps')).write_bytes(patch)
    for name, data in (('manifest.json', report), ('rebound_review.json', ledger)):
        (args.output_dir/name).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
