    ldrb r1, [r0]
    cmp r1, #127
    bne original
    ldr r3, decoder
    bl call_r3
    adds r1, r0, #1
    beq fatal
    adds r6, #3
    lsls r0, r0, #1
    ldr r1, large_codes
    ldrh r0, [r1, r0]
    b converted
original:
    adds r6, #1
    mov r1, r8
    ldr r3, converter_function
    bl call_r3
converted:
    ldr r3, converted_return
    bx r3
fatal:
    ldr r0, diagnostic_stop
    bx r0
call_r3:
    bx r3
    .balign 4, 0
decoder: .word 0x08c00501
large_codes: .word 0x08c0a000
converter_function: .word 0x080050ad
converted_return: .word 0x08005081
diagnostic_stop: .word 0x08c00701
