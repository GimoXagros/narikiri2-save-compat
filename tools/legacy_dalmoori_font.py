"""Native glyph/component imports for the unchanged legacy FFR cell encoding."""
import json
from pathlib import Path
import subprocess
import tempfile
import unicodedata
from functools import lru_cache
from import_dalmoori_8x8 import import_characters,parse_generated_glyph
from build_dalmoori_gba_font import place
from transcribe_compact_font import READINGS

ROOT=Path(__file__).resolve().parents[1]
INITIALS='ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'
VOWELS='ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'
FINALS=' ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ'

@lru_cache(maxsize=1)
def bitmaps():
    scalar={};tails=[]
    for tile,value in READINGS.items():
        text=unicodedata.normalize('NFC',value)
        if len(text)==1 and 0x1100<=ord(text)<=0x1112:
            scalar[tile]=INITIALS[ord(text)-0x1100]
        elif 0x1161<=ord(text[0])<=0x1175:
            if len(text)>2 or len(text)==2 and not 0x11A8<=ord(text[1])<=0x11C2:
                raise ValueError('Unrecognized legacy vowel/coda cell')
            tails.append(dict(tile=tile,vowel=VOWELS[ord(text[0])-0x1161],
                              coda=FINALS[ord(text[1])-0x11A7] if len(text)==2 else ''))
        elif len(text)==1:scalar[tile]=text
        else:raise ValueError('Unrecognized legacy cell interpretation')
    result={}
    with tempfile.TemporaryDirectory() as temporary:
        folder=Path(temporary);checkout=ROOT/'third_party/_work/dalmoori-font'
        manifest=import_characters(checkout,folder/'scalars',list(scalar.values()))
        for tile,char in scalar.items():
            source=folder/'scalars/glyphs'/f'U+{ord(char):04X}.txt'
            _,_,_,rows=parse_generated_glyph(source)
            result[tile]=place([[int(c=='#') for c in row] for row in rows])
        (folder/'input.json').write_text(json.dumps(tails,ensure_ascii=False),encoding='utf-8')
        subprocess.run(['node',str(ROOT/'tools/import_legacy_dalmoori.mjs'),str(checkout),
                        str(folder/'input.json'),str(folder/'output.json')],check=True,capture_output=True,text=True)
        pieces=json.loads((folder/'output.json').read_text(encoding='utf-8'))
        for row in pieces:
            file=folder/f"tail-{row['tile']}.txt";file.write_text(row['bitmap'],encoding='utf-8')
            _,_,_,pixels=parse_generated_glyph(file)
            result[row['tile']]=place([[int(c=='#') for c in line] for line in pixels])
    if set(result)!=set(READINGS):raise ValueError('Legacy textual cell population mismatch')
    return result
