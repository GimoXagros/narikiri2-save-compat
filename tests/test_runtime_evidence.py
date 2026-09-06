import copy
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from record_runtime_acceptance import CORE_SHA256, ROM_SHA256, validate_run


class RuntimeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.events = [
            {"op": "initialize", "frame": 0, "ram_interventions": 0,
             "rom_sha256": ROM_SHA256, "core_sha256": CORE_SHA256, "input_save_sha256": None},
            {"frame": 50, "request": {"op": "frames", "count": 50}, "result": {}},
            {"frame": 50, "request": {"op": "save_export", "name": "test.sav"},
             "result": {"size": 8192, "fixture_modified": False}},
            {"frame": 50, "request": {"op": "close"}, "result": {}},
        ]

    def test_clean_evidence_requires_matching_source_and_normal_close(self):
        self.assertTrue(validate_run(self.events, None, clean=True)["normal_close"])
        with self.assertRaises(ValueError):
            validate_run(self.events, "unexpected_save", clean=True)
        with self.assertRaises(ValueError):
            validate_run(self.events[:-1], None, clean=True)

    def test_previous_rom_results_cannot_be_promoted(self):
        events = copy.deepcopy(self.events)
        events[0]["rom_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            validate_run(events, None, clean=True)

    def test_state_load_and_ram_fixture_are_not_clean_progression(self):
        for op in ("state_load", "write_ram"):
            events = copy.deepcopy(self.events)
            events.insert(2, {"frame": 50, "request": {"op": op}, "result": {}})
            with self.assertRaises(ValueError):
                validate_run(events, None, clean=True)

    def test_save_requires_exact_size_and_explicit_nonfixture_flag(self):
        for key, value in (("size", 32768), ("fixture_modified", True), ("fixture_modified", None)):
            events = copy.deepcopy(self.events)
            events[2]["result"][key] = value
            with self.assertRaises(ValueError):
                validate_run(events, None, clean=True)

    def test_clean_sequence_rejects_rewind_and_post_close_work(self):
        events = copy.deepcopy(self.events)
        events[2]["frame"] = 10
        with self.assertRaises(ValueError):
            validate_run(events, None, clean=True)
        events = copy.deepcopy(self.events)
        events.insert(2, {"frame": 50, "request": {"op": "close"}, "result": {}})
        with self.assertRaises(ValueError):
            validate_run(events, None, clean=True)


if __name__ == "__main__":
    unittest.main()
