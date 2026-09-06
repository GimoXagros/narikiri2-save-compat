# v0.9a build and tests

Applying the release ZIP needs only Python 3.10+ and its standard library. Reproducing the ROM additionally needs Node.js, the pinned Python packages in requirements-dev.txt, and the exact original FFR input listed in README.md.

```powershell
python -m pip install -r requirements-dev.txt
git clone https://github.com/RanolP/dalmoori-font third_party/_work/dalmoori-font
git -C third_party/_work/dalmoori-font checkout --detach 897f0e71224d9964a84b888f2596b2bfd7f98def
```

In the font checkout's generator directory, use pnpm 7.33.7, install the frozen lockfile and run `pnpm run build:debug`. Follow third_party/dalmoori-font/SOURCE_MANIFEST.json; do not substitute another font or revision.

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
