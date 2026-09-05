"""Adopted fixed-revision specification for the AN9J Candidate A save repair."""

from __future__ import annotations

from dataclasses import dataclass

from source_profiles import source_profile


_CANDIDATE_A = source_profile("AN9J_CANDIDATE_A")
EXPECTED_OUTPUT_SHA256 = _CANDIDATE_A.sha256
OUTPUT_SIZE = _CANDIDATE_A.size
PROTECTED_POINTER_START = 0xA5FF8
PROTECTED_POINTER_COUNT = 9


@dataclass(frozen=True)
class ExpectedWrite:
    write_id: str
    purpose: str
    offset: int
    expected_source: bytes
    final_bytes: bytes

    @property
    def end(self) -> int:
        return self.offset + len(self.final_bytes)


EXPECTED_WRITES = (
    ExpectedWrite(
        "SAVE_SETUP_RESTORE",
        "Restore the verified EEPROM setup/configuration entry prefix",
        0xA60D4,
        bytes.fromhex("00207047"),
        bytes.fromhex("0A1C0006"),
    ),
    ExpectedWrite(
        "SAVE_READ_RESTORE",
        "Restore the verified EEPROM V120 read entry prefix",
        0xA6258,
        bytes.fromhex(
            "70B500040A1C400BE021090541180731002308781070013301320139072BF8D9002070BC02BC0847"
        ),
        bytes.fromhex(
            "70B5A2B00D1C0004030C034800688088834205D3014844E0F4500002FF8000002248061C0068017A"
        ),
    ),
    ExpectedWrite(
        "SAVE_WRITE_RESTORE",
        "Restore the verified EEPROM V120 write entry prefix",
        0xA6308,
        bytes.fromhex(
            "70B500040A1C400BE021090541180731002310780870013301320139072BF8D9002070BC02BC0847"
        ),
        bytes.fromhex(
            "30B5A9B00D1C0004040C034800688088844205D3014855E0F4500002FF8000000F480068007A4000"
        ),
    ),
)


ALLOWED_DIFF_RANGES = (
    (0xA60D4, 0xA60D8),
    (0xA625A, 0xA625D),
    (0xA625E, 0xA6280),
    (0xA6308, 0xA6309),
    (0xA630A, 0xA630D),
    (0xA630E, 0xA6330),
)


def allowed_diff_offsets() -> list[int]:
    return [offset for start, end in ALLOWED_DIFF_RANGES for offset in range(start, end)]
