#!/usr/bin/env python3
"""Partition relocation-survey candidates without adopting them as text.

The full row catalog contains source text and therefore stays under
``analysis/private``.  Only aggregate counts and source identities are written
to the tracked summary.  A candidate becomes product input only after its
consumer and record bounds are independently proved.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import struct
from collections import Counter, defaultdict
from pathlib import Path

from narikiri2_text_spec import (
    BASELINE_SHA256,
    ITEM_RECORD_COUNT,
    ITEM_RECORD_SIZE,
    ITEM_TABLE_OFFSET,
    JAPANESE_SHA256,
)
from source_profiles import source_profile


JOB_TABLE_OFFSET = 0x2B580C
JOB_RECORD_SIZE = 0x40
JOB_RECORD_COUNT = 201
JOB_COMPACT_POINTER_OFFSET = 0x04
MONSTER_TABLE_OFFSET = 0x2BF4D4
MONSTER_RECORD_SIZE = 0x34
MONSTER_RECORD_COUNT = 165
COMPACT_TARGET_MIN = 0x950000
COMPACT_TARGET_MAX = 0x960000


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require_hash(data: bytes, expected: str, label: str) -> None:
    actual = digest(data)
    if actual != expected:
        raise ValueError(f"{label} SHA-256 {actual} does not match {expected}")


def read_string_at_pointer(rom: bytes, storage: int) -> tuple[int, bytes]:
    if storage < 0 or storage + 4 > len(rom):
        raise ValueError(f"pointer storage 0x{storage:X} is outside ROM")
    pointer = struct.unpack_from("<I", rom, storage)[0]
    if not 0x08000000 <= pointer < 0x08000000 + len(rom):
        raise ValueError(f"pointer at 0x{storage:X} is outside ROM: 0x{pointer:08X}")
    target = pointer - 0x08000000
    end = rom.find(b"\0", target, min(target + 4096, len(rom)))
    if end < 0:
        raise ValueError(f"unterminated string at 0x{target:X}")
    return target, rom[target:end]


def known_compact_storages() -> dict[int, str]:
    known = {}
    for index in range(JOB_RECORD_COUNT):
        known[JOB_TABLE_OFFSET + index * JOB_RECORD_SIZE + JOB_COMPACT_POINTER_OFFSET] = "JOB"
    for index in range(MONSTER_RECORD_COUNT):
        known[MONSTER_TABLE_OFFSET + index * MONSTER_RECORD_SIZE] = "MONSTER"
    for index in range(ITEM_RECORD_COUNT):
        known[ITEM_TABLE_OFFSET + index * ITEM_RECORD_SIZE] = "ITEM"
    if len(known) != 523:
        raise AssertionError("known compact field denominator changed")
    return known


def known_compact_labels() -> dict[int, str]:
    labels = {}
    for index in range(JOB_RECORD_COUNT):
        labels[JOB_TABLE_OFFSET + index * JOB_RECORD_SIZE + JOB_COMPACT_POINTER_OFFSET] = f"JOB_{index:03d}"
    for index in range(MONSTER_RECORD_COUNT):
        labels[MONSTER_TABLE_OFFSET + index * MONSTER_RECORD_SIZE] = f"MONSTER_{index:03d}"
    for index in range(ITEM_RECORD_COUNT):
        labels[ITEM_TABLE_OFFSET + index * ITEM_RECORD_SIZE] = f"ITEM_{index:03d}"
    return labels


def partition_rows(rows: list[dict[str, str]]) -> dict[str, object]:
    compact = [
        row for row in rows
        if COMPACT_TARGET_MIN <= int(row["kr_target_hex"], 16) < COMPACT_TARGET_MAX
    ]
    known = known_compact_storages()
    by_target: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in compact:
        by_target[row["kr_target_hex"]].append(row)
    known_refs = [row for row in compact if int(row["storage_hex"], 16) in known]
    known_targets = {row["kr_target_hex"] for row in known_refs}
    residual_refs = [row for row in compact if int(row["storage_hex"], 16) not in known]
    residual_targets = {row["kr_target_hex"] for row in residual_refs}
    return {
        "compact": compact,
        "by_target": by_target,
        "known_refs": known_refs,
        "known_targets": known_targets,
        "residual_refs": residual_refs,
        "residual_targets": residual_targets,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--survey", type=Path,
                        default=root / "analysis/expanded_pointer_survey.csv")
    parser.add_argument("--baseline-rom", type=Path,
                        default=root / "output/NARIKIRI2_AN9J_K_EEPROM_RESTORED.gba")
    parser.add_argument("--japanese-rom", type=Path, required=True)
    parser.add_argument("--english-reference-rom", type=Path)
    parser.add_argument("--private-catalog", type=Path,
                        default=root / "analysis/private/compact_target_candidates.csv")
    parser.add_argument("--summary", type=Path,
                        default=root / "analysis/compact_target_catalog_summary.json")
    args = parser.parse_args()

    baseline = args.baseline_rom.read_bytes()
    japanese = args.japanese_rom.read_bytes()
    require_hash(baseline, BASELINE_SHA256, "Candidate A")
    require_hash(japanese, JAPANESE_SHA256, "Japanese ROM")
    english = args.english_reference_rom.read_bytes() if args.english_reference_rom else None
    english_profile = source_profile("ND2_EN_V230_APPLIED")
    if english is not None:
        require_hash(english, english_profile.sha256, "English v2.30 reference ROM")

    with args.survey.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    parts = partition_rows(rows)
    known = known_compact_storages()
    labels = known_compact_labels()

    private_rows = []
    english_valid_refs = 0
    for ordinal, (target, uses) in enumerate(sorted(parts["by_target"].items()), 1):
        storages = sorted(int(row["storage_hex"], 16) for row in uses)
        categories = sorted({known[s] for s in storages if s in known})
        jp_texts = sorted({row["jp_decode_hypothesis"] for row in uses})
        en_texts: set[str] = set()
        if english is not None:
            for storage in storages:
                try:
                    _, raw = read_string_at_pointer(english, storage)
                    en_texts.add(raw.decode("cp932"))
                    english_valid_refs += 1
                except (ValueError, UnicodeDecodeError):
                    pass
        private_rows.append({
            "candidate_id": f"COMPACT_CANDIDATE_{ordinal:04d}",
            "kr_target_hex": target,
            "reference_count": len(uses),
            "storage_hexes": ";".join(f"{value:08X}" for value in storages),
            "known_categories": ";".join(categories),
            "japanese_context": " | ".join(jp_texts),
            "english_reference_context": " | ".join(sorted(en_texts)),
            "kr_raw_hex": uses[0]["kr_raw_hex"],
            "status": (
                "KNOWN_TABLE_FIELD" if categories
                else "CONSUMER_UNCLASSIFIED_NOT_PRODUCT_INPUT"
            ),
        })

    args.private_catalog.parent.mkdir(parents=True, exist_ok=True)
    with args.private_catalog.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(private_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(private_rows)

    category_refs = Counter(known[int(row["storage_hex"], 16)] for row in parts["known_refs"])
    summary = {
        "schema": "narikiri2-compact-target-catalog-summary-v1",
        "evidence_kind": "SURVEY_PARTITION_ONLY_NOT_COMPLETE_EXTRACTION",
        "source_profiles": {
            "baseline": "AN9J_CANDIDATE_A",
            "japanese": "AN9J_JP_REV0",
            "english_reference": "ND2_EN_V230_APPLIED" if english is not None else None,
        },
        "aligned_changed_pointer_candidates": len(rows),
        "compact_candidate_references": len(parts["compact"]),
        "compact_candidate_unique_targets": len(parts["by_target"]),
        "known_table_field_denominator": len(known),
        "known_table_references_found": len(parts["known_refs"]),
        "known_table_fields_absent_from_changed_pointer_survey": sorted(
            labels[storage]
            for storage in known
            if storage not in {int(row["storage_hex"], 16) for row in parts["known_refs"]}
        ),
        "known_table_reference_categories": dict(sorted(category_refs.items())),
        "known_table_unique_targets": len(parts["known_targets"]),
        "consumer_unclassified_references": len(parts["residual_refs"]),
        "consumer_unclassified_unique_targets": len(parts["residual_targets"]),
        "english_reference_valid_pointer_reads": english_valid_refs if english is not None else None,
        "private_catalog": "analysis/private/compact_target_candidates.csv (ignored; regenerate locally)",
        "adoption_policy": "A survey row is not product input until its consumer, bounds, and rendering path are proved.",
        "status": "BANKWIDE_DENOMINATOR_NOT_CLOSED",
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
