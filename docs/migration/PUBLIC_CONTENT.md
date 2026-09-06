# Public imports and private exclusions

[IMPORT_ALLOWLIST.json](IMPORT_ALLOWLIST.json) identifies the nine selected authored source/test imports by original file SHA-256 and exact selected scope. Six whole-file/test-method groups plus isolated reusable functions retain their assertions; new drivers use explicit local inputs. New integration tooling, CI and reports are authored for this repository under its existing MIT terms. Original attribution remains GimoXagros's legacy work, with historical refs and dates in the private metadata backup.

The original `logo.png` is byte-identical to legacy PR #1 / canonical PR #2; it keeps the separate rights notice and is not part of the MIT/code or Apache/font grant. No logo data was re-encoded.

The following remain **PRIVATE_ARCHIVE_ONLY** and must not enter public Git, releases or CI artifacts:

| Material | Preservation and reason |
| --- | --- |
| ROMs, saves, memory/state dumps, original screenshots | Private working-file manifests and backups. They are local inputs/evidence, not distributable source. |
| Complete extracted Japanese/FFR corpora, private raw matching tables and research source material | Private working files; current canonical source reads needed original text locally and uses authored hash-bound changes. |
| Generated font checkouts/assets and old glyph fixtures | Private backup and pinned upstream manifest. Generate afresh for builds; preserve Apache-2.0 notice. |
| Old POC/Gate2/development patches | Private mirror and release backups, never reintroduced through history or tags. |
| Historical diagnostic-specific drivers and logs | Private source/evidence index; generic host and event validator imported, remaining route work in issue #4. |
| Local instructions, session state and absolute paths | Private backup only; adopted policies are summarized in current public docs. |

The historical object audit covered **142 canonical blobs** and **468 legacy blobs**, including all accessible branch/tag/PR refs. No Git LFS pointers or submodule trees were found. The only canonical binary Git blob was the approved, separately attributed logo. Legacy contained that same logo and seven old IPS/BPS blobs; all seven remain private. Existing public release attachments were separately downloaded, hashed and ZIP members checked; they were not imported as Git blobs or replaced.

The explicitly excluded object remains excluded:

- Path: `patches/development/b788876e/NARIKIRI2_AN9J_K_COMPLETE_DEV_FROM_JP.bps`
- Git blob: `b568c11d21b516146c84988ff4a4af55a0e739cc`
- Size: 4,371,780 bytes
- SHA-256: `06a8169e3ad8610e8201aa30858abd1bdb476d234f237ba3aa8b372a6b687ab3`

The public audit checks tracked-file content signatures, credential-shaped text, original logo identity and active dependency paths. It is an additional mechanical gate, not a license determination or an assertion that an arbitrary patch is safe. The source and method allowlist was reviewed before import; no complete raw corpus, archive, fixture or encoded replacement for them was added. Existing history and frozen verification JSON remain unchanged.
