    cmp r4, #0x7f
    bne original
    ldrb r0, [r2, #1]
    cmp r0, #1
    blo original
    cmp r0, #FONT_COUNT
    bhi original
    ldr r1, virtual_base
    adds r4, r0, r1
    ldr r0, [sp]
    adds r0, #1
    str r0, [sp]
    b ascii_path
original:
    adds r0, r4, #0
    subs r0, #0x20
    cmp r0, #0x5f
    bhi kana_path
ascii_path:
    ldr r0, ascii_return
    bx r0
kana_path:
    ldr r0, kana_return
    bx r0
    .balign 4, 0
virtual_base: .word 0x187
ascii_return: .word 0x08001af9
kana_return: .word 0x08001b29
