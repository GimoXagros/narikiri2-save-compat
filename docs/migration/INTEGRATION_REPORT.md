# Repository integration report — 2026-09-07

Status: **COMPLETE** for integration code, main merge, independent reproduction and legacy archive. Actual action evidence is maintained in `verification/repository-integration.json` and the archive checklist. This is repository consolidation, not a game-content change or a new release.

## Scope and evidence

Canonical main began at `d1eefbeaf9aa01c55229f28aaf809d4800596c5e` (v0.9a). Legacy main was `9808c76d821add6bf963279a28dee612ee24749b`; the development working tree remained based on `0e18f64a488901a8a565fbcd9da8b7413aa91e10`. All five remote legacy heads, its v0.5 tag and accessible PR refs were mirrored. Local refs, dirty/untracked work and additional worktrees were separately preserved. No unrelated history is imported.

The paginated inventory covered canonical 4 branches / 3 tags / 3 merged PRs / 0 issues / 3 releases / 11 assets, and legacy 5 branches / 1 tag / 1 merged PR / 0 issues / 1 release / 4 assets. There were no open PRs or unresolved review threads. Neither repository had Actions workflows, runs or artifacts at the initial audit. Secrets were not extracted; configuration metadata is private. No Git LFS pointer or submodule tree was found in the accessible history.

REST protection calls on the private legacy repository returned a plan-related 403, retained as an error record. An independent GraphQL query returned empty branch-protection/ruleset connections with `hasNextPage=false`; branch API records also marked every audited branch unprotected. The canonical wiki setting is enabled, but its authenticated Git endpoint returned Repository not found. No wiki data was assumed empty or imported. Legacy wiki is disabled. This unavailable canonical auxiliary endpoint does not conceal any legacy source inventory.

## Migration decisions

The [file table](MIGRATION_TABLE.tsv) has 344 selected code/config/document/data-path rows: 79 content-equivalent existing items, 9 selective imports, 34 superseded items with current counterparts, and 222 private archival items. Generated assets, ROMs, evidence directories and all historical Git objects are additionally covered by the private complete manifests and [public exclusions](PUBLIC_CONTENT.md). Nine source imports bring back 28 unchanged test methods plus reusable accessor/event/report helpers and the generic explicit-input diagnostic host. Four new public-boundary regressions bring the current suite to 134.

The [146-row test map](TEST_MAPPING.tsv) distinguishes 61 already present method ASTs, 28 imported unchanged methods, 56 superseded old-product contracts and one historical inventory fixture retained privately. The denominator difference is explained by the actual contracts, not by treating 146 and 102 as comparable coverage totals. No active failing test was deleted or replaced with an unconditional skip. Old full tests and source fixtures remain privately restorable.

The v0.5 `restore.py`, Candidate A 79-byte save repair, EEPROM guards, all current product build inputs/assembly, authored v0.9a text decisions, logo, font manifest and old verification/history files are unchanged. Generic runtime support is now available in canonical; older matrix drivers with private screens/diagnostic filenames are preserved with follow-up issue #4. FFR secondary-work permission is recorded as the user's 2026-09-07 report in RIGHTS.md, without broadening its scope.

## Executed validation

The baseline was cloned independently from canonical. Python dependencies were installed in a fresh venv; the pinned Dalmoori revision was freshly cloned and built with pnpm 7.33.7 and a separate package store. No legacy checkout, generated-font junction, private source cache or legacy raw URL was needed. Exact local FFR and JP files were hash-checked; JP is a developer-test input only.

Commands actually executed (local paths replaced here with placeholders):

```powershell
python tools/build_ffr_v09.py --ffr "<FFR>" --output-dir output/v0.9-final-build
python tools/build_ffr_v09a.py --ffr "<FFR>" --output-dir output/baseline-build-1
python tools/build_ffr_v09a.py --ffr "<FFR>" --output-dir output/baseline-build-2
python -m unittest discover -s tests -v
python tools/package_ffr_v09a_release.py --build-dir output/baseline-build-1 --output-dir dist/baseline
python tools/build_ffr_v09a.py --ffr "<FFR>" --output-dir output/candidate-build-1
python tools/build_ffr_v09a.py --ffr "<FFR>" --output-dir output/candidate-build-2
python -m unittest discover -s tests -v
python tools/run_public_tests.py
python tools/audit_repository.py
```

Baseline: collected/run/pass 102, fail/error/skip 0. Candidate: collected/run/pass 134, fail/error/skip 0. Public synthetic/source subset: collected/run/pass 43, fail/error/skip 0. The new accessor tests execute 544 real ARM cases using local Candidate A; this is CPU fixture evidence, not natural gameplay.

