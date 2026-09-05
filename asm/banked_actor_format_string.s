    push {r1, lr}
    ldr r3, resolve_name
    bl call_r3
    pop {r1, r3}
    mov lr, r3
    push {r4, r5, r6, lr}
    adds r4, r0, #0
    adds r5, r1, #0
    ldr r3, count_text
    bl call_r3
    ldr r3, continuation
    bx r3
call_r3:
    bx r3
    .balign 4, 0
resolve_name: .word 0x08c1e881
count_text: .word 0x080028a5
continuation: .word 0x080025e3
