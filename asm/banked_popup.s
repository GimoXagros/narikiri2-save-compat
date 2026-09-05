    adds r2, r1, #0
scan:
    ldrb r3, [r2]
    cmp r3, #0
    beq original
    cmp r3, #127
    beq banked
    cmp r3, #128
    blo scan_one
    cmp r3, #159
    bls scan_two
    cmp r3, #224
    blo scan_one
scan_two:
    adds r2, #1
scan_one:
    adds r2, #1
    b scan
original:
    push {r4, r5, r6, lr}
    adds r6, r1, #0
    movs r3, #0
    adds r4, r0, #4
    ldr r2, original_return
    bx r2
banked:
    push {r4, r5, r6, r7, lr}
    sub sp, #12
    adds r4, r0, #4
    adds r5, r1, #0
    adds r7, r1, #0
    movs r6, #0
count_loop:
    ldrb r0, [r7]
    cmp r0, #0
    beq padding
    cmp r0, #127
    bne count_ascii
    adds r0, r7, #0
    ldr r3, decoder
    bl call_r3
    adds r0, #1
    beq fatal
    adds r7, #2
    b count_one
count_ascii:
    subs r0, #32
    cmp r0, #94
    bhi fatal
count_one:
    adds r7, #1
    adds r6, #1
    cmp r6, #15
    bhi fatal
    b count_loop
padding:
    adds r0, r6, #1
    lsrs r0, r0, #1
    movs r1, #9
    subs r1, r1, r0
    movs r0, #129
    movs r2, #64
pad_loop:
    cmp r1, #0
    beq convert_loop
    strb r0, [r4]
    strb r2, [r4, #1]
    adds r4, #2
    subs r1, #1
    b pad_loop
convert_loop:
    ldrb r0, [r5]
    cmp r0, #0
    beq finish
    cmp r0, #127
    bne convert_ascii
    adds r0, r5, #0
    ldr r3, decoder
    bl call_r3
    lsls r0, r0, #1
    ldr r1, large_codes
    ldrh r0, [r1, r0]
    adds r5, #3
    b write_code
convert_ascii:
    adds r0, r5, #0
    movs r1, #0
    ldr r3, ascii_converter
    bl call_r3
    adds r5, #1
write_code:
    strb r0, [r4]
    lsrs r0, r0, #8
    strb r0, [r4, #1]
    adds r4, #2
    b convert_loop
finish:
    movs r0, #0
    strb r0, [r4]
    add sp, #12
    pop {r4, r5, r6, r7}
    pop {r1}
    bx r1
fatal:
    ldr r0, diagnostic_stop
    bx r0
call_r3:
    bx r3
    .balign 4, 0
original_return: .word 0x08025d09
decoder: .word 0x08c00501
large_codes: .word 0x08c0a000
ascii_converter: .word 0x080050ad
diagnostic_stop: .word 0x08c00701
