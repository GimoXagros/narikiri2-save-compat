"""Private-font development profile; no global Latin-font reclamation.

All output ownership is declared before any source mutation. Assembly requires
Keystone 0.9.2; generated instructions are also checked with Capstone. See the
design and the instruction-level tests before treating this as accepted code.
"""
from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
import struct

from find_gba_lz77_asset import decompress_lz77_stream
from narikiri2_item_ui_font import (UI_FONT_LZ77_OFFSET, extract_glyph_pixels,
                                  fit_bitmap, pack_ui_tile)
from narikiri2_text_spec import (BASELINE_SHA256, ITEM_RECORD_COUNT,
                                ITEM_RECORD_SIZE, ITEM_TABLE_OFFSET,
                                hangul_to_game_code, read_c_string, read_pointer)
from verify_save_fix_guard import verify_save_fix_bytes
from confirmed_text_edits import plans as full_text_plans
from item_glyph_presentation import revised_ui_glyphs, PROVENANCE

SOURCE_SIZE = 0xC00000
TARGET_SIZE = 0xC04000
PRIVATE_TILE_START = 0x178
PRIVATE_LARGE_INDEX = 4992
PRIVATE_LARGE_CODE = 0x9F40
GLYPHS = ("ㄸ", "곰", "곡", "괭:L", "꽃:L", "빵:L", "괭:R", "꽃:R", "빵:R", "롱:L", "롱:R", "룡:L", "룡:R")
COUNT = len(GLYPHS)
UI_OFFSET, SOLID_OFFSET, LARGE_OFFSET, TEXT_OFFSET = 0xC01000, 0xC01400, 0xC01800, 0xC01C00

# Entry points and exact overwritten Thumb-1 instructions. No relaxed matching.
HOOKS = (
    ("private_small", 0x1AF0, "201C20385F2817D8", 0xC00000, 0),
    ("private_simple", 0x1E10, "101C20385E2807D8", 0xC00100, 0),
    ("private_full_name", 0x1674, "FFF75AFF201C311C", 0xC00200, 3),
    ("private_convert", 0x5078, "0136414600F016F8", 0xC00300, 3),
    ("private_large_lookup", 0x14E0, "10B552010B4BD418", 0xC00400, 3),
    ("private_font_load", 0x21CC, "381CF0BC02BC0847", 0xC00500, 3),
    ("private_sprite_lookup", 0x2220, "1548091889461549", 0xC00600, 0),
)


@dataclass(frozen=True)
class Write:
    identity: str
    category: str
    offset: int
    expected: bytes
    final: bytes

    @property
    def end(self):
        return self.offset + len(self.final)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def large_codes(raw: bytes):
    """Code-boundary scan for the full-text consumer, not an unaligned byte find."""
    position = 0
    while position < len(raw):
        lead = raw[position]
        if 0x80 <= lead <= 0x9F or lead >= 0xE0:
            if position + 1 == len(raw):
                break
            yield position, (lead << 8) | raw[position + 1]
            position += 2
        else:
            position += 1


