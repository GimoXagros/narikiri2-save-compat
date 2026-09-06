import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_compact_target_catalog import known_compact_storages, partition_rows
from source_profiles import load_source_profiles, source_profile


class SourceProfileTests(unittest.TestCase):
    def test_registry_has_unique_normalized_hashes_and_expected_roles(self):
        profiles = load_source_profiles()
        self.assertEqual(len(profiles), 5)
        self.assertEqual(source_profile("AN9J_FFR_BETA3_071102").size, 0x980000)
        self.assertEqual(source_profile("AN9J_JP_REV0").size, 0x800000)
        self.assertEqual(source_profile("AN9J_CANDIDATE_A").size, 0xC00000)
        self.assertTrue(source_profile("ND2_EN_V230_APPLIED").reference_only)
        for profile in profiles.values():
            self.assertEqual(len(profile.sha256), 64)
            self.assertEqual(profile.sha256, profile.sha256.lower())
            int(profile.sha256, 16)

    def test_registry_json_is_the_only_source_profile_authority(self):
        payload = json.loads((ROOT / "config/source_profiles.json").read_text(encoding="utf-8"))
        ids = {row["id"] for section in ("profiles", "reference_only") for row in payload[section]}
        self.assertEqual(ids, set(load_source_profiles()))

    def test_known_compact_denominator_and_partition(self):
        known = known_compact_storages()
        self.assertEqual(len(known), 523)
        first_known = min(known)
        rows = [
            {"storage_hex": f"{first_known:08X}", "kr_target_hex": "00950000"},
            {"storage_hex": "00000100", "kr_target_hex": "00950010"},
            {"storage_hex": "00000104", "kr_target_hex": "00800000"},
        ]
        parts = partition_rows(rows)
        self.assertEqual(len(parts["compact"]), 2)
        self.assertEqual(len(parts["known_refs"]), 1)
        self.assertEqual(len(parts["residual_refs"]), 1)


if __name__ == "__main__":
    unittest.main()
