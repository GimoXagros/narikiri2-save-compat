#!/usr/bin/env python3
"""Provisional Unicode transcription of the original FFR compact font.

These readings were inspected against ROM-derived 8x8/16x16 glyph sheets.
They describe displayed glyph pieces, not CP932 semantics of stored bytes.
They are investigation data: no translation or release approval is implied.
"""
import csv
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from extended_compact_spec import text_at
from build_compact_target_catalog import known_compact_labels
from narikiri2_text_spec import BASELINE_SHA256


def nfd(text):
    return unicodedata.normalize("NFD", text)


def readings():
    result = {0x10: " ", 0x15: "%", 0x1F: "/", 0x2F: "?"}
    result.update({0x20+i: str(i) for i in range(10)})
    result.update({0x31+i: chr(65+i) for i in range(26)})
    for tile, initial in zip((0x11,0x12,0x13,0x14,0x16,0x17,0x18,0x19,
                              0x1A,0x1B,0x1C,0x1D,0x1E,0x2A),
                             "ᄀᄂᄃᄅᄆᄇᄉᄋᄌᄎᄏᄐᄑᄒ"):
        result[tile] = initial
    complete = {
        0x2B:"고",0x2C:"곤",0x2D:"골",0x2E:"공",0x30:"광",
        0x4B:"괴",0x4C:"구",0x4D:"궁",0x4E:"권",0x4F:"그",
        0x50:"금",0x51:"노",0x52:"녹",0x53:"논",0x54:"도",0x55:"동",
        0x56:"두",0x57:"둘",0x58:"드",0x59:"들",0x5A:"로",0x5B:"록",
        0x5C:"론",0x5D:"롬",0x5E:"뢰",0x5F:"료",0x60:"루",0x61:"르",
        0x62:"른",0x63:"모",0x64:"몬",0x65:"무",0x66:"문",0x67:"물",
        0x68:"보",0x69:"본",0x6A:"볼",0x6B:"봉",0x6C:"부",0x6D:"불",0x6E:"브",
        0xB1:"블",0xB2:"소",0xB3:"수",0xB4:"술",0xB5:"쉐",0xB6:"슈",
        0xB7:"스",0xB8:"슬",0xB9:"슴",0xBA:"승",0xBB:"오",0xBC:"온",
        0xBD:"외",0xBE:"왈",0xBF:"왕",0xC0:"요",0xC1:"용",0xC2:"우",
        0xC3:"운",0xC4:"울",0xC5:"원",0xC6:"월",0xC7:"위",0xC8:"윈",
        0xC9:"윗",0xCA:"유",0xCB:"으",0xCC:"은",0xCD:"을",0xCE:"음",
        0xCF:"의",0xD0:"주",0xD1:"즈",0xD2:"즌",0xD3:"조",0xD4:"죠",
        0xD5:"츠",0xD6:"초",0xD7:"코",0xD8:"콘",0xD9:"쿠",0xDA:"큐",
        0xDB:"크",0xDC:"클",0xDD:"토",0xDE:"톤",0xDF:"트",0xE0:"특",
        0xE1:"투",0xE2:"포",0xE3:"폭",0xE4:"풍",0xE5:"프",0xE6:"플",
        0xE7:"호",0xE8:"홀",0xE9:"홍",0xEA:"화",0xEB:"황",0xEC:"후",0xED:"흑",
    }
    result.update({tile: nfd(value) for tile, value in complete.items()})
    # Right-hand vowel/final pieces. The null initial is removed from a
    # convenient Hangul exemplar; NFC then joins them with the preceding initial.
    tails = {
        0x71:"아",0x72:"악",0x73:"안",0x74:"앋",0x75:"알",0x76:"암",
        0x77:"압",0x78:"앗",0x79:"았",0x7A:"앙",0x7B:"앚",0x7C:"앛",
        0x7D:"야",0x7E:"약",0x7F:"얀",0x80:"양",0x81:"어",0x82:"억",
        0x83:"언",0x84:"얻",0x85:"얼",0x86:"엄",0x87:"업",0x88:"엇",
        0x89:"었",0x8A:"엉",0x8B:"없",0x8C:"여",0x8D:"역",0x8E:"연",
        0x8F:"열",0x90:"염",0x91:"였",0x92:"영",0x93:"옆",0x94:"이",
        0x95:"익",0x96:"인",0x97:"일",0x98:"임",0x99:"입",0x9A:"잇",
        0x9B:"있",0x9C:"잉",0x9D:"잊",0x9E:"잋",0x9F:"에",0xA0:"엑",
        0xA1:"엔",0xA2:"엘",0xA3:"엠",0xA4:"엣",0xA5:"엤",0xA6:"예",
        0xA7:"애",0xA8:"액",0xA9:"앤",0xAA:"앰",0xAB:"앵",0xAC:"앴",0xAD:"앱",
    }
    result.update({tile: nfd(value)[1:] for tile, value in tails.items()})
    return result


