    push {lr}
    ldr r1, [r6]
    ldr r3, store_name
    bl call_r3
    pop {r3}
    mov lr, r3
    ldr r0, terminator_offset
    ldr r3, continuation
    bx r3
call_r3:
    bx r3
    .balign 4, 0
store_name: .word 0x08c1e801
terminator_offset: .word 0x145
continuation: .word 0x0801dc71
