# v0.9a build and tests

Applying the release ZIP needs only Python 3.10+ and its standard library. Reproducing the ROM additionally needs Node.js, the pinned Python packages in requirements-dev.txt, and the exact original FFR input listed in README.md.

```powershell
python -m pip install -r requirements-dev.txt
git clone https://github.com/RanolP/dalmoori-font third_party/_work/dalmoori-font
git -C third_party/_work/dalmoori-font checkout --detach 897f0e71224d9964a84b888f2596b2bfd7f98def
```

In the font checkout's generator directory, use pnpm 7.33.7, install the frozen lockfile and run `pnpm run build:debug`. Follow third_party/dalmoori-font/SOURCE_MANIFEST.json; do not substitute another font or revision.

The 2026-09-07 independent reproduction used Python 3.14, Node.js 24.19.0 and pnpm 7.33.7, with a newly installed virtual environment and a fresh font clone/store. Do not make `third_party/_work` a junction to an older project checkout. The canonical repository, pinned upstream font and declared local inputs are sufficient. A system pnpm with another version is not the pinned generator command.

```powershell
# From third_party/_work/dalmoori-font/generator, using pnpm 7.33.7:
pnpm install --frozen-lockfile
pnpm run build:debug
```

```powershell
python tools/build_ffr_v09a.py --ffr "FFR.gba" --output-dir output/v0.9a-final-build
python tools/package_ffr_v09a_release.py --build-dir output/v0.9a-final-build --output-dir dist/v0.9a
```

The build derives Candidate A from the exact immutable FFR, regenerates frozen v0.9, then applies source-bound authored text spans and the separate inspection renderer. It checks complete review membership, 8,946 pointer bindings, protected tokens/numbers, glyph round trips, description capacity, nonoverlapping writes, font/sound preservation, deterministic output and cumulative BPS reapplication. The product build and packager both require the exact artifact approved by verification/v0.9a.json. `--candidate` only creates a local validation candidate; the packager rejects that status.

Public text decisions contain authored span changes and source hashes, not the complete original corpus. v0.9 code and verification remain frozen so that old output is reproducible.

The real-data tests also need the exact Japanese and FFR inputs in the repository root, Candidate A at output/NARIKIRI2_AN9J_K_EEPROM_RESTORED.gba, and the frozen v0.9 output at output/v0.9-final-build/NARIKIRI2_AN9J_K_DALMOORI_v0.9.gba. Those files are ignored and never committed. Build v0.9 with tools/build_ffr_v09.py; Candidate A can be made using the preserved restore.py. See config/source_profiles.json for identities.

```powershell
python -m unittest discover -s tests -v
```

Runtime results identify the ROM and mGBA core hashes, controller route, and any RAM preparation separately. Private saves, screenshots and raw dialogue stay local. Runtime success on one emulator is not a hardware or full-playthrough claim.

Public CI runs `python tools/audit_repository.py` and `python tools/run_public_tests.py`: 43 synthetic/source-contract tests, with no ROM, save, emulator, font checkout or extra Python packages. This is a deliberately smaller denominator than the 134-test local real-data suite; it never substitutes for that suite. A missing local dependency/input is an error, not a successful full regression.

`python tools/audit_extended_compact.py --baseline-rom "<Candidate A.gba>"` executes 544 real ARM accessor cases. `python tools/libretro_probe.py --core "<local libretro core>" --rom "<local v0.9a.gba>" --run-dir "<new private directory>"` starts the optional diagnostic host; add `--save` only with an explicit local 8 KiB copy. The core is a separately supplied local tool, not a build dependency. Its hash, ROM hash, BIOS options and interventions are recorded in the private run log.

See [integration results](https://github.com/GimoXagros/narikiri2-save-compat/blob/main/docs/migration/INTEGRATION_REPORT.md) for frozen-tag ZIP reproduction. Documentation edits can change a newly generated local ZIP; never upload that ZIP over the existing v0.9a release assets.
