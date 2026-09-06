# v0.9 canonical integration

Canonical: https://github.com/GimoXagros/narikiri2-save-compat
Development archive: https://github.com/GimoXagros/narikiri2-an9j-save-fix

The canonical v0.5 main at 6c26506 is the parent of this integration. Its original restore.py, synthetic tests, verification/v0.5.json and existing tag remain; the original documentation is also preserved under docs/history/v0.5. No history is force-rewritten or deleted.

The validated v0.9 build dependency closure, its assembly/translation/config inputs, and focused regressions are imported as an audited source snapshot from the legacy working tree based on 0e18f64a488901a8a565fbcd9da8b7413aa91e10. Legacy experimentation and private evidence remain in their original repository/workspace.

A whole-history merge is deliberately excluded: the legacy object audit identified a historical Japanese-input BPS blob b568c11d21b516146c84988ff4a4af55a0e739cc at patches/development/b788876e/NARIKIRI2_AN9J_K_COMPLETE_DEV_FROM_JP.bps (4,371,780 bytes). It is not imported or released. The new patch accepts only the exact FFR input.

Raw Japanese full-name reference columns are omitted from the public authored table. Three complete source-text repair matches are represented by source hashes and authored replacement bytes. Description decisions retain authored final text and hash bindings; original description text is read locally. The resulting canonical build must reproduce the exact validated ROM and BPS.

The local comprehensive development suite passed 146 tests. The focused canonical suite has a different denominator, recorded in VERIFICATION.md. Old POC/historical analyses are not presented as current release evidence.

## v0.9a

The v0.9a second stage is built on the byte-frozen v0.9 product. It adds the enemy-inspection consumer and source-bound authored text spans. The private 8,038-entry original corpus is not imported. v0.9 documentation is preserved under docs/history/v0.9; existing tags, source and baseline hashes remain unchanged.
