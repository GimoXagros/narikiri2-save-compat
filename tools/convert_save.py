#!/usr/bin/env python3
"""Convert verified AN9J save containers without modifying the source file."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import tempfile
from pathlib import Path


EEPROM_SIZE = 8192
VBAM_SRAM_SIZE = 32768
SIGNATURE = b"IRIKIRAN"
FORMAT_EEPROM = "eeprom8k"
FORMAT_VBAM = "vbam-sram32k"


class SaveFormatError(ValueError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_format(data: bytes, format_name: str) -> None:
    if format_name == FORMAT_EEPROM:
        if len(data) != EEPROM_SIZE:
            raise SaveFormatError(f"{FORMAT_EEPROM} requires exactly {EEPROM_SIZE} bytes")
        if data[:8] != SIGNATURE:
            raise SaveFormatError(f"{FORMAT_EEPROM} is missing the AN9J physical signature")
        return
    if format_name == FORMAT_VBAM:
        if len(data) != VBAM_SRAM_SIZE:
            raise SaveFormatError(f"{FORMAT_VBAM} requires exactly {VBAM_SRAM_SIZE} bytes")
        if data[:8] != SIGNATURE:
            raise SaveFormatError(f"{FORMAT_VBAM} is missing the AN9J physical signature")
        if data[EEPROM_SIZE:] != b"\xFF" * (VBAM_SRAM_SIZE - EEPROM_SIZE):
            raise SaveFormatError(f"{FORMAT_VBAM} has non-FF data outside the first 8 KiB")
        return
    raise SaveFormatError(f"unsupported format: {format_name}")


def detect_format(data: bytes) -> str:
    matches: list[str] = []
    for format_name in (FORMAT_EEPROM, FORMAT_VBAM):
        try:
            validate_format(data, format_name)
        except SaveFormatError:
            continue
        matches.append(format_name)
    if len(matches) != 1:
        raise SaveFormatError(f"could not uniquely detect format; matches={matches}")
    return matches[0]


def convert_bytes(data: bytes, source_format: str, target_format: str) -> bytes:
    validate_format(data, source_format)
    if source_format == target_format:
        return data
    if source_format == FORMAT_VBAM and target_format == FORMAT_EEPROM:
        result = data[:EEPROM_SIZE]
    elif source_format == FORMAT_EEPROM and target_format == FORMAT_VBAM:
        result = data + b"\xFF" * (VBAM_SRAM_SIZE - EEPROM_SIZE)
    else:
        raise SaveFormatError(f"unsupported conversion: {source_format} -> {target_format}")
    validate_format(result, target_format)
    return result


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--from", dest="source_format", choices=["auto", FORMAT_EEPROM, FORMAT_VBAM], default="auto")
    parser.add_argument("--to", dest="target_format", choices=[FORMAT_EEPROM, FORMAT_VBAM], required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    source = args.input.resolve()
    output = args.output.resolve()
    if source == output:
        raise SaveFormatError("input and output paths must differ")
    if output.exists() and not args.overwrite:
        raise FileExistsError(f"refusing to overwrite existing output: {output}")

    source_data = source.read_bytes()
    source_format = detect_format(source_data) if args.source_format == "auto" else args.source_format
    validate_format(source_data, source_format)
    result = convert_bytes(source_data, source_format, args.target_format)
    roundtrip = convert_bytes(result, args.target_format, source_format)
    if roundtrip != source_data:
        raise RuntimeError("round-trip conversion did not reproduce the source bytes")

    source_hash = digest(source_data)
    backup = output.with_name(f"{output.stem}.source-{source_hash[:8]}.bak{source.suffix}")
    backup.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists():
        if digest(backup.read_bytes()) != source_hash:
            raise FileExistsError(f"existing backup does not match source: {backup}")
    else:
        shutil.copy2(source, backup)
    atomic_write(output, result)

    print(f"OK: detected source format {source_format}")
    print(f"OK: source backup {backup}")
    print(f"OK: wrote {output} ({len(result)} bytes, sha256={digest(result)})")
    print("OK: inverse round trip reproduced the source byte-for-byte")
    print("RUNTIME STATUS: NOT VERIFIED until the converted save loads and re-saves in game")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
