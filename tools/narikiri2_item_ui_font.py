"""Small item-name font support for the fixed AN9J Korean baseline."""

from __future__ import annotations

from collections import defaultdict, deque

from find_gba_lz77_asset import decompress_lz77_stream
from item_name_consumer import COMPACT_CODE_TEXT
from narikiri2_text_spec import (
    ASCII_CONVERSION_TABLE,
    TextStructureError,
    _table_halfword,
    game_sjis_glyph_index,
    hangul_to_game_code,
)


UI_FONT_LZ77_OFFSET = 0x0CA3F4
UI_FONT_DECOMPRESSED_SIZE = 0x2000
UI_FONT_RESERVED_END = 0x0CABC4
FONT_OFFSET = 0x0AC3F4
GLYPH_SIZE = 32

# These uppercase ASCII slots are unused by the final 157 item names. They are
# deliberately explicit because changing a global compact-font slot is a
# product-level compatibility decision, not a generic encoder fallback.
CUSTOM_RAW_BY_CHARACTER = {
    "분": 0x4A,  # J
    "꽃": 0x51,  # Q
    "괭": 0x58,  # X (removed with PICKAUX)
    "빵": 0x5A,  # Z
}

KNOWN_COMPACT_GLYPHS = {
    0x3D: (0x94ED, COMPACT_CODE_TEXT[0x94ED]),
    0x3E: (0x94EE, COMPACT_CODE_TEXT[0x94EE]),
}

# Frozen failed POC2 inputs, retained ONLY for byte-exact reproduction.
# The key "곰" records intended wording, not verified rendering: raw 3D is 골.
# 21CD and 24D3 also require reassessment; do not use this as a new encoder.
ITEM_UI_SEQUENCES = {
    "분꽃": bytes.fromhex("4A51"),
    "곰": bytes.fromhex("3D"),
    "곡괭이": bytes.fromhex("21CD5829C4"),
    "빵": bytes.fromhex("5A"),
    "롱보우": bytes.fromhex("24D37812B2"),
}


def compress_lz77(data: bytes, *, vram_safe: bool = False) -> bytes:
    """Create a deterministic type-0x10 stream.

    SWI 12h buffers the low destination byte until the halfword is complete.
    A distance-one back-reference can therefore read stale VRAM. Opt in to
    distance >= 2 and word padding for that consumer. The default preserves
    historical WRAM-stream reproducibility.
    """
    if not 0 < len(data) <= 0xFFFFFF:
        raise ValueError("LZ77 input size is outside the GBA header range")
    output = bytearray((0x10, len(data) & 0xFF, len(data) >> 8 & 0xFF, len(data) >> 16 & 0xFF))
    positions: dict[bytes, deque[int]] = defaultdict(deque)
    cursor = 0
    while cursor < len(data):
        flag_offset = len(output)
        output.append(0)
        flags = 0
        for bit in range(7, -1, -1):
            if cursor >= len(data):
                break
            best_length = 0
            best_distance = 0
            if cursor + 3 <= len(data):
                key = data[cursor:cursor + 3]
                candidates = positions[key]
                while candidates and cursor - candidates[0] > 0x1000:
                    candidates.popleft()
                for candidate in reversed(candidates):
                    distance = cursor - candidate
                    if vram_safe and distance < 2:
                        continue
                    length = 3
                    limit = min(18, len(data) - cursor)
                    while length < limit and data[candidate + length] == data[cursor + length]:
                        length += 1
                    if length > best_length:
                        best_length, best_distance = length, distance
                        if length == 18:
                            break
            if best_length >= 3:
                flags |= 1 << bit
                encoded_distance = best_distance - 1
                output.extend((((best_length - 3) << 4) | (encoded_distance >> 8), encoded_distance & 0xFF))
                consumed = best_length
            else:
                output.append(data[cursor])
                consumed = 1
            for position in range(cursor, cursor + consumed):
                if position + 3 <= len(data):
                    bucket = positions[data[position:position + 3]]
                    bucket.append(position)
                    while bucket and position - bucket[0] > 0x1000:
                        bucket.popleft()
            cursor += consumed
        output[flag_offset] = flags
    if vram_safe:
        output.extend(b'\0' * (-len(output) % 4))
    return bytes(output)


def extract_glyph_pixels(rom: bytes, code: int) -> list[list[int]]:
    index = game_sjis_glyph_index(code)
    start = FONT_OFFSET + index * GLYPH_SIZE
    raw = rom[start:start + GLYPH_SIZE]
    if len(raw) != GLYPH_SIZE:
        raise TextStructureError("source glyph exceeds ROM")
    return [
        [
            (int.from_bytes(raw[y * 2:y * 2 + 2], "little") >> x) & 1
            for x in range(16)
        ]
        for y in range(16)
    ]


