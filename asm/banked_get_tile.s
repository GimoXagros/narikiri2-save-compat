    push {r1, r2, r3, lr}
    ldr r3, decoder
    bl call_r3
    adds r1, r0, #1
    beq done
    lsls r0, r0, #5
    ldr r1, palette_mode
    ldrb r1, [r1]
    cmp r1, #11
    beq solid
    ldr r1, clear_font
    b get
solid:
    ldr r1, solid_font
get:
    adds r0, r0, r1
    ldr r3, cache
    bl call_r3
done:
    pop {r1, r2, r3}
    pop {r3}
    bx r3
call_r3:
    bx r3
    .balign 4, 0
decoder: .word 0x08c00501
cache: .word 0x08c00801
palette_mode: .word 0x0300145a
clear_font: .word 0x08c02000
solid_font: .word 0x08c06000
