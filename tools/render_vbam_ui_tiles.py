#!/usr/bin/env python3
"""Render UI tile candidates from a gzip-compressed VBA-M state for analysis."""

from __future__ import annotations

import argparse
import gzip
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def locate_iwram(state: bytes) -> int:
    candidates = []
    for base in range(0, len(state) - 0x8000):
        left, right = struct.unpack_from("<II", state, base + 0x4C)
        if 0x06000000 <= left < 0x06018000 and 0x06000000 <= right < 0x06018000:
            candidates.append(base)
    if not candidates:
        raise ValueError("IWRAM base was not found")
    return candidates[0]


def render_tile(draw: ImageDraw.ImageDraw, raw: bytes, x0: int, y0: int, scale: int) -> None:
    if len(raw) != 32:
        raise ValueError("truncated 4bpp tile")
    for y in range(8):
        for x in range(8):
            packed = raw[y * 4 + x // 2]
            pixel = (packed >> (4 * (x & 1))) & 0xF
            if pixel:
                shade = 0 if pixel >= 8 else 80
                draw.rectangle(
                    (x0 + x * scale, y0 + y * scale, x0 + (x + 1) * scale - 1, y0 + (y + 1) * scale - 1),
                    fill=(shade, shade, shade),
                )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--block", type=int, choices=range(4))
    parser.add_argument("--scale", type=int, default=4)
    parser.add_argument("--first-tile", type=lambda value: int(value, 16), default=0x10)
    parser.add_argument("--last-tile", type=lambda value: int(value, 16), default=0xAF)
    args = parser.parse_args()
    state = gzip.decompress(args.state.read_bytes())
    iwram = locate_iwram(state)
    vram = iwram + 0x8000 + 0x400 + 0x40000
    scale = args.scale
    cell_w, cell_h = 8 * scale + 16, 8 * scale + 20
    columns = 16
    first, last = args.first_tile, args.last_tile + 1
    if not 0 <= first < last <= 0x400:
        raise SystemExit("ERROR: invalid tile range")
    rows_per_block = (last - first + columns - 1) // columns
    section_h = 28 + rows_per_block * cell_h
    blocks = [args.block] if args.block is not None else list(range(4))
    image = Image.new("RGB", (columns * cell_w, len(blocks) * section_h), "white")
    draw = ImageDraw.Draw(image)
    label_font = ImageFont.load_default()
    for section, block in enumerate(blocks):
        section_y = section * section_h
        draw.text((4, section_y + 4), f"charblock {block} / VRAM +0x{block * 0x4000:04X}", fill="black", font=label_font)
        for tile_id in range(first, last):
            position = tile_id - first
            x0 = (position % columns) * cell_w
            y0 = section_y + 28 + (position // columns) * cell_h
            offset = vram + block * 0x4000 + tile_id * 32
            render_tile(draw, state[offset:offset + 32], x0, y0, scale)
            draw.text((x0, y0 + 33), f"{tile_id:02X}", fill="black", font=label_font)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output)
    print(f"OK: IWRAM snapshot offset=0x{iwram:X}, VRAM snapshot offset=0x{vram:X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
