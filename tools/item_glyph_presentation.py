"""Source-component UI letterform revision after b788876e human rejection.

Presentation only: 8px row height, original palette/loader/geometry unchanged.
These are deterministic crops/compositions of the baseline UI font, not a
system-font substitution or bitmap edits to shared source glyph slots.
"""


def revised_ui_glyphs(tile):
    """Return 16x8 private canvases using the game's existing bold skeletons."""
    gong, ro, bieup, a, i = (tile(n) for n in (0x2E, 0x5A, 0x17, 0x71, 0x94))
    result = {}
    gwaeng = [[0]*16 for _ in range(8)]
    # 고 in the left half; ㅏ + ㅣ in the right; the existing round ㅇ below.
    for y in range(5):
        gwaeng[y][0:8] = gong[y]
        gwaeng[y][9:13] = a[y][1:5]
        gwaeng[y][14:16] = i[y][1:3]
    for y in range(3):
        gwaeng[y+5][4:11] = gong[y+5][1:8]
    result['괭'] = gwaeng

    ppang = [[0]*16 for _ in range(8)]
    # User's sign reference prioritizes a bold ㅃ/ㅏ and a separate broad round
    # ㅇ. Remove only the duplicate upper vertical-extension row of UI 17;
    # retain its open top, middle bar, lower counter and bottom bar. One empty
    # row separates that four-row upper group from the three-row round footer.
    for y, source_y in enumerate((0, 2, 3, 4)):
        body = [bieup[source_y][x] for x in (2, 3, 4, 5, 7)]
        ppang[y][0:5] = body
        ppang[y][6:11] = body
        ppang[y][12:16] = a[source_y][1:5]
    for y in range(3):
        ppang[y+5][2:13] = [gong[y+5][1+x*7//11] for x in range(11)]
    result['빵'] = ppang

    # A compact ㄹ retains both turns of source 로. The ㅗ stem is moved into
    # the lower ㄹ row and shares its baseline to fit the established 8px UI.
    # This is a review candidate, not a claim of human typography approval.
    rong = [row[:] for row in ro[:5]] + [row[:] for row in gong[5:8]]
    for x, bit in enumerate(ro[5]):
        rong[3][x] |= bit
    # Keep every source column: a wider ink box prevents the misread narrow
    # raw-6F glyph used in b788876e. Padding is part of the 16px cell.
    result['롱'] = [[0] + [row[1+x*7//12] for x in range(12)] + [0]*3 for row in rong]
    # 룡 = ㄹ + ㅛ + ㅇ, not 롱 (ㅗ). Retain the two source 요 stems.
    ryong = [row[:] for row in ro[:5]] + [row[:] for row in gong[5:8]]
    for x, bit in enumerate(tile(0xC0)[5]):
        ryong[3][x] |= bit
    result['룡'] = [[0] + [row[1+x*7//12] for x in range(12)] + [0]*3 for row in ryong]
    return result


PROVENANCE = {
    '괭': 'UI 2E 고/ㅇ + 71 ㅏ + 94 ㅣ; 16x8 component placement, no vertical resampling',
    '빵': 'User sign reference: bold upper group and broad round footer; UI 17/71 rows 0,2,3,4 + blank row + UI 2E round ㅇ enlarged horizontally 7→11px; 16x8',
    '롱': 'UI 5A 로 preserves both ㄹ turns; shared ㅗ baseline + UI 2E round ㅇ; 12px ink in 16x8',
    '룡': 'UI 5A ㄹ + C0 요 two ㅛ stems + 2E round ㅇ; 12px ink in 16x8; distinct from 롱',
}
