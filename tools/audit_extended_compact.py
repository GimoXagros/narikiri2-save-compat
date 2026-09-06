"""Execute real table accessors using local Candidate A; counts are CPU fixtures.

Extracted from the legacy audit. The original corpus-generating driver remains
in the private archive; this entry point needs only the declared local ROM.
"""
import argparse, hashlib, json, struct, unicodedata
from pathlib import Path
from extended_compact_spec import validate_tables
from narikiri2_text_spec import BASELINE_SHA256

def make_cpu(rom):
    from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB
    cpu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    for address, size in ((0x08000000, 0x1000000), (0x02000000, 0x40000),
                          (0x03000000, 0x8000)):
        cpu.mem_map(address, size)
    cpu.mem_write(0x08000000, rom)
    return cpu


def audit_accessors(rom):
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_PC,
                                   UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_CPSR)
    cpu = make_cpu(rom)
    stop = 0x02020000

    def run(start, r0, r1, end=stop):
        cpu.reg_write(UC_ARM_REG_CPSR, 0x3F)
        cpu.reg_write(UC_ARM_REG_SP, 0x03007E00)
        cpu.reg_write(UC_ARM_REG_LR, stop | 1)
        cpu.reg_write(UC_ARM_REG_R0, r0)
        cpu.reg_write(UC_ARM_REG_R1, r1)
        cpu.emu_start(start | 1, end, count=5000)
        if cpu.reg_read(UC_ARM_REG_PC) != end:
            raise ValueError(f"Accessor did not reach continuation: {start:08X}")

    for index in range(232):
        for selector in (0, 1):
            run(0x08008C54, index, selector)
            expected = struct.unpack_from("<I", rom, 0x374A38 + 20*index + 4*selector)[0]
            if cpu.reg_read(UC_ARM_REG_R0) != expected:
                raise ValueError(f"Arte pointer mismatch: {index}/{selector}")

    # Isolate the documented unlocked path. This is explicitly a CPU fixture.
    def force_unlocked(uc, address, size, _):
        uc.reg_write(UC_ARM_REG_R0, 1)
        uc.reg_write(UC_ARM_REG_PC, 0x08018DA9)

    hook = cpu.hook_add(UC_HOOK_CODE, force_unlocked, begin=0x080A11F4, end=0x080A11F4)
    for index in range(22):
        run(0x08018D9C, 0x02000100, index, 0x08001DDC)
        expected = struct.unpack_from("<I", rom, 0x2C5334 + 40*index)[0]
        if cpu.reg_read(UC_ARM_REG_R1) != expected or cpu.reg_read(UC_ARM_REG_R0) != 0x02000100:
            raise ValueError(f"Character book formatter argument mismatch: {index}")
    cpu.hook_del(hook)

    for index in range(58):
        run(0x080092CC, index, 0)
        expected = struct.unpack_from("<I", rom, 0x375D40 + 4*index)[0]
        if cpu.reg_read(UC_ARM_REG_R0) != expected:
            raise ValueError(f"Battle name accessor mismatch: {index}")
    return {"arte_index_selector_cases": 464, "character_unlocked_fixture_cases": 22,
            "battle_name_ordinary_cases": 58, "total": 544,
            "status": "PASS_CPU_FIXTURE_NOT_NORMAL_PLAY"}


def source_name_equivalent(compact, full):
    # Source comparison only. Never edits Korean wording or removes spaces.
    return unicodedata.normalize("NFKC", compact.replace("%h", "")) == unicodedata.normalize("NFKC", full)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-rom', type=Path, required=True)
    args = parser.parse_args()
    rom = args.baseline_rom.read_bytes()
    if hashlib.sha256(rom).hexdigest() != BASELINE_SHA256:
        raise ValueError('Exact Candidate A required')
    validate_tables(rom)
    print(json.dumps(audit_accessors(rom), indent=2))

if __name__ == '__main__':
    main()