READINGS = readings()
FORMAT = re.compile(rb"%(?:[-+ #0]*\d*(?:\.\d+)?[a-zA-Z%])")


def transcribe(raw):
    mode, position = 0, 0
    output, units, unsupported = [], [], []
    while position < len(raw):
        value = raw[position]
        # Retain format tokens symbolically. Only the already observed %h
        # toggle is interpreted. Arguments and inserted strings are not guessed.
        match = FORMAT.match(raw, position) if value == 0x25 else None
        if match:
            token = match.group()
            units.append({"kind":"format", "raw_hex":token.hex().upper(), "mode_before":mode})
            if token == b"%h":
                mode ^= 1
            else:
                output.append("⟦" + token.decode("ascii") + "⟧")
            position = match.end()
            continue
        if value == 0x12:
            units.append({"kind":"mode", "raw_hex":"12", "mode_before":mode})
            mode ^= 1
        elif value == 0x0A:
            units.append({"kind":"newline", "raw_hex":"0A"})
            output.append("\n")
        else:
            tile = value - 0x10 if 0x20 <= value <= 0x7E else value + (0x10 if mode else -0x30) if 0xA1 <= value <= 0xDF else None
            if tile not in READINGS:
                unsupported.append(f"{position}:{value:02X}")
                output.append(f"⟦RAW:{value:02X}⟧")
            else:
                output.append(READINGS[tile])
            units.append({"kind":"glyph" if tile in READINGS else "unsupported",
                          "raw_hex":f"{value:02X}", "tile":tile, "mode":mode})
        position += 1
    if bytes.fromhex("".join(unit["raw_hex"] for unit in units)) != raw:
        raise ValueError("Transcription lost protected source bytes")
    text = unicodedata.normalize("NFC", "".join(output))
    incomplete_jamo = [f"U+{ord(c):04X}" for c in text if 0x1100 <= ord(c) <= 0x11FF]
    return {"text":text, "units":units, "unsupported":unsupported,
            "uncomposed_jamo":incomplete_jamo}


def main():
    root = Path(__file__).resolve().parents[1]
    rom = (root / "output/NARIKIRI2_AN9J_K_EEPROM_RESTORED.gba").read_bytes()
    if hashlib.sha256(rom).hexdigest() != BASELINE_SHA256:
        raise ValueError("Candidate A identity mismatch")
    catalog = list(csv.DictReader((root / "analysis/private/compact_target_candidates.csv").open(encoding="utf-8-sig")))
    output = []
    for row in catalog:
        result = transcribe(bytes.fromhex(row["kr_raw_hex"]))
        output.append({"candidate_id":row["candidate_id"], "kr_target_hex":row["kr_target_hex"],
                       "kr_raw_hex":row["kr_raw_hex"], "display_transcription":result["text"],
                       "unsupported":";".join(result["unsupported"]),
                       "uncomposed_jamo":";".join(result["uncomposed_jamo"]),
                       "token_units_json":json.dumps(result["units"], ensure_ascii=False),
                       "status":"PROVISIONAL_VISUAL_TRANSCRIPTION_NOT_PRODUCT_INPUT"})
    path = root / "analysis/private/compact_display_transcription.csv"
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(output[0]),lineterminator="\n")
        writer.writeheader(); writer.writerows(output)
    glyphs = {c for r in output for c in re.sub(r"⟦.*?⟧", "", r["display_transcription"])
              if c != "\n" and not 0x1100 <= ord(c) <= 0x11FF}
    summary={"schema":"narikiri2-compact-transcription-v1", "source_sha256":BASELINE_SHA256,
             "mapped_printable_tiles":len(READINGS), "candidate_targets":len(output),
             "targets_with_unsupported_bytes":sum(bool(r["unsupported"]) for r in output),
             "targets_with_uncomposed_jamo":sum(bool(r["uncomposed_jamo"]) for r in output),
             "provisional_unique_codepoints_excluding_symbolic_tokens":len(glyphs),
             "provisional_hangul_syllables":sum("가"<=c<="힣" for c in glyphs),
             "source_byte_roundtrip":"PASS", "product_input":False,
             "limitations":["Glyph readings require review; this is not translation approval.",
                            "Format tokens except %h stay symbolic; runtime insertions are not counted.",
                            "Uncomposed jamo and mark-mode bytes remain explicitly unresolved.",
                            "This changed-pointer survey is not the whole game's text denominator."]}
    (root/"analysis/compact_transcription_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
