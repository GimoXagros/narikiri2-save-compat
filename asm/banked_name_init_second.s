    ldr r1, source_pointer
    ldr r1, [r1]
    push {r0, r2, r3}
    adds r0, #60
    adds r3, r1, #0
    movs r2, #0
copy:
    ldrb r1, [r3, r2]
    strb r1, [r0, r2]
    cmp r1, #0
    beq done
    adds r2, #1
    cmp r2, #19
    blo copy
    ldr r0, failure
    bx r0
done:
    ldr r1, [r3]
    pop {r0, r2, r3}
    adds r0, #79
    ldr r3, resume
    bx r3
    .balign 4, 0
source_pointer: .word 0x08009788
resume: .word 0x0800973d
failure: .word 0x08c00701
