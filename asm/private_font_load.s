    ldr r0, font_base_pointer
    ldr r0, [r0]
    ldr r1, required_font_base
    cmp r0, r1
    bne done
    ldr r0, tilemap_pointer
    ldr r0, [r0]
    ldr r1, required_tilemap
    cmp r0, r1
    bne done
    ldr r0, tilebase_pointer
    ldr r0, [r0]
    cmp r0, #0
    bne done
    ldr r0, mode_pointer
    ldrb r0, [r0]
    cmp r0, #0
    beq transparent
    cmp r0, #11
    bne done
    ldr r1, solid_font
    b copy_setup
transparent:
    ldr r1, clear_font
copy_setup:
    ldr r2, private_vram
    movs r3, #FONT_COUNT
    lsls r3, r3, #3
copy_word:
    ldr r0, [r1]
    str r0, [r2]
    adds r1, #4
    adds r2, #4
    subs r3, #1
    bne copy_word
done:
    adds r0, r7, #0
    pop {r4, r5, r6, r7}
    pop {r1}
    bx r1
    .balign 4, 0
font_base_pointer: .word 0x03000050
required_font_base: .word 0x0600c000
tilemap_pointer: .word 0x0300004c
required_tilemap: .word 0x0600f800
tilebase_pointer: .word 0x03000054
mode_pointer: .word 0x0300145a
clear_font: .word 0x08c01000
solid_font: .word 0x08c01400
private_vram: .word 0x0600ef00
