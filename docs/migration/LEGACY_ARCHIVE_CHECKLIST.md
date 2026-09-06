# Legacy archive checklist

Status: **pending main merge and final verification**. The table records actual completed evidence, not permission to skip outstanding gates.

| Gate | State | Evidence |
| --- | --- | --- |
| A Access/inventory/comparison | PASS | Authenticated private legacy access; all branch/tag/PR, issue/review, release/asset and local work inventories, file/test maps. |
| B Backup/restore | PASS | Private mirrors/bundles, SHA-256 working files/assets, matching restore refs and fsck; attached worktrees included. |
| C Required counterparts/tasks | PASS | Nine selected source imports, 28 restored tests, current contracts mapped; remaining product QA in canonical issue #4. No essential build/preservation UNRESOLVED item. |
| D Canonical main/checks | PENDING | Candidate 134 tests and public 43 tests pass; normal PR merge and post-merge checks still required. |
| E Independent reproduction | PASS | Fresh canonical clone, new font generation/store/venv, two builds each stage, real patch/guard/package checks. |
| F Frozen releases/product | PASS BEFORE MERGE | Existing v0.5/v0.9/v0.9a tags/assets backed up; exact original v0.9a ZIP/ROM/BPS; final remote recheck required. |
| G No unaudited new work | PENDING FINAL RECHECK | Compare remote refs, PR/releases and all private working-file hashes immediately before archive. |
| H Notice/tasks/permission | PENDING NOTICE | Owner admin permission verified; issue #4 carries open QA; legacy notice must be merged normally first. |

Archive target only: `GimoXagros/narikiri2-an9j-save-fix`, ID **1353791084**, private. Canonical ID **1356107995** must remain public and unarchived. Legacy branches/tags remain intact; permanent deletion, history rewrites and visibility changes are prohibited. The final action must read back both identities, archive state, default branches and release access.
