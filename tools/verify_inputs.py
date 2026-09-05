#!/usr/bin/env python3
"""Identify and verify the two supported AN9J ROM inputs without modifying them."""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

from source_profiles import source_profile


@dataclass(frozen=True)
class Profile:
    profile_id: str
    description: str
    size: int
    sha256: str


_JP = source_profile("AN9J_JP_REV0")
_FFR = source_profile("AN9J_FFR_K")
PROFILES = (
    Profile(
        "AN9J_J",
        "Japanese source ROM",
        _JP.size,
        _JP.sha256,
    ),
    Profile(
        "AN9J_K_FFR",
        "Existing Korean-patched ROM",
        _FFR.size,
        _FFR.sha256,
    ),
)


def digest_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def gba_header_checksum(header: bytes) -> int:
    if len(header) < 0xBE:
        raise ValueError("file is too short to contain a GBA header")
    return (-(sum(header[0xA0:0xBD]) + 0x19)) & 0xFF


def read_header(path: Path) -> bytes:
    with path.open("rb") as source:
        return source.read(0xC0)


def header_fields(header: bytes) -> dict[str, object]:
    return {
        "title_raw": header[0xA0:0xAC],
        "title": header[0xA0:0xAC].rstrip(b"\0").decode("ascii", errors="replace"),
        "game_code": header[0xAC:0xB0].decode("ascii", errors="replace"),
        "maker_code": header[0xB0:0xB2].decode("ascii", errors="replace"),
        "version": header[0xBC],
        "checksum_stored": header[0xBD],
        "checksum_calculated": gba_header_checksum(header),
    }


def validate_header(path: Path, fields: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if fields["title_raw"].rstrip(b"\0") != b"NARIKIRI2":
        errors.append(f"{path.name}: title is {fields['title']!r}, expected 'NARIKIRI2'")
    if fields["game_code"] != "AN9J":
        errors.append(f"{path.name}: game code is {fields['game_code']!r}, expected 'AN9J'")
    if fields["maker_code"] != "AF":
        errors.append(f"{path.name}: maker code is {fields['maker_code']!r}, expected 'AF'")
    if fields["version"] != 0:
        errors.append(f"{path.name}: version is {fields['version']}, expected 0")
    if fields["checksum_stored"] != 0x2D:
        errors.append(
            f"{path.name}: stored header checksum is 0x{fields['checksum_stored']:02X}, expected 0x2D"
        )
    if fields["checksum_calculated"] != 0x2D:
        errors.append(
            f"{path.name}: calculated header checksum is 0x{fields['checksum_calculated']:02X}, expected 0x2D"
        )
    if fields["checksum_stored"] != fields["checksum_calculated"]:
        errors.append(f"{path.name}: stored and calculated header checksums differ")
    return errors


def find_inputs(input_dir: Path) -> tuple[dict[str, dict[str, object]], list[str]]:
    results: dict[str, dict[str, object]] = {}
    errors: list[str] = []
    candidates = sorted(path for path in input_dir.glob("*.gba") if path.is_file())
    for path in candidates:
        size = path.stat().st_size
        size_profiles = [profile for profile in PROFILES if profile.size == size]
        if not size_profiles:
            continue
        digest = digest_file(path)
        for profile in size_profiles:
            if digest != profile.sha256:
                continue
            if profile.profile_id in results:
                errors.append(
                    f"duplicate content for {profile.profile_id}: "
                    f"{results[profile.profile_id]['path']} and {path}"
                )
                continue
            header = header_fields(read_header(path))
            errors.extend(validate_header(path, header))
            results[profile.profile_id] = {
                "profile": profile,
                "path": path.resolve(),
                "size": size,
                "sha256": digest,
                "header": header,
            }
    for profile in PROFILES:
        if profile.profile_id not in results:
            errors.append(
                f"missing supported input {profile.profile_id}: "
                f"size=0x{profile.size:X}, sha256={profile.sha256}"
            )
    return results, errors


def render_report(
    input_dir: Path,
    results: dict[str, dict[str, object]],
    errors: list[str],
) -> str:
    lines = [
        "# AN9J input verification",
        "",
        "Input directory: local project root (absolute path intentionally omitted)",
        "",
        f"Overall result: **{'PASS' if not errors else 'FAIL'}**",
        "",
        "Identification uses byte length and SHA-256. Filenames are not trusted.",
        "",
    ]
    for profile in PROFILES:
        lines.extend([f"## {profile.profile_id}", ""])
        result = results.get(profile.profile_id)
        if result is None:
            lines.extend(["Result: **NOT FOUND**", ""])
            continue
        header = result["header"]
        lines.extend(
            [
                f"- Description: {profile.description}",
                f"- Filename: `{Path(result['path']).name}`",
                f"- Size: `{result['size']}` (`0x{result['size']:X}`)",
                f"- SHA-256: `{result['sha256']}`",
                f"- Title: `{header['title']}`",
                f"- Game code: `{header['game_code']}`",
                f"- Maker code: `{header['maker_code']}`",
                f"- Version: `{header['version']}`",
                f"- Stored header checksum: `0x{header['checksum_stored']:02X}`",
                f"- Calculated header checksum: `0x{header['checksum_calculated']:02X}`",
                "",
            ]
        )
    if errors:
        lines.extend(["## Errors", ""])
        lines.extend(f"- {error}" for error in errors)
        lines.append("")
    else:
        lines.extend(
            [
                "## Conclusion",
                "",
                "Both immutable inputs match the adopted AN9J profiles. Static analysis may proceed.",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    results, errors = find_inputs(args.input_dir)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(args.input_dir, results, errors), encoding="utf-8")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    for profile in PROFILES:
        result = results[profile.profile_id]
        print(
            f"OK {profile.profile_id}: size=0x{result['size']:X} "
            f"sha256={result['sha256']} path={result['path']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
