    ldrb r1, [r0]
    cmp r1, #0x7f
    bne original
    ldrb r1, [r0, #1]
    cmp r1, #1
    blo original
    cmp r1, #FONT_COUNT
    bhi original
    adds r6, #2
    adds r0, r1, #0
    adds r0, #0x3f
    lsls r0, r0, #8
    adds r0, #0x9f
converted:
    ldr r3, converted_return
    bx r3
original:
    adds r6, #1
    mov r1, r8
    ldr r3, converter_function
    bl call_r3
    b converted
call_r3:
    bx r3
    .balign 4, 0
converter_function: .word 0x080050ad
converted_return: .word 0x08005081
