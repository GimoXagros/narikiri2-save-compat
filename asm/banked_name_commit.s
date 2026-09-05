    cmp r0, #127
    beq copy_slot
    cmp r6, #0
    beq copy_slot
    movs r6, #0
    movs r0, #18
    ldr r3, toggle_return
    bx r3
copy_slot:
    ldr r3, copy_return
    bx r3
    .balign 4, 0
toggle_return: .word 0x0801a1f9
copy_return: .word 0x0801a1fd
