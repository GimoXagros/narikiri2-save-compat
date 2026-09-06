    push {r4, r5, r6, r7, lr}
    sub sp, #12
    str r0, [sp]
    str r1, [sp, #4]
    adds r4, r2, #0
    movs r0, #0
    str r0, [sp, #8]
    ldr r3, info_globals
    bl call_r3
    ldr r6, [r0]
    ldr r3, info_map
    bl call_r3
    ldr r1, [sp, #4]
    lsls r1, r1, #4
    ldr r2, [sp]
    adds r1, r1, r2
    adds r5, r0, r1
    ldr r1, [sp, #4]
    lsrs r1, r1, #1
    lsls r1, r1, #4
    adds r7, r1, r2
    adds r7, #72
loop:
    ldrb r0, [r4]
    cmp r0, #0
    beq done
    cmp r0, #127
    beq banked
    cmp r0, #18
    bne legacy
    ldr r0, [sp, #8]
    movs r1, #1
    eors r0, r1
    str r0, [sp, #8]
    adds r4, #1
    b loop
legacy:
    ldr r1, [sp, #8]
    lsls r1, r1, #6
    adds r0, r0, r1
    lsls r0, r0, #1
    ldr r1, legacy_lookup
    adds r0, r0, r1
    movs r1, #0
    ldrsh r0, [r0, r1]
    ldrb r0, [r6, r0]
    adds r4, #1
    b write_map
banked:
    cmp r7, #72
    blo fatal
    cmp r7, #135
    bhi fatal
    adds r0, r4, #0
    ldr r3, decode
    bl call_r3
    adds r1, r0, #1
    beq fatal
    lsls r0, r0, #5
    ldr r1, font
    adds r0, r0, r1
    lsls r1, r7, #6
    ldr r2, affine_font
    adds r1, r1, r2
    movs r2, #32
copy:
    ldrb r3, [r0]
    push {r0, r2}
    movs r2, #15
    ands r2, r3
    cmp r2, #0
    beq low_background
    movs r2, #175
    b low_ready
low_background:
    movs r2, #161
low_ready:
    lsrs r3, r3, #4
    cmp r3, #0
    beq high_background
    movs r3, #175
    b high_ready
high_background:
    movs r3, #161
high_ready:
    lsls r3, r3, #8
    orrs r3, r2
    strh r3, [r1]
    pop {r0, r2}
    adds r0, #1
    adds r1, #2
    subs r2, #1
    bne copy
    adds r0, r7, #0
    adds r4, #3
write_map:
    strb r0, [r5]
    adds r5, #1
    adds r7, #1
    b loop
done:
    add sp, #12
    pop {r4, r5, r6, r7}
    pop {r0}
    bx r0
fatal:
    ldr r0, stop
    bx r0
call_r3:
    bx r3
    .balign 4, 0
info_globals: .word 0x0804f6a5
info_map: .word 0x0804f699
legacy_lookup: .word 0x083afb82
decode: .word 0x08c00501
font: .word 0x08c02000
affine_font: .word 0x06008000
stop: .word 0x08c00701
