    push {r4, r5, r6, r7, lr}
    sub sp, #4
    adds r5, r0, #0
    adds r4, r1, #0
    movs r1, #24
    ldr r3, clear
    bl call_r3
    movs r6, #0
    movs r7, #0
    strb r7, [r5, #25]
next:
    ldrb r2, [r4]
    cmp r2, #0
    beq done
    lsls r0, r7, #2
    adds r1, r5, r0
    cmp r2, #127
    beq private
    cmp r2, #18
    bne legacy
    movs r0, #1
    subs r6, r0, r6
    adds r4, #1
legacy:
    cmp r6, #0
    beq copy_legacy
    movs r0, #18
    strb r0, [r1]
    adds r1, #1
copy_legacy:
    ldrb r0, [r4]
    strb r0, [r1]
    adds r4, #1
    adds r1, #1
    ldrb r2, [r4]
    cmp r2, #222
    beq voiced
    cmp r2, #223
    bne counted
voiced:
    strb r2, [r1]
    adds r4, #1
    b counted
private:
    adds r0, r4, #0
    ldr r3, decode
    push {r1}
    bl call_r3
    pop {r1}
    adds r0, #1
    beq fatal
    ldrb r0, [r4]
    strb r0, [r1]
    ldrb r0, [r4, #1]
    strb r0, [r1, #1]
    ldrb r0, [r4, #2]
    strb r0, [r1, #2]
    adds r4, #3
counted:
    adds r7, #1
    strb r7, [r5, #25]
    cmp r7, #6
    blo next
done:
    adds r0, r5, #0
    ldr r3, redraw
    bl call_r3
    add sp, #4
    pop {r4, r5, r6, r7}
    pop {r0}
    bx r0
fatal:
    ldr r0, failure
    bx r0
call_r3:
    bx r3
    .balign 4, 0
clear: .word 0x08004cb9
decode: .word 0x08c00501
redraw: .word 0x08019f49
failure: .word 0x08c00701
