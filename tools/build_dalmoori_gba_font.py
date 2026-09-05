#!/usr/bin/env python3
"""Pack imported Dalmoori bitmaps into verified GBA 4bpp 8x8 tiles."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def read_bitmap(path: Path) -> list[list[int]]:
    rows = [[1 if c == "#" else 0 for c in line.strip()] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 8 or any(len(row) not in (4, 8) for row in rows) or len({len(row) for row in rows}) != 1:
        raise ValueError(f"Unsupported bitmap geometry: {path}")
    return rows


def place(bitmap: list[list[int]], width: int = 8, x_offset: int = 0, y_offset: int = 0) -> list[list[int]]:
    if not 0 <= x_offset <= width - len(bitmap[0]) or not 0 <= y_offset <= 8 - len(bitmap):
        raise ValueError("Glyph offset exceeds the 8x8 cell")
    result = [[0] * width for _ in range(8)]
    for y, row in enumerate(bitmap):
        result[y + y_offset][x_offset:x_offset + len(row)] = row
    return result


def pack_4bpp(bitmap: list[list[int]], clear_index: int, ink_index: int) -> bytes:
    if not 0 <= clear_index < 16 or not 0 <= ink_index < 16 or clear_index == ink_index:
        raise ValueError("Palette indices must be distinct 4-bit values")
    output = bytearray(32)
    for y, row in enumerate(bitmap):
        for x, pixel in enumerate(row):
            value = ink_index if pixel else clear_index
            output[y * 4 + x // 2] |= value << (4 * (x & 1))
    return bytes(output)


def unpack_4bpp(tile: bytes, clear_index: int, ink_index: int) -> list[list[int]]:
    if len(tile) != 32:
        raise ValueError("A 4bpp 8x8 tile must contain 32 bytes")
    result = []
    for y in range(8):
        row = []
        for x in range(8):
            value = tile[y * 4 + x // 2] >> (4 * (x & 1)) & 0xF
            if value not in (clear_index, ink_index):
                raise ValueError("Packed tile contains an unapproved palette index")
            row.append(int(value == ink_index))
        result.append(row)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--glyph-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--clear-index", type=lambda x: int(x, 0), default=0)
    parser.add_argument("--ink-index", type=lambda x: int(x, 0), default=15)
    parser.add_argument("--halfwidth-x-offset", type=int, default=0)
    args = parser.parse_args()
    paths = sorted(args.glyph_dir.glob("U+*.txt"))
    if not paths:
        raise ValueError("No imported glyphs found")
    result = bytearray()
    for path in paths:
        source = read_bitmap(path)
        bitmap = place(source, x_offset=args.halfwidth_x_offset if len(source[0]) == 4 else 0)
        tile = pack_4bpp(bitmap, args.clear_index, args.ink_index)
        if unpack_4bpp(tile, args.clear_index, args.ink_index) != bitmap:
            raise ValueError(f"4bpp round-trip failed: {path}")
        result += tile
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)
    print(json.dumps({"status": "PASS", "tiles": len(paths), "bytes": len(result),
                      "sha256": hashlib.sha256(result).hexdigest()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
