"""Established 0x08001AC8 name-consumer rules for the fixed AN9J revision.

The 157 fixed names contain no mark/control arguments other than 0x12.
Other controls are deliberately rejected, not silently treated as printable.
This is not a general-purpose UI/dialogue decoder.
"""
from __future__ import annotations

COMPACT_CODE_TEXT = {0x94ED: "골", 0x94EE: "공"}


def decode_verified_compact(code: bytes) -> str:
    if len(code) != 2:
        raise ValueError("Expected exactly one big-endian code unit")
    value = int.from_bytes(code, "big")
    if value not in COMPACT_CODE_TEXT:
        raise ValueError(f"Unverified compact code: {value:04X}")
    return COMPACT_CODE_TEXT[value]


def encode_verified_compact(text: str) -> bytes:
    inverse = {text_value: code for code, text_value in COMPACT_CODE_TEXT.items()}
    if text not in inverse:
        raise ValueError(f"No verified compact code for {text!r}")
    return inverse[text].to_bytes(2, "big")


def tiles_for_name(raw: bytes) -> list[int]:
    mode = 0
    tiles = []
    for index, value in enumerate(raw):
        if value == 0x12:
            mode ^= 1
        elif 0x20 <= value <= 0x7E:
            tiles.append(value - 0x10)
        elif 0xA1 <= value <= 0xDF:
            if value in (0xDE, 0xDF):
                raise ValueError("Dakuten/handakuten require caller mark-mode evidence")
            tiles.append(value + (0x10 if mode else -0x30))
        else:
            raise ValueError(f"Unmodeled item-name byte {value:02X} at {index}")
    return tiles


def name_advance_px(raw: bytes) -> int:
    return 8 * len(tiles_for_name(raw))