def check_survey(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 10347:
        raise ValueError("Expanded-pointer survey denominator changed; inspect before rebuilding")
    unique_compact = {}
    for row in rows:
        raw = bytes.fromhex(row["kr_raw_hex"])
        target = int(row["kr_target_hex"], 16)
        if target >= 0x900000:
            unique_compact[target] = raw
            if b"\x7f" in raw:
                raise ValueError("Private-token collision in compact survey")
        if any(PRIVATE_LARGE_CODE <= code < PRIVATE_LARGE_CODE + 32 for _, code in large_codes(raw)):
            raise ValueError("Private large-code collision at a decoded code boundary")
    if len(unique_compact) != 1211:
        raise ValueError("Distinct compact survey denominator changed")
    return {"pointer_candidates": len(rows), "distinct_compact_candidates": len(unique_compact),
            "private_code_collisions": 0, "scope": "SURVEY_NOT_COMPLETE_REACHABILITY_PROOF"}


def tile_bitmap(tile: bytes):
    return [[int(bool((tile[y*4+x//2] >> ((x & 1)*4)) & 15)) for x in range(8)] for y in range(8)]


def pack_large(bitmap):
    return b"".join(sum(bit << x for x, bit in enumerate(row)).to_bytes(2, "little") for row in bitmap)


def make_glyph_banks(source: bytes):
    decompressed = decompress_lz77_stream(source, UI_FONT_LZ77_OFFSET, 0x10000)
    if decompressed is None or len(decompressed[0]) != 0x2000 or decompressed[1] != 1769:
        raise ValueError("Original small-font profile mismatch")
    small_font = decompressed[0]
    small_d = tile_bitmap(small_font[0x13*32:0x14*32])
    small_dd = [[0]*8 for _ in range(8)]
    # Preserve the source ㄷ skeleton; horizontally reduce its six-pixel body to
    # three pixels, duplicate with one clear separating column. No new strokes.
    for y in range(8):
        for x in range(3):
            bit = int(any(small_d[y][2+x*2:4+x*2]))
            small_dd[y][1+x] = small_dd[y][5+x] = bit
    large_d = extract_glyph_pixels(source, 0x94D3)
    large_dd = [[0]*16 for _ in range(16)]
    for y in range(16):
        for x in range(3):
            bit = int(any(large_d[y][6+x*2:8+x*2]))
            large_dd[y][4+x] = large_dd[y][8+x] = bit
    small = [pack_ui_tile(small_dd)]
    large = [pack_large(large_dd)]
    records = [{"id": 1, "character": "ㄸ", "source": "baseline ㄷ: small tile 13 / large code 94D3",
                "transform": "six-to-three-column OR reduction; two copies separated by one column"}]
    # 곰 uses the exact existing 고 head and the square ㅁ from the large 곰.
    # In contrast, raw 3E (공) has a rounded ㅇ; do not change that shared slot.
    go_head = tile_bitmap(small_font[0x2e*32:0x2f*32])[:5]
    gom_source = extract_glyph_pixels(source, hangul_to_game_code("곰"))
    gom_tail = []
    for y in (8,9,11):
        original_row = gom_source[y][2:10]
        gom_tail.append([0]+[original_row[(x*7)//6] for x in range(7)])
    gok_tail = tile_bitmap(small_font[0x52*32:0x53*32])[5:8]  # existing 녹: ㄱ footer
    small.extend((pack_ui_tile(go_head+gom_tail), pack_ui_tile(go_head+gok_tail)))
    for identity, char in ((2,"곰"),(3,"곡")):
        code = hangul_to_game_code(char)
        bitmap = extract_glyph_pixels(source, code)
        large.append(pack_large(bitmap))
        records.append({"id": identity, "character": char, "source": f"baseline large Hangul code {code:04X}",
                        "transform": "large byte identity; existing 고 head plus source-derived distinct ㅁ/ㄱ footer"})
    # These three syllables need more horizontal detail than one 8px tile.
    # Retain source columns, deleting only explicitly reviewed vertical-extension
    # rows. No threshold resampling or new ink; the resulting 16x8 canvas is split
    # into two adjacent cells. Both cells together stay within each old name's
    # advance. The large path stretches columns 3:2 and splits at its 12px advance.
    retained_rows = {"괭": (1,3,4,6,7,8,9,11), "꽃": (1,3,5,6,7,8,9,11),
                     "빵": (1,3,4,6,7,8,9,11), "롱": (1,2,3,4,5,7,9,11),
                     "룡": (1,2,3,4,5,7,9,11)}
    revised = revised_ui_glyphs(lambda n: tile_bitmap(small_font[n*32:(n+1)*32]))
    halves = {}
    for char, source_rows in retained_rows.items():
        bitmap = extract_glyph_pixels(source, hangul_to_game_code(char))
        columns = [x for x in range(16) if any(row[x] for row in bitmap)]
        left, span = min(columns), max(columns)-min(columns)+1
        # Enlarge only: duplicate original columns into a 14px ink box, leaving
        # one margin column at each end of the two-cell canvas. No lost columns
        # and no six-pixel artificial gap before the next Korean syllable.
        if span > 14:
            raise ValueError("Wide source glyph exceeds the retained-column design")
        ui = [[0]+[bitmap[y][left+x*span//14] for x in range(14)]+[0] for y in source_rows]
        if char in revised:
            ui = revised[char]
        wide_large = [[row[x*2//3] for x in range(24)] for row in bitmap]
        halves[char] = ([pack_ui_tile([row[x:x+8] for row in ui]) for x in (0,8)],
                        [pack_large([row[x:x+12]+[0]*4 for row in wide_large]) for x in (0,12)])
    for identity, label in enumerate(GLYPHS[3:], 4):
        char, part = label.split(":")
        side = int(part == "R")
        small.append(halves[char][0][side])
        large.append(halves[char][1][side])
        records.append({"id":identity,"character":char,"part":part,
                        "source":f"baseline large Hangul code {hangul_to_game_code(char):04X}",
                        "transform": (PROVENANCE[char] if char in revised else f"small source rows {retained_rows[char]}; nearest-column enlargement to 14px") + f"; half {part}; large horizontal 3:2 split"})
    clear = b"".join(small)
    solid = bytes((byte or 0) | (0x0B if byte & 15 == 0 else 0) |
                  (0xB0 if byte & 0xF0 == 0 else 0) for byte in clear)
    big = b"".join(large)
    if len(set(small)) != COUNT or any(not any(glyph) for glyph in small):
        raise ValueError("Empty or colliding private glyph")
    for row in records:
        idx = row["id"] - 1
        row.update({"raw_hex": f"7F{idx+1:02X}", "ui_tile": PRIVATE_TILE_START + idx,
                    "large_code": f"{PRIVATE_LARGE_CODE+idx:04X}",
                    "small_sha256": digest(small[idx]), "large_sha256": digest(large[idx]),
                    "visual_acceptance": "NOT_VERIFIED"})
    return clear, solid, big, records


def assemble_hook(path: Path, offset: int, count: int = COUNT):
    from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB, KS_MODE_LITTLE_ENDIAN
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
    text = path.read_text(encoding="utf-8").replace("FONT_COUNT", str(count))
    encoded, _ = Ks(KS_ARCH_ARM, KS_MODE_THUMB | KS_MODE_LITTLE_ENDIAN).asm(text, addr=0x08000000+offset)
    if encoded is None or not 0 < len(encoded) <= 0x100:
        raise ValueError(f"Assembly exceeds its owned 256-byte block: {path.name}")
    payload = bytes(encoded)
    # Literal words are data, not instructions. Inspect the instruction prefix
    # up to the first alignment directive, excluding label-only lines.
    count = sum(bool(line.strip()) and not line.strip().endswith(":")
                for line in text.split(".balign", 1)[0].splitlines())
    instructions = list(Cs(CS_ARCH_ARM, CS_MODE_THUMB).disasm(payload, 0x08000000+offset))[:count]
    if len(instructions) != count:
        raise ValueError("Assembly instruction count mismatch")
    for instruction in instructions:
        if instruction.size == 4 and instruction.mnemonic != "bl":
            raise ValueError(f"Thumb-2 instruction forbidden: {instruction.mnemonic} {instruction.op_str}")
        if instruction.mnemonic in ("blx", "it", "itt", "cbz", "cbnz", "movw", "movt", "nop"):
            raise ValueError(f"Not ARM7TDMI-safe: {instruction.mnemonic}")
    return payload, [{"address": f"{i.address:08X}", "bytes": i.bytes.hex().upper(),
                      "instruction": f"{i.mnemonic} {i.op_str}"} for i in instructions]


def veneer(offset: int, target: int, scratch: int) -> bytes:
    if offset & 3 or target & 1 or scratch not in (0, 3):
        raise ValueError("Invalid absolute Thumb veneer")
    return struct.pack("<HHI", 0x4800 | scratch << 8, 0x4700 | scratch << 3, 0x08000000+target+1)


def private_tiles(raw: bytes, count: int = COUNT):
    from item_name_consumer import tiles_for_name
    result = []
    mode = 0
    cursor = 0
    # Mode persists across private tokens; the original parser is used for each
    # ordinary byte, seeded with a mode toggle when necessary.
    while cursor < len(raw):
        b = raw[cursor]
        if b == 0x12:
            mode ^= 1
            cursor += 1
            continue
        if b == 0x7F:
            if cursor + 1 >= len(raw) or not 1 <= raw[cursor+1] <= count:
                raise ValueError("Malformed private name token")
            result.append(PRIVATE_TILE_START + raw[cursor+1] - 1)
            cursor += 2
        else:
            result.extend(tiles_for_name((b"\x12" if mode else b"") + bytes((b,))))
            cursor += 1
    return result


def validate_private_pairs(raw: bytes, glyphs: tuple[str, ...] = GLYPHS):
    """The half-glyph tokens are not independently meaningful translations."""
    tokens = []
    i = 0
    while i < len(raw):
        if raw[i] == 0x7f:
            if i+1 >= len(raw):
                raise ValueError("Truncated private token")
            tokens.append((i, raw[i+1]))
            i += 2
        else:
            i += 1
    for position, identity in tokens:
        if not 1 <= identity <= len(glyphs):
            raise ValueError("Invalid private glyph identity")
        label = glyphs[identity-1]
        if label.endswith(':L'):
            right = glyphs.index(label[:-1]+'R') + 1
            if raw[position+2:position+4] != bytes((0x7f,right)):
                raise ValueError("Missing right half of a wide private glyph")
        elif label.endswith(':R'):
            left = glyphs.index(label[:-1]+'L') + 1
            if position < 2 or raw[position-2:position] != bytes((0x7f,left)):
                raise ValueError("Orphan right half of a wide private glyph")


def development_name_limit(source: bytes, index: int, old: bytes, count: int = COUNT) -> int:
    """Tile limit for admission to DEV; it is not final screen acceptance."""
    if index != 65:
        return len(private_tiles(old, count))
    storage = ITEM_TABLE_OFFSET + index*ITEM_RECORD_SIZE
    # ITEM_010 is a six-cell weapon name in the same 0x0F layout category.
    # ITEM_044 (the former reference) is armour category 0x11 and therefore
    # cannot establish capacity for ITEM_065.
    reference = ITEM_TABLE_OFFSET + 10*ITEM_RECORD_SIZE
    if source[storage+11] != source[reference+11]:
        raise ValueError('ITEM_065 layout reference category differs')
    _, reference_name = read_pointer(source, reference)
    if len(private_tiles(read_c_string(source, reference_name, len(source)), count)) < 5:
        raise ValueError('ITEM_065 source category has no five-cell reference')
    return 5


def build(
    source: bytes,
    root: Path,
    translations: list[dict],
    *,
    glyph_provider=make_glyph_banks,
    glyph_labels: tuple[str, ...] = GLYPHS,
    include_full_text: bool = True,
):
    # The existing popup centering counter treats IDs below 0x20 as controls.
    # Raising this ceiling requires changing and testing that consumer too.
    count = len(glyph_labels)
    if not 1 <= count < 0x20:
        raise ValueError("Private glyph count exceeds the verified popup-counter contract")
    if len(source) != SOURCE_SIZE or digest(source) != BASELINE_SHA256:
        raise ValueError("Not the immutable Candidate A baseline")
    verify_save_fix_bytes(source)
    survey = check_survey(root / "analysis/expanded_pointer_survey.csv")
    clear, solid, big, glyphs = glyph_provider(source)
    if not (len(clear) == count * 32 and len(solid) == count * 32 and len(big) == count * 32):
        raise ValueError("Private glyph provider size does not match its declared labels")
    tail = bytearray(b"\xff" * (TARGET_SIZE-SOURCE_SIZE))
    tail_allocations = []
    def allocate(identity: str, offset: int, data: bytes, category: str):
        if not SOURCE_SIZE <= offset < offset + len(data) <= TARGET_SIZE:
            raise ValueError(f"Tail allocation out of range: {identity}")
        if any(offset < row["end"] and row["offset"] < offset+len(data) for row in tail_allocations):
            raise ValueError(f"Tail allocation overlaps: {identity}")
        tail_allocations.append({"id": identity, "offset": offset, "end": offset+len(data),
                                 "category": category, "sha256": digest(data)})
        tail[offset-SOURCE_SIZE:offset-SOURCE_SIZE+len(data)] = data
    writes = []
    disassembly = {}
    for identity, offset, expected_hex, target, scratch in HOOKS:
        payload, disassembled = assemble_hook(root / f"asm/{identity}.s", target, count)
        allocate(identity, target, payload, "THUMB_CODE")
        disassembly[identity] = disassembled
        writes.append(Write(identity.upper(), "THUMB_HOOK", offset, bytes.fromhex(expected_hex),
                            veneer(offset, target, scratch)))
    allocate("PRIVATE_UI_TRANSPARENT", UI_OFFSET, clear, "FONT_GLYPH")
    allocate("PRIVATE_UI_SOLID", SOLID_OFFSET, solid, "FONT_GLYPH")
    allocate("PRIVATE_LARGE", LARGE_OFFSET, big, "FONT_GLYPH")
    cursor, changed_names = TEXT_OFFSET, []
    seen = set()
    for row in translations:
        index = int(row["entry_index"])
        if index in seen or not 0 <= index < ITEM_RECORD_COUNT:
            raise ValueError("Invalid or repeated item-name edit")
        seen.add(index)
        storage = ITEM_TABLE_OFFSET + index * ITEM_RECORD_SIZE
        _, old_offset = read_pointer(source, storage)
        old = read_c_string(source, old_offset, len(source))
        if old.hex().upper() != row["expected_raw_hex"].upper():
            raise ValueError(f"Item {index} source name mismatch")
        raw = bytes.fromhex(row["final_raw_hex"])
        if not raw or b"\x00" in raw or len(raw) >= 32:
            raise ValueError("Empty/NUL/oversized compact-name payload")
        tiles = private_tiles(raw, count)
        validate_private_pairs(raw, glyph_labels)
        limit = development_name_limit(source, index, old, count)
        if len(tiles) > limit:
            raise ValueError(f"Item {index} exceeds its declared development tile limit")
        allocate(f"ITEM_{index:03d}_NAME", cursor, raw+b"\0", "TEXT_PAYLOAD")
        pointer = (0x08000000+cursor).to_bytes(4, "little")
        writes.append(Write(f"ITEM_{index:03d}_NAME_POINTER", "TEXT_POINTER", storage,
                            source[storage:storage+4], pointer))
        changed_names.append({**row, "old_offset": old_offset, "new_offset": cursor,
                              "advance_px": len(tiles)*8, "old_advance_px": len(private_tiles(old, count))*8,
                              "development_limit_px":limit*8,
                              "capacity_status":"ALL_CONTEXTS_PENDING_FINAL_BATCH"})
        cursor += len(raw)+1
    full_changes=full_text_plans(source,root) if include_full_text else []
    changed_descriptions=set()
    for row in full_changes:
        storage=row['storage']
        allocate(row['id'],cursor,row['payload']+b'\0','TEXT_PAYLOAD')
        writes.append(Write(row['id']+'_POINTER','TEXT_POINTER',storage,source[storage:storage+4],
                            struct.pack('<I',0x08000000+cursor)))
        row['new_offset']=cursor
        cursor+=len(row['payload'])+1
        if row['item'] is not None:
            changed_descriptions.add(row['item'])
    # Complete plan exists before this first mutation of the source copy.
    writes.append(Write("OWNED_APPEND_BLOCK", "APPENDED_CODE_FONT_TEXT_AND_PADDING", SOURCE_SIZE, b"", bytes(tail)))
    writes.sort(key=lambda w: w.offset)
    for left, right in zip(writes, writes[1:]):
        if left.end > right.offset:
            raise ValueError("Expected-write plan overlap")
    result = bytearray(source)
    for write in writes:
        if source[write.offset:write.offset+len(write.expected)] != write.expected:
            raise ValueError(f"Expected source bytes mismatch: {write.identity}")
        if write.identity != "OWNED_APPEND_BLOCK" and len(write.expected) != len(write.final):
            raise ValueError("In-place write length changed")
        result[write.offset:write.end] = write.final
    result = bytes(result)
    guard = verify_save_fix_bytes(result, expected_size=TARGET_SIZE)
    if result[0xAC3F4:0xCB000] != source[0xAC3F4:0xCB000]:
        raise ValueError("An original font, compressed stream, palette or mapping was changed")
    permitted = {i for w in writes for i in range(w.offset, w.end)}
    diff = [i for i in range(SOURCE_SIZE) if source[i] != result[i]]
    if any(i not in permitted for i in diff):
        raise ValueError("Unplanned source difference")
    # Original item records remain intact apart from explicitly listed pointers.
    for index in range(ITEM_RECORD_COUNT):
        start = ITEM_TABLE_OFFSET+index*ITEM_RECORD_SIZE
        _, pointer = read_pointer(result, start)
        read_c_string(result, pointer, len(result))
        if result[start+4:start+0x10] != source[start+4:start+0x10]:
            raise ValueError("An item's logic/stats changed")
        if index not in changed_descriptions and result[start+0x10:start+0x14] != source[start+0x10:start+0x14]:
            raise ValueError("An unlisted item description pointer changed")
        _, description = read_pointer(result,start+0x10)
        read_c_string(result,description,len(result))
        if index not in seen and result[start:start+4] != source[start:start+4]:
            raise ValueError("Unlisted item name pointer changed")
    plan = [{"id": w.identity, "category": w.category, "offset": w.offset, "end": w.end,
             "expected_source_hex": w.expected.hex().upper(), "final_sha256": digest(w.final),
             "actual_changed_source_bytes": sum(a != b for a, b in zip(w.expected, w.final))}
            for w in writes]
    return result, {"status": "DEVELOPMENT_NOT_RELEASE_ACCEPTED", "source_sha256": digest(source),
                    "target_sha256": digest(result), "source_size": SOURCE_SIZE, "target_size": len(result),
                    "save_guard": guard, "original_font_assets_byte_identical": True,
                    "source_changed_bytes": len(diff), "unplanned_differences": 0,
                    "glyphs": glyphs, "survey": survey, "writes": plan,
                    "tail_allocations": tail_allocations, "names": changed_names,
                    "full_text_changes":[{**{k:v for k,v in row.items() if k not in ('expected','payload')},
                                          'expected_raw_hex':row['expected'].hex().upper(),
                                          'final_raw_hex':row['payload'].hex().upper()} for row in full_changes],
                    "disassembly": disassembly, "hardware_acceptance": "NOT_VERIFIED"}
