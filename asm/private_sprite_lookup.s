    ldr r0, private_byte_index
    cmp r1, r0
    blo original
    subs r1, r1, r0
    ldr r0, private_byte_limit
    cmp r1, r0
    blo private
    ldr r0, private_byte_index
    adds r1, r1, r0
original:
    ldr r0, original_font
    adds r1, r1, r0
    b done
private:
    ldr r0, private_font
    adds r1, r1, r0
done:
    mov r9, r1
    ldr r1, palette_mode
    ldr r0, original_return
    bx r0
    .balign 4, 0
private_byte_index: .word 4992 * 32
private_byte_limit: .word FONT_COUNT * 32
private_font: .word 0x08c01800
original_font: .word 0x080ac3f4
palette_mode: .word 0x0300145a
original_return: .word 0x08002229
