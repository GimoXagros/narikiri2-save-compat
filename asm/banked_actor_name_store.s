    adds r2, r1, #0
scan:
    ldrb r3, [r2]
    cmp r3, #0
    beq legacy
    cmp r3, #127
    beq indirect
    adds r2, #1
    b scan
indirect:
    ldr r2, signature
    str r2, [r0]
    str r1, [r0, #4]
    movs r2, #0
    strh r2, [r0, #8]
    bx lr
legacy:
    ldr r3, original_copy
    bx r3
    .balign 4, 0
signature: .word 0x444e007f
original_copy: .word 0x080a6b91
