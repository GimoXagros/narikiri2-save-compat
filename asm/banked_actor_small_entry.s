    push {r0, lr}
    adds r0, r1, #0
    ldr r3, resolve_name
    bl call_r3
    adds r1, r0, #0
    pop {r0, r3}
    mov lr, r3
    push {r4, r5, r6, r7, lr}
    sub sp, #4
    adds r5, r0, #0
    str r1, [sp]
    ldr r3, continuation
    bx r3
call_r3:
    bx r3
    .balign 4, 0
resolve_name: .word 0x08c1e881
continuation: .word 0x08001ad1
