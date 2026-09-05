    push {lr}
    mov sb, r0
    ldr r3, store_name
    bl call_r3
    pop {r3}
    mov lr, r3
    ldr r1, flag_offset
    ldr r3, continuation
    bx r3
call_r3:
    bx r3
    .balign 4, 0
store_name: .word 0x08c1e801
flag_offset: .word 0x103
continuation: .word 0x0801d761
