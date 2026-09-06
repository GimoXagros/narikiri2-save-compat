# Remaining product verification

Repository consolidation preserves v0.9a; it does not satisfy v1.0 promotion.

Tracked as [canonical issue #4](https://github.com/GimoXagros/narikiri2-save-compat/issues/4). This is a new consolidation follow-up, not a fabricated transfer of a legacy issue; the legacy repository had no issues.

- Run the exact v0.9a ROM on the target GBARunner3/hardware configuration, including new game, two cold reloads, existing 8 KiB saves, custom names and suspend/resume. Record ROM, loader, firmware and hardware identities. Older Candidate A hardware observations cannot establish this result.
- Complete a long playthrough and branch/event coverage. Current runtime samples do not prove every encounter, unlock, dialogue branch or technique works in natural progression.
- Expand reproducible controller routes for the current product. The generic `tools/libretro_probe.py` host is now in this repository with explicit local core/ROM/save arguments. Historical diagnostic-specific matrix/replay drivers and recordings remain indexed in the private archive; they are not current build inputs or automatic acceptance results.
- If links in unrelated project portals still point at the old repository or v0.5, handle them as separate work in those repositories. This integration does not modify them.

Priority: hardware/save verification and long-play coverage before v1.0. Route expansion supports those checks; it does not block the unchanged v0.9a public verification release.

The imported runtime-event validator rejects different ROM/core identities, absent close events, fixture operations presented as clean play, wrong save size and rewound frames. Its default hashes identify an old test fixture. Supply current expected hashes explicitly. The validator checks provenance only; inspect the resulting screens and gameplay separately.
