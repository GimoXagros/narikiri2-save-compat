"""Reject missing, failing or skipped unittest evidence; no frozen report driver."""
import re

def parse_unittest_result(log,returncode):
    count=re.search(r'Ran (\d+) tests?',log)
    # A test name can itself contain "skipped" (e.g. not_silently_skipped).
    # Inspect actual unittest result markers, not arbitrary substrings.
    skipped=re.search(r'\.\.\. skipped\b|skipped=\d+',log)
    if returncode or not count or skipped or not re.search(r'^OK\s*$',log,re.MULTILINE):
        raise ValueError('Verification must pass without skipped CPU/dependency tests:\n'+log)
    return int(count[1])
