"""Fixed AN9J table identities. Physical membership is not normal-play reachability.

No text or translation from this investigation is a product-build input.
Offsets are ROM offsets; end addresses are exclusive.
"""
from dataclasses import dataclass
import struct

from narikiri2_text_spec import read_pointer, read_c_string


@dataclass(frozen=True)
class CompactTable:
    identity: str
    start: int
    stride: int
    count: int
    evidence: str

    @property
    def end(self):
        return self.start + self.stride * self.count

    def fields(self):
        return {self.start + i * self.stride: f"{self.identity}_{i:03d}"
                for i in range(self.count)}


TABLES = (
    CompactTable("ARTE", 0x374A38, 20, 232,
                 "08008C54 selects record*20 + (0 or 4); subsequent data is a pointer array"),
    CompactTable("CHARACTER_BOOK", 0x2C5334, 40, 22,
                 "08018D9C reads record*40+0 and calls 08001DDC when unlocked"),
    CompactTable("BATTLE_COMMAND", 0x2C7B60, 8, 13,
                 "0801C2CC copies 0x70 bytes (13 records plus null record) to stack"),
    CompactTable("BATTLE_NAME", 0x375D40, 4, 58,
                 "080092CC ordinary branch reads table[index*4]; special -1/58/59 branches differ"),
    CompactTable("SELECT_PARTY", 0x3AE0C0, 4, 7,
                 "0801C384 passes null-terminated list to 08004D98; normal-play entry unresolved"),
    CompactTable("SELECT_JOB", 0x3AE0E0, 4, 201,
                 "Physical null-terminated pointer list; caller/normal-play entry unresolved"),
    CompactTable("SELECT_MONSTER", 0x3AE408, 4, 164,
                 "Physical null-terminated pointer list; caller/normal-play entry unresolved"),
    CompactTable("SELECT_ENEMY", 0x3AE69C, 4, 7,
                 "Physical null-terminated pointer list; caller/normal-play entry unresolved"),
)


def extended_fields():
    result = {}
    for table in TABLES:
        for storage, identity in table.fields().items():
            if storage in result:
                raise ValueError("Overlapping table fields")
            result[storage] = (identity, table.identity)
    return result


def text_at(rom, storage):
    pointer, target = read_pointer(rom, storage)
    raw = read_c_string(rom, target, min(target + 4096, len(rom)))
    return pointer, raw


def validate_tables(rom):
    for table in TABLES:
        for storage in table.fields():
            text_at(rom, storage)
        if table.identity.startswith("SELECT_") or table.identity == "BATTLE_COMMAND":
            if struct.unpack_from("<I", rom, table.end)[0] != 0:
                raise ValueError(f"{table.identity}: expected null table terminator")
    for i in range(232):
        for field in (4, 8):
            text_at(rom, 0x374A38 + i * 20 + field)
