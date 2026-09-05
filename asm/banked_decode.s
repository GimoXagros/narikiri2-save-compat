    push {r1, r2, r3, lr}
    ldrb r1, [r0]
    cmp r1, #127
    bne invalid
    ldrb r1, [r0, #1]
    subs r1, #1
    cmp r1, #30
    bhi invalid
    ldrb r2, [r0, #2]
    subs r2, #1
    cmp r2, #30
    bhi invalid
    lsls r0, r1, #5
    subs r0, r0, r1
    adds r0, r0, r2
    ldr r3, glyph_count
    cmp r0, r3
    bhs invalid
    b done
invalid:
    movs r0, #0
    mvns r0, r0
done:
    pop {r1, r2, r3}
    pop {r3}
    bx r3
    .balign 4, 0
glyph_count: .word FONT_COUNT
