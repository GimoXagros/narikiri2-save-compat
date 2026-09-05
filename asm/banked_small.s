    cmp r4, #127
    bne original
    push {r1, r2, r3, r5, r6, r7, lr}
    sub sp, #4
    adds r0, r2, #0
    ldr r3, tile_getter
    bl call_r3
    adds r4, r0, #0
    adds r0, #1
    beq fatal
    adds r4, #16
    ldr r0, [sp, #32]
    adds r0, #2
    str r0, [sp, #32]
    add sp, #4
    pop {r1, r2, r3, r5, r6, r7}
    pop {r0}
    mov lr, r0
    b ascii_path
original:
    adds r0, r4, #0
    subs r0, #0x20
    cmp r0, #0x5f
    bhi kana_path
ascii_path:
    ldr r0, ascii_return
    bx r0
kana_path:
    ldr r0, kana_return
    bx r0
fatal:
    ldr r0, diagnostic_stop
    bx r0
call_r3:
    bx r3
    .balign 4, 0
tile_getter: .word 0x08c00601
ascii_return: .word 0x08001af9
kana_return: .word 0x08001b29
diagnostic_stop: .word 0x08c00701