Both independent builds of each stage reproduced the frozen v0.9a ROM (13,041,664 bytes, SHA-256 `faa2f0ebe1f7bbd9f4a7e1d38b7d35ca2349bfed1d8c2a5d8ae45feb0f7631f6`) and BPS (501,338 bytes, SHA-256 `9289ff85f946fa661c17dee9a9cb6afcd91278caf1af23590e59964ad461810a`). Real BPS application equals the direct ROM. Seven explicit CLI negative cases rejected wrong FFR, actual JP, repatched input, damaged BPS, existing output, input-as-output and save-as-output; originals and sentinel files were unchanged.

The original v0.9a source rebuilt the published ZIP exactly: 201,395 bytes, SHA-256 `a098d1a8a34741959c7950affde4e80e7140380364d7e97ec9f2dcf62b1578c8`. All 27 members and the independent manifest matched the saved public download. Candidate documentation changes can change local ZIP bytes and manifest checksums; a file-level package difference report records this separately. Existing public attachments are never replaced.

A newly executed 600-frame HLE cold boot using the imported canonical host displayed the title screen and closed normally, with zero RAM interventions/state loads/save exports. ROM and core identities are in the JSON record (mGBA 0.11-219-e31759b, core SHA-256 `0d3177c927d791fef897f735d88db3646f7932d02054af108619c6df4e1597f1`). The already supplied core was copied to a separate local-tools directory; it is optional and never a product-build dependency. This smoke check does not establish save detection/compatibility or full gameplay; the initial core save allocation is recorded as observed, not claimed to be an 8 KiB in-game save.

## Preservation and follow-up

Backups are durable local owner storage outside public trees: remote mirrors, local bundles, metadata/assets, byte-verified working-file copies, attached worktrees and original private material. Bundle restore trials matched all local refs and `git fsck --full` passed. Main workspaces preserve 23,677 canonical files (605,721,406 bytes) and 72,198 legacy files (1,823,496,782 bytes), excluding regenerable environments/caches. Additional worktrees preserve 890 files (113,735,832 bytes). Backup restore instructions are in [ROLLBACK.md](ROLLBACK.md). These are local durable copies, not an off-device redundancy claim.

No old tag, release asset or prerelease flag is changed. No v1.0 promotion occurs. [Issue #4](https://github.com/GimoXagros/narikiri2-save-compat/issues/4) remains open for hardware/full-play and route expansion; there were no legacy issues to transfer. The legacy logo PR is mapped to the canonical logo PR and identical original hash. Other repositories are untouched. Archive and branch cleanup occur only after the checklist gates pass, with exact current ref checks immediately before mutation.

## Completed remote actions

Canonical [PR #5](https://github.com/GimoXagros/narikiri2-save-compat/pull/5) merged normally at `7e4c11246f303f99c91cd5851131d9fbae53514e`; candidate commit was `6026fe3ff7821386555215eb3d96b99761a90002`. Both PR checks and the resulting main CI passed. The remote main was fetched into the independent checkout: all 134 tests passed again (0 failures/errors/skips), both builds reproduced the same frozen ROM/BPS, and the final local ZIP matched the recorded documentation-only candidate ZIP. Subsequent closure commits update reporting files only, not these tested sources or package inputs.

Legacy [notice PR #2](https://github.com/GimoXagros/narikiri2-an9j-save-fix/pull/2) merged normally at `533997aa41f298cccdf1219bb3161896498fa0d6`. The original README body remains intact after the new notice. The description/homepage now direct development and releases to canonical. At 2026-09-07 01:37 KST the API confirmed legacy ID 1353791084 **archived=true, private=true** and canonical ID 1356107995 **archived=false, private=false**. All original legacy branches/tags remain; the newly merged notice branch is also retained as history.

Before archiving, all 72,198 legacy working files and the full untracked-file inventory matched the backup; no unaudited remote head, original PR update or release/tag change was present. All 11 public canonical assets were downloaded again without authentication and matched the backup. The four legacy assets and existing tag/asset metadata were unchanged. Original and new notices are linked to canonical issue #4; no historical issue was fabricated or marked resolved by migration.

The following canonical **remote** branches were deleted only after exact tip rechecks, matched backups, merged-PR evidence and protection checks:

| Branch | Deleted tip | Evidence |
| --- | --- | --- |
| codex/add-project-logo-20260906 | cb2ea20065bca1b49042c8b3a29393700384da40 | Squash-equivalent to PR #2: all four modified files exactly match merge 2bfda48212fb296d54ba0a06f842dcce0481b803; logo and rights remain. |
| feat/narikiri2-dalmoori-8x8 | 70fc68f81bd90582e9a5fb7c35e5b82cbb5468a7 | Ancestor, merged PR #1, frozen v0.9 reproduction. |
| fix/v0.9a-dialogue | 07970510454894b19271de03aeaf0a9151f96ee9 | Ancestor, merged PR #3, frozen v0.9a reproduction. |

Local refs and existing worktrees remain available; no user working folder was removed. The current integration branch remains for closure records. Default branches, all tags, all release assets and all legacy historical refs are preserved. Canonical's old v0.5-only repository description was updated to the actual FFR v0.9a scope. The issue #4 product gates remain open, and no v1.0 or fresh game release was created.
