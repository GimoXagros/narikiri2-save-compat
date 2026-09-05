    ldr r3, wrap_function
    bl call_r3
    ldrb r0, [r4]
    cmp r0, #127
    bne original
    adds r0, r4, #0
    ldr r3, decoder
    bl call_r3
    adds r1, r0, #1
    beq fatal
    adds r4, #2
    lsls r0, r0, #1
    ldr r1, large_codes
    ldrh r0, [r1, r0]
    ldr r3, converted_return
    bx r3
original:
    adds r0, r4, #0
    adds r1, r6, #0
    ldr r3, original_return
    bx r3
fatal:
    ldr r0, diagnostic_stop
    bx r0
call_r3:
    bx r3
    .balign 4, 0
wrap_function: .word 0x0800152d
decoder: .word 0x08c00501
large_codes: .word 0x08c0a000
original_return: .word 0x0800167d
converted_return: .word 0x08001681
diagnostic_stop: .word 0x08c00701
