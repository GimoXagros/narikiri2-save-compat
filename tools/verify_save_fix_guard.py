#!/usr/bin/env python3
"""Verify that a cumulative AN9J ROM still contains the adopted EEPROM repair."""

from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path

from save_fix_spec import EXPECTED_WRITES, OUTPUT_SIZE
from verify_inputs import gba_header_checksum, header_fields


EEPROM_TAG_OFFSET = 0x3741D8
EEPROM_DESCRIPTOR_OFFSET = 0x3741F0


class SaveFixGuardError(ValueError):
    """Raised when an artifact violates a protected save invariant."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SaveFixGuardError(message)


def verify_save_fix_bytes(rom: bytes, *, expected_size: int = OUTPUT_SIZE) -> dict[str, object]:
    require(len(rom) == expected_size, f"ROM size is 0x{len(rom):X}, expected 0x{expected_size:X}")
    for write in EXPECTED_WRITES:
        actual = rom[write.offset:write.end]
        require(actual == write.final_bytes, f"{write.write_id} protected bytes changed")

    require(rom.find(b"EEPROM_V122") == EEPROM_TAG_OFFSET, "EEPROM_V122 moved or disappeared")
    require(rom.count(b"EEPROM_V122") == 1, "EEPROM_V122 count changed")
    require(
        struct.unpack_from("<I", rom, EEPROM_DESCRIPTOR_OFFSET)[0] == 0x2000,
        "EEPROM descriptor logical size changed",
    )
    require(
        struct.unpack_from("<H", rom, EEPROM_DESCRIPTOR_OFFSET + 4)[0] == 0x0400,
        "EEPROM descriptor block count changed",
    )
    require(rom[EEPROM_DESCRIPTOR_OFFSET + 8] == 0x0E, "EEPROM descriptor address bits changed")
    require(struct.unpack_from('<I',rom,0xA1E4)[0]==0x089513E8,
            'Aligned save-signature pointer changed')
    require(rom[0x9513E8:0x9513F0]==b'NARIKIRI','Eight-byte save signature changed')

    fields = header_fields(rom[:0xC0])
    require(fields["title"] == "NARIKIRI2", "GBA title changed")
    require(fields["game_code"] == "AN9J", "game code changed")
    require(fields["maker_code"] == "AF", "maker code changed")
    require(fields["version"] == 0, "revision changed")
    require(fields["checksum_stored"] == 0x2D, "stored header checksum changed")
    require(gba_header_checksum(rom[:0xC0]) == 0x2D, "calculated header checksum changed")

    return {
        "size": len(rom),
        "sha256": hashlib.sha256(rom).hexdigest(),
        "game_code": fields["game_code"],
        "protected_window_count": len(EXPECTED_WRITES),
        "save_signature": "PASS: original aligned CpuSet source",
        "status": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify_save_fix_bytes(args.rom.read_bytes())
    except (OSError, SaveFixGuardError) as error:
        raise SystemExit(f"ERROR: {error}") from error
    print(f"OK: save-fix guard PASS for {args.rom.name}")
    print(f"OK: size=0x{result['size']:X} sha256={result['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
