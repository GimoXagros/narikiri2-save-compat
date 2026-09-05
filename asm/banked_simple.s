    cmp r2, #127
    bne original
    push {r0, r1, r3, r4, r5, r6, r7, lr}
    adds r0, r3, #0
    ldr r3, tile_getter
    bl call_r3
    adds r2, r0, #0
    adds r0, #1
    beq fatal
    adds r2, #16
    pop {r0, r1, r3, r4, r5, r6, r7}
    pop {r0}
    mov lr, r0
    adds r3, #2
    b ascii_path
original:
    adds r0, r2, #0
    subs r0, #0x20
    cmp r0, #0x5e
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
ascii_return: .word 0x08001e19
kana_return: .word 0x08001e29
diagnostic_stop: .word 0x08c00701
