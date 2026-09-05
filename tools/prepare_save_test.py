#!/usr/bin/env python3
"""Create content-verified, isolated ROM copies for clean save testing."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from verify_inputs import PROFILES, find_inputs
from save_fix_spec import EXPECTED_OUTPUT_SHA256, OUTPUT_SIZE


FORBIDDEN_SUFFIXES = {
    ".sav", ".ss0", ".ss1", ".ss2", ".ss3", ".ss4",
    ".ss5", ".ss6", ".ss7", ".ss8", ".ss9",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_clean(case_dir: Path, basename: str) -> list[str]:
    unwanted: list[str] = []
    for path in case_dir.iterdir():
        lower_name = path.name.lower()
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            unwanted.append(path.name)
        elif lower_name.startswith(basename.lower()) and lower_name != f"{basename.lower()}.gba":
            unwanted.append(path.name)
    if unwanted:
        raise RuntimeError(f"case is not clean: {case_dir}: {unwanted}")
    return sorted(path.name for path in case_dir.iterdir())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("."))
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--test-root", type=Path, default=Path("output/save-tests"))
    parser.add_argument("--run-id")
    args = parser.parse_args()

    inputs, input_errors = find_inputs(args.input_dir)
    if input_errors:
        raise RuntimeError("input verification failed: " + "; ".join(input_errors))
    profiles = {profile.profile_id: profile for profile in PROFILES}
    jp_profile = profiles["AN9J_J"]
    kr_profile = profiles["AN9J_K_FFR"]
    jp = inputs[jp_profile.profile_id]["path"]
    kr = inputs[kr_profile.profile_id]["path"]
    candidate = args.candidate.resolve()
    if candidate.stat().st_size != OUTPUT_SIZE or sha256(candidate) != EXPECTED_OUTPUT_SHA256:
        raise RuntimeError("candidate size or SHA-256 does not match the adopted Candidate A")

    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.test_root.resolve() / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    cases = [
        ("japanese", jp, jp_profile.sha256),
        ("korean_existing", kr, kr_profile.sha256),
        ("candidate_a", candidate, EXPECTED_OUTPUT_SHA256),
    ]
    manifest = {
        "schema": "narikiri2-clean-save-test-v1",
        "run_id": run_id,
        "prepared_utc": datetime.now(timezone.utc).isoformat(),
        "savestate_policy": "none; boot only from ROM power-on",
        "cases": [],
    }
    for case_id, source, expected_hash in cases:
        case_dir = run_dir / case_id
        case_dir.mkdir()
        rom = case_dir / f"{case_id}.gba"
        shutil.copyfile(source, rom)
        actual_hash = sha256(rom)
        if actual_hash != expected_hash:
            raise RuntimeError(f"copy verification failed for {case_id}")
        listing = assert_clean(case_dir, case_id)
        manifest["cases"].append({
            "case_id": case_id,
            "source_name": source.name,
            "rom": str(rom),
            "rom_size": rom.stat().st_size,
            "rom_sha256": actual_hash,
            "prelaunch_listing": listing,
            "prelaunch_sav_present": False,
            "runtime_status": "NOT VERIFIED",
        })

    manifest_path = run_dir / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: prepared clean test run {run_dir}")
    for case in manifest["cases"]:
        print(f"OK: {case['case_id']}: no .sav/savestate; {case['rom_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
