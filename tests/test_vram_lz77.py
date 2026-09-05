"""Destination-bus regression: normal byte-array LZ round trips miss this bug."""
from pathlib import Path
import random
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from narikiri2_item_ui_font import compress_lz77
from build_banked_font import ascii_font


def halfword_destination(stream, initial_byte):
    size=int.from_bytes(stream[1:4],'little')
    memory=bytearray([initial_byte])*(size+2)
    cursor=4
    written=0
    pending=0
    def emit(value):
        nonlocal written,pending
        if written&1:
            memory[written-1:written+1]=bytes((pending,value))
        else:pending=value
        written+=1
    while written<size:
        flags=stream[cursor];cursor+=1
        for bit in range(7,-1,-1):
            if written>=size:break
            if flags&(1<<bit):
                a,b=stream[cursor:cursor+2];cursor+=2
                count=(a>>4)+3;distance=((a&15)<<8)+b+1
                if distance>written:raise ValueError('Reference before destination')
                for _ in range(count):emit(memory[written-distance])
            else:
                emit(stream[cursor]);cursor+=1
    if written&1:memory[written-1:written+1]=bytes((pending,0))
    return bytes(memory[:size])


class VramLz77Tests(unittest.TestCase):
    def test_distance_one_reproduces_stale_background(self):
        raw=b'\0'*64
        old=compress_lz77(raw)
        self.assertNotEqual(halfword_destination(old,0xbb),raw)
        self.assertEqual(halfword_destination(compress_lz77(raw,vram_safe=True),0xbb),raw)

    def test_vram_streams_ignore_prior_destination_contents(self):
        rng=random.Random(1234)
        cases=[b'\0'*8192,bytes(range(256))*32,b'ABC'*51,
               bytes(rng.randrange(16) for _ in range(8192))]
        for raw in cases:
            stream=compress_lz77(raw,vram_safe=True)
            self.assertEqual(len(stream)%4,0)
            for poison in (0,0xbb,0xff):
                self.assertEqual(halfword_destination(stream,poison),raw)

    def test_active_font_clear_reload_after_solid_mode(self):
        source=(ROOT/'output/NARIKIRI2_AN9J_K_EEPROM_RESTORED.gba').read_bytes()
        stream,expected,_=ascii_font(source)
        for poison in (0,0xbb,0xff):
            self.assertEqual(halfword_destination(stream,poison),expected)


if __name__=='__main__':unittest.main()
