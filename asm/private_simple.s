    cmp r2, #0x7f
    bne original
    ldrb r0, [r3, #1]
    cmp r0, #1
    blo original
    cmp r0, #FONT_COUNT
    bhi original
    ldr r2, virtual_base
    adds r2, r2, r0
    adds r3, #1
    b ascii_path
original:
    adds r0, r2, #0
    subs r0, #0x20
    cmp r0, #0x5e
    bhi kana_path
ascii_path:
    ldr r0, ascii_return
    bx r0
kana_path:
    ldr r0, kana_return
    bx r0
    .balign 4, 0
virtual_base: .word 0x187
ascii_return: .word 0x08001e19
kana_return: .word 0x08001e29
