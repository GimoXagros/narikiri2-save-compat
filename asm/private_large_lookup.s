    push {r4, lr}
    ldr r3, private_index
    cmp r2, r3
    blo original
    subs r4, r2, r3
    cmp r4, #FONT_COUNT
    bhs original
    lsls r4, r4, #5
    ldr r3, private_font
    adds r4, r4, r3
    b done
original:
    lsls r2, r2, #5
    ldr r3, original_font
    adds r4, r2, r3
done:
    ldr r3, original_return
    bx r3
    .balign 4, 0
private_index: .word 4992
private_font: .word 0x08c01800
original_font: .word 0x080ac3f4
original_return: .word 0x080014e9