def fit_bitmap(source: list[list[int]], width: int = 8, height: int = 8) -> list[list[int]]:
    points = [(x, y) for y, row in enumerate(source) for x, bit in enumerate(row) if bit]
    if not points:
        raise TextStructureError("empty source glyph")
    left, right = min(x for x, _ in points), max(x for x, _ in points) + 1
    top, bottom = min(y for _, y in points), max(y for _, y in points) + 1
    cropped = [row[left:right] for row in source[top:bottom]]
    source_height, source_width = len(cropped), len(cropped[0])
    ratio = min(width / source_width, height / source_height)
    fitted_width = max(1, round(source_width * ratio))
    fitted_height = max(1, round(source_height * ratio))
    resized = [[0] * fitted_width for _ in range(fitted_height)]
    for y in range(fitted_height):
        y_start = y * source_height // fitted_height
        y_end = max(y_start + 1, ((y + 1) * source_height + fitted_height - 1) // fitted_height)
        for x in range(fitted_width):
            x_start = x * source_width // fitted_width
            x_end = max(x_start + 1, ((x + 1) * source_width + fitted_width - 1) // fitted_width)
            samples = [cropped[sy][sx] for sy in range(y_start, min(y_end, source_height)) for sx in range(x_start, min(x_end, source_width))]
            resized[y][x] = int(sum(samples) * 255 >= 96 * len(samples))
    result = [[0] * width for _ in range(height)]
    x0, y0 = (width - fitted_width) // 2, (height - fitted_height) // 2
    for y, row in enumerate(resized):
        result[y0 + y][x0:x0 + fitted_width] = row
    return result


def pack_ui_tile(bitmap: list[list[int]]) -> bytes:
    output = bytearray(32)
    for y in range(8):
        for x in range(8):
            if bitmap[y][x]:
                output[y * 4 + x // 2] |= 0xF << (4 * (x & 1))
    return bytes(output)


def pack_compact_glyph(bitmap: list[list[int]]) -> bytes:
    rows = [[0] * 16 for _ in range(16)]
    x0, y0 = 3, 1
    for y in range(8):
        for x in range(8):
            if bitmap[y][x]:
                rows[y0 + y][x0 + x] = 1
    output = bytearray()
    for row in rows:
        value = sum(bit << column for column, bit in enumerate(row))
        output.extend(value.to_bytes(2, "little"))
    return bytes(output)


def apply_custom_item_glyphs(rom: bytes) -> tuple[bytes, list[dict[str, object]]]:
    result = bytearray(rom)
    stream = decompress_lz77_stream(rom, UI_FONT_LZ77_OFFSET, 0x10000)
    if stream is None:
        raise TextStructureError("item UI font LZ77 stream is invalid")
    ui_font, original_length = stream
    if len(ui_font) != UI_FONT_DECOMPRESSED_SIZE:
        raise TextStructureError("item UI font decompressed size mismatch")
    ui_font_buffer = bytearray(ui_font)
    writes: list[dict[str, object]] = []
    for character, raw in CUSTOM_RAW_BY_CHARACTER.items():
        source = extract_glyph_pixels(rom, hangul_to_game_code(character))
        bitmap = fit_bitmap(source)
        tile = raw - 0x10
        ui_start = tile * 32
        ui_font_buffer[ui_start:ui_start + 32] = pack_ui_tile(bitmap)

        compact_code = _table_halfword(rom, ASCII_CONVERSION_TABLE, raw - 0x20)
        compact_index = game_sjis_glyph_index(compact_code)
        compact_start = FONT_OFFSET + compact_index * GLYPH_SIZE
        result[compact_start:compact_start + GLYPH_SIZE] = pack_compact_glyph(bitmap)
        writes.append(
            {
                "character": character,
                "raw_hex": f"{raw:02X}",
                "ui_tile": tile,
                "compact_code_hex": f"{compact_code:04X}",
                "compact_font_offset": compact_start,
            }
        )

    compressed = compress_lz77(bytes(ui_font_buffer))
    if decompress_lz77_stream(compressed, 0, 0x10000)[0] != bytes(ui_font_buffer):
        raise TextStructureError("recompressed item UI font does not round-trip")
    original_end = UI_FONT_LZ77_OFFSET + original_length
    if any(rom[original_end:UI_FONT_RESERVED_END]):
        raise TextStructureError("item UI font padding window is not empty")
    available = UI_FONT_RESERVED_END - UI_FONT_LZ77_OFFSET
    if len(compressed) > available:
        raise TextStructureError(
            f"recompressed item UI font is 0x{len(compressed):X}, exceeds 0x{available:X}-byte source window"
        )
    result[UI_FONT_LZ77_OFFSET:UI_FONT_LZ77_OFFSET + len(compressed)] = compressed
    writes.insert(
        0,
        {
            "asset_offset": UI_FONT_LZ77_OFFSET,
            "original_compressed_length": original_length,
            "available_length": available,
            "new_compressed_length": len(compressed),
            "decompressed_size": len(ui_font_buffer),
        },
    )
    return bytes(result), writes
