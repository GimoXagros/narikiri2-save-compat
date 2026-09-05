    ldr r3, wrap_function
    bl call_r3
    ldrb r0, [r4]
    cmp r0, #0x7f
    bne original
    ldrb r0, [r4, #1]
    cmp r0, #1
    blo original
    cmp r0, #FONT_COUNT
    bhi original
    adds r4, #1
    adds r0, #0x3f
    lsls r0, r0, #8
    adds r0, #0x9f
converted:
    ldr r3, converted_return
    bx r3
original:
    adds r0, r4, #0
    adds r1, r6, #0
    ldr r3, original_return
    bx r3
call_r3:
    bx r3
    .balign 4, 0
wrap_function: .word 0x0800152d
original_return: .word 0x0800167d
converted_return: .word 0x08001681
