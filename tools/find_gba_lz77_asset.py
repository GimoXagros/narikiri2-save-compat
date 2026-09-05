#!/usr/bin/env python3
"""Find GBA LZ77 streams whose output contains a VRAM byte sample."""

from __future__ import annotations

import argparse
import gzip
from pathlib import Path

def decompress_lz77_stream(data: bytes, start: int, maximum: int) -> tuple[bytes, int] | None:
    if start + 4 > len(data) or data[start] != 0x10:
        return None
    size = int.from_bytes(data[start + 1:start + 4], "little")
    if not 0 < size <= maximum:
        return None
    source = start + 4
    output = bytearray()
    try:
        while len(output) < size:
            flags = data[source]
            source += 1
            for bit in range(7, -1, -1):
                if len(output) >= size:
                    break
                if flags & (1 << bit):
                    left, right = data[source], data[source + 1]
                    source += 2
                    length = (left >> 4) + 3
                    distance = ((left & 0x0F) << 8 | right) + 1
                    if distance > len(output):
                        return None
                    for _ in range(length):
                        output.append(output[-distance])
                        if len(output) >= size:
                            break
                else:
                    output.append(data[source])
                    source += 1
        return bytes(output), source - start
    except IndexError:
        return None


def decompress_lz77(data: bytes, start: int, maximum: int) -> bytes | None:
    result = decompress_lz77_stream(data, start, maximum)
    return result[0] if result is not None else None


def main() -> int:
    from render_vbam_ui_tiles import locate_iwram

    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--tile", type=lambda value: int(value, 16), default=0x31)
    parser.add_argument("--tile-count", type=int, default=8)
    parser.add_argument("--maximum-output", type=lambda value: int(value, 0), default=0x20000)
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    state = gzip.decompress(args.state.read_bytes())
    iwram = locate_iwram(state)
    vram = iwram + 0x8000 + 0x400 + 0x40000
    start = vram + 0xC000 + args.tile * 32
    sample = state[start:start + args.tile_count * 32]
    matches: list[tuple[int, int, int]] = []
    for offset, value in enumerate(rom):
        if value != 0x10:
            continue
        decompressed = decompress_lz77(rom, offset, args.maximum_output)
        if decompressed is None:
            continue
        position = decompressed.find(sample)
        if position >= 0:
            matches.append((offset, len(decompressed), position))
    for offset, size, position in matches:
        print(f"0x{offset:08X}\toutput=0x{size:X}\tsample=0x{position:X}")
    print(f"matches={len(matches)}")
    return 0 if matches else 1


if __name__ == "__main__":
    raise SystemExit(main())
