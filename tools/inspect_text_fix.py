"""Own the enemy-inspection affine text consumer, separate from the BG0 font."""
import hashlib
import struct
from pathlib import Path

from build_banked_font import assemble, veneer
from private_font_spec import Write

ROOT = Path(__file__).resolve().parents[1]
V09_SHA256 = '560535ba5dce7246a4c1b210a082b93a08091b8f9e2bfa96467e44adbbf65c81'
ENTRY, BODY = 0x25FDC, 0xC1EC00
EXPECTED = bytes.fromhex('f0b5474680b4041c')


def plans(source):
    if hashlib.sha256(source).hexdigest() != V09_SHA256:
        raise ValueError('Inspection fix requires the exact v0.9 baseline')
    # Resource 0x11a is a 240-tile, 8bpp affine atlas. Japanese kana slots
    # 72..135 become cell-local Hangul slots only for this inspection window.
    # Alphabet/digits, punctuation, window tiles, and element icons stay intact.
    if source[0x302684:0x30268c] != struct.pack('<4H',282,282,283,284):
        raise ValueError('Inspection resource ownership changed')
    if source[0x71fdd0:0x71fdd4] != bytes.fromhex('30003c00'):
        raise ValueError('Inspection atlas extent changed')
    for code in list(range(32,127)) + list(range(128,136)):
        offset = struct.unpack_from('<h',source,0x3afb82+2*code)[0]
        tile = source[0x721d38+offset]
        if 72 <= tile <= 135:
            raise ValueError('Inspection ASCII or element icon aliases Hangul slots')
    payload = assemble(ROOT/'asm/banked_inspect_text.s',BODY,512,0x400)
    return [Write('inspect_text_entry','hook',ENTRY,EXPECTED,veneer(ENTRY,BODY,3)),
            Write('inspect_text_body','assembly',BODY,b'\xff'*len(payload),payload)]


def apply(source):
    writes = plans(source)
    target = bytearray(source)
    for write in writes:
        if source[write.offset:write.offset+len(write.expected)] != write.expected:
            raise ValueError(f'Inspection source guard: {write}')
        target[write.offset:write.end] = write.final
    return bytes(target), writes
