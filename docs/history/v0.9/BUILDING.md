# v0.9 build and tests

The release ZIP applies a prebuilt BPS using Python 3.10+ and the standard library only. Source reproduction additionally requires Node.js and the pinned Python development packages in requirements-dev.txt.

```powershell
python -m pip install -r requirements-dev.txt
git clone https://github.com/RanolP/dalmoori-font third_party/_work/dalmoori-font
git -C third_party/_work/dalmoori-font checkout --detach 897f0e71224d9964a84b888f2596b2bfd7f98def
```

In the checkout's generator directory, use pnpm 7.33.7, install with the frozen lockfile, and run `pnpm run build:debug`. See its SOURCE_MANIFEST.json. Do not substitute a system/TTF font or another upstream revision.

```powershell
python tools/build_ffr_v09.py --ffr "FFR.gba" --output-dir output/v0.9-final-build
```

This verifies the exact FFR input, restores Candidate A, builds all writes from that immutable image, assembles tracked Thumb-1 code, checks write ownership and protected regions, builds twice, verifies frozen target/BPS hashes, and reapplies BPS. It fails if verification/v0.9.json does not approve that exact artifact. Use a new output directory.

The focused v0.9 regression suite retains the original v0.5 synthetic tests. The real consumer tests also need the exact Japanese ROM (SHA-256 in config/source_profiles.json) in the repository root and Candidate A at output/NARIKIRI2_AN9J_K_EEPROM_RESTORED.gba. Both remain ignored/local. Candidate A can be made with the preserved v0.5 restore.py from the exact FFR and Japanese inputs.

```powershell
python -m unittest discover -s tests -v
python tools/package_release.py --build-dir output/v0.9-final-build --output-dir dist/my-v09
```

The non-distribution diagnostic build in build_banked_font.py is for inspection; build_ffr_v09.py is the frozen product entry point. Legacy restore.py/verify_local.py remain for v0.5 reproduction and are not the v0.9 product build.
