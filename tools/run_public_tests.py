"""Explicit synthetic/source-contract CI subset; never substitutes real-data QA."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
sys.path.insert(0, str(ROOT / 'tools'))
NAMES = ['test_restore', 'test_bps_and_report_contracts', 'test_runtime_evidence',
         'test_compact_transcription', 'test_repository_integration']

if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromNames(NAMES)
    collected = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(f'Collected {collected}; run {result.testsRun}; failures {len(result.failures)}; '
          f'errors {len(result.errors)}; skipped {len(result.skipped)}')
    raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
