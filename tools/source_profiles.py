"""Load the single adopted AN9J source-profile registry."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class SourceProfile:
    profile_id: str
    size: int
    sha256: str
    game_code: str | None
    role: str
    reference_only: bool


@lru_cache(maxsize=1)
def load_source_profiles() -> dict[str, SourceProfile]:
    path = Path(__file__).resolve().parents[1] / "config" / "source_profiles.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    profiles: dict[str, SourceProfile] = {}
    for section, reference_only in (("profiles", False), ("reference_only", True)):
        for row in payload.get(section, []):
            profile = SourceProfile(
                profile_id=row["id"],
                size=int(row["size"]),
                sha256=row["sha256"].lower(),
                game_code=row.get("game_code"),
                role=row["role"],
                reference_only=reference_only,
            )
            if profile.profile_id in profiles:
                raise ValueError(f"duplicate source profile id: {profile.profile_id}")
            profiles[profile.profile_id] = profile
    return profiles


def source_profile(profile_id: str) -> SourceProfile:
    try:
        return load_source_profiles()[profile_id]
    except KeyError as exc:
        raise KeyError(f"unknown source profile id: {profile_id}") from exc
