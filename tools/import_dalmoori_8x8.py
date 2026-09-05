#!/usr/bin/env python3
"""Import deterministic 8x8 bitmaps from the pinned Dalmoori generator output."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import unicodedata


PINNED_COMMIT = "897f0e71224d9964a84b888f2596b2bfd7f98def"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_checkout(checkout: Path) -> None:
    actual = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if actual != PINNED_COMMIT:
        raise ValueError(f"Dalmoori checkout is {actual}, expected {PINNED_COMMIT}")
    if not (checkout / "LICENSE").is_file():
        raise ValueError("Pinned Dalmoori LICENSE is missing")


def parse_generated_glyph(path: Path) -> tuple[int, int, bool, tuple[str, ...]]:
    lines = tuple("".join(c for c in line if c in "#.") for line in path.read_text(encoding="utf-8").splitlines())
    lines = tuple(line for line in lines if line)
    if not lines or len({len(line) for line in lines}) != 1:
        raise ValueError(f"Malformed generated glyph: {path}")
    width, height = len(lines[0]), len(lines)
    if (width, height) not in ((4, 8), (8, 8)):
        raise ValueError(f"Unsupported Dalmoori glyph geometry {width}x{height}: {path}")
    if any(set(line) - {"#", "."} for line in lines):
        raise ValueError(f"Non-binary pixel in {path}")
    return width, height, width == 4, lines


def generated_path(checkout: Path, character: str) -> Path:
    code = f"{ord(character):04X}"
    return checkout / "generator" / "build" / "ascii-font" / code[:2] / f"{code}.txt"


def import_characters(checkout: Path, output: Path, characters: list[str]) -> list[dict[str, str]]:
    verify_checkout(checkout)
    normalized = sorted({unicodedata.normalize("NFC", c) for c in characters}, key=ord)
    if any(len(c) != 1 for c in normalized):
        raise ValueError("Every requested glyph must normalize to one Unicode scalar")
    glyph_dir = output / "glyphs"
    glyph_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for character in normalized:
        source = generated_path(checkout, character)
        if not source.is_file():
            raise ValueError(f"Missing generated Dalmoori glyph U+{ord(character):04X}")
        width, height, halfwidth, bitmap = parse_generated_glyph(source)
        body = "\n".join(bitmap) + "\n"
        destination = glyph_dir / f"U+{ord(character):04X}.txt"
        destination.write_text(body, encoding="utf-8", newline="\n")
        rows.append({
            "unicode": f"U+{ord(character):04X}", "character": character,
            "source_commit": PINNED_COMMIT,
            "source_path_or_composition": source.relative_to(checkout).as_posix(),
            "width": str(width), "height": str(height),
            "halfwidth": str(halfwidth).lower(),
            "bitmap_sha256": sha256(body.encode("utf-8")),
            "used_by_game_codes": "PENDING_FINAL_MAPPING",
        })
    manifest = output / "glyph_manifest.csv"
    with manifest.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--characters", required=True, help="Unicode characters to import")
    args = parser.parse_args()
    rows = import_characters(args.checkout.resolve(), args.output.resolve(), list(args.characters))
    print(json.dumps({"status": "PASS", "source_commit": PINNED_COMMIT, "glyphs": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
