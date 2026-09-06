"""Japanese-source-bound corrections over the independently ported BETA3 build."""
import hashlib
import json
import struct
import unicodedata
from pathlib import Path

from confirmed_text_edits import encode_full, normalized
from narikiri2_text_spec import read_c_string, decode_game_text, JAPANESE_SHA256
from reviewed_v09a import tokens, numbers, validate_layout
from build_banked_font import encode
from build_compact_target_catalog import known_compact_labels
from extended_compact_spec import extended_fields, text_at

ROOT = Path(__file__).resolve().parents[1]
INPUT_SHA256 = 'a40b46dcb560c6081c337156beef6c9d40d928f578dfbab5b2a72a6a6e5eed85'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build(source, japanese):
    if sha(source) != INPUT_SHA256 or sha(japanese) != JAPANESE_SHA256:
        raise ValueError('Exact BETA3 review intermediate and Japanese revision required')
    ledger = json.loads((ROOT/'translation/v09b_japanese_review.json').read_text(encoding='utf-8'))
    writes = []
    cursor = len(source)
    owners = set()
    identities = set()
    for row in ledger:
        if row.get('review') != 'JAPANESE_SOURCE_COMPARED' or not row.get('bindings'):
            raise ValueError('Unreviewed or unbound correction')
        if row['id'] in identities:
            raise ValueError('Duplicate reviewed identity')
        identities.add(row['id'])
        js = int(row['japanese_binding'], 16)
        jp = struct.unpack_from('<I', japanese, js)[0] - 0x08000000
        jr = read_c_string(japanese, jp, len(japanese))
        if sha(jr) != row['japanese_sha256']:
            raise ValueError('Japanese source changed: ' + row['id'])
        bindings = [int(s, 16) for s in row['bindings']]
        if js not in bindings:
            raise ValueError('Japanese binding is not a reviewed field')
        for storage in bindings:
            if not 0 <= storage <= len(japanese) - 4:
                raise ValueError('Pointer storage outside original cartridge')
            if any(storage < b and storage + 4 > a for a, b in
                   ((0xA601C, 0xA6800), (0xAC3F4, 0x2B2CAC))):
                raise ValueError('Protected cartridge region')
            if storage in owners:
                raise ValueError('Multiple pointer owners')
            owners.add(storage)
            pos = struct.unpack_from('<I', source, storage)[0] - 0x08000000
            raw = read_c_string(source, pos, len(source))
            if sha(raw) != row['source_sha256']:
                raise ValueError('Korean review source changed: ' + row['id'])
        old = normalized(decode_game_text(source, raw))
        final = row['final']
        if old == final or tokens(old) != tokens(final):
            raise ValueError('Empty correction or protected token change: ' + row['id'])
        if numbers(old) != numbers(final):
            jp_numbers = numbers(unicodedata.normalize('NFKC', jr.decode('cp932')))
            final_numbers = numbers(unicodedata.normalize('NFKC', final))
            if row.get('numeral_notation') != 'MATCH_JAPANESE' or jp_numbers != final_numbers:
                raise ValueError('Unreviewed numeric change: ' + row['id'])
        validate_layout(row['id'], bindings, final)
        payload = encode_full(final) + b'\0'
        if normalized(decode_game_text(source, payload[:-1])) != final:
            raise ValueError('Missing glyph or encoding mismatch: ' + row['id'])
        for storage in bindings:
            writes.append((storage, struct.pack('<I', cursor + 0x08000000)))
        writes.append((cursor, payload))
        cursor += len(payload)
    compact = json.loads((ROOT/'translation/v09b_compact_review.json').read_text(encoding='utf-8'))
    fields = known_compact_labels()
    fields.update({s: value[0] for s, value in extended_fields().items()})
    glyphs = json.loads((ROOT/'config/private_glyph_order.json').read_text(encoding='utf-8'))['glyphs']
    index = {c: i for i, c in enumerate(glyphs)}
    for row in compact:
        storage = int(row['binding'], 16)
        if row.get('review') != 'JAPANESE_SOURCE_COMPARED' or fields.get(storage) != row['id']:
            raise ValueError('Unreviewed compact field')
        if storage in owners or row['id'] in identities:
            raise ValueError('Duplicate compact field')
        owners.add(storage)
        identities.add(row['id'])
        raw, jr = text_at(source, storage)[1], text_at(japanese, storage)[1]
        if sha(raw) != row['source_sha256'] or sha(jr) != row['japanese_sha256']:
            raise ValueError('Compact source changed')
        if raw != encode(row['previous'], index) or row['previous'] == row['final']:
            raise ValueError('Compact transcription mismatch')
        if len(row['final']) > 18 or tokens(row['final']) or numbers(row['previous']) != numbers(row['final']):
            raise ValueError('Compact layout or control mismatch')
        payload = encode(row['final'], index) + b'\0'
        writes.append((storage, struct.pack('<I', cursor + 0x08000000)))
        writes.append((cursor, payload))
        cursor += len(payload)
    # 080A48C6 loads two pointers through this literal, not a C string.
    # FFR relocated it to save prose. D00549 was therefore a false text field.
    # Both genuine translated entries at 00373760/64 are already reviewed.
    trade_literal = 0xA4918
    if trade_literal in owners or source[trade_literal:trade_literal+4] != bytes.fromhex('192dc208'):
        raise ValueError('Trade table literal changed')
    if japanese[trade_literal:trade_literal+4] != bytes.fromhex('60373708'):
        raise ValueError('Japanese trade table identity changed')
    if source[0xA48C6:0xA48D0] != japanese[0xA48C6:0xA48D0]:
        raise ValueError('Trade pointer-table consumer changed')
    for slot in (0x373760, 0x373764):
        pos = struct.unpack_from('<I', source, slot)[0] - 0x08000000
        if not read_c_string(source, pos, len(source)).startswith(b'%l'):
            raise ValueError('Trade table entry changed')
    writes.append((trade_literal, bytes.fromhex('60373708')))
    size = (cursor + 0xFFFF) & ~0xFFFF
    if size > 0x02000000:
        raise ValueError('GBA cartridge address-space overflow')
    image = source + b'\xff' * (size - len(source))
    target = bytearray(image)
    end = 0
    for pos, payload in sorted(writes):
        if pos < end:
            raise ValueError('Overlapping review writes')
        target[pos:pos+len(payload)] = payload
        end = pos + len(payload)
    return bytes(target), dict(corrected=len(ledger), bindings=len(owners),
                               compact_corrected=len(compact),
                               compact_ledger_sha256=sha((ROOT/'translation/v09b_compact_review.json').read_bytes()),
                               trade_pointer_table_restored=True,
                               ledger_sha256=sha((ROOT/'translation/v09b_japanese_review.json').read_bytes()))
