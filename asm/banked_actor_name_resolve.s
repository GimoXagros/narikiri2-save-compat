    ldrb r2, [r0]
    cmp r2, #127
    bne done
    ldrb r2, [r0, #1]
    cmp r2, #0
    bne done
    ldrh r2, [r0, #2]
    ldr r3, signature_tail
    cmp r2, r3
    bne done
    ldr r0, [r0, #4]
    lsrs r2, r0, #24
    cmp r2, #2
    beq done
    cmp r2, #3
    beq done
    cmp r2, #8
    beq done
    ldr r3, failure
    bx r3
done:
    bx lr
    .balign 4, 0
signature_tail: .word 0x444e
failure: .word 0x08c00701
