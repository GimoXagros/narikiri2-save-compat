    push {r0, r1, lr}
    ldr r3, display_control
    ldrh r3, [r3]
    movs r2, #7
    ands r3, r2
    movs r2, #240
    cmp r3, #1
    bne size_ready
    movs r2, #128
size_ready:
    lsls r2, r2, #4
    ldr r3, copy_bytes
    bl call_r3
    pop {r0, r1, r3}
    mov lr, r3
    ldr r3, continuation
    bx r3
call_r3:
    bx r3
    .balign 4, 0
display_control: .word 0x03000010
copy_bytes: .word 0x08003129
continuation: .word 0x08001f31
