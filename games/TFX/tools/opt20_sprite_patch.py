from pathlib import Path
p=Path('src/TFXHD.s');s=p.read_bytes().decode('latin1')
assert 'mask_sprite_040:' not in s
new='''; CPU mask merge for the new 040 renderer. Parameters are the original
; MaskSprite blitter-style block; keep its caller's preserved registers.
mask_sprite_040:
        movem.l d0/d6/a0-a1/a3-a4/a6,-(sp)
        move.l  mask_sprite_params(pc),a6
        move.l  18(a6),a0
        move.l  22(a6),a1
        move.w  16(a6),a2
        move.l  30(a6),a3
        move.w  10(a6),a4
        move.w  12(a6),a5
        move.w  4(a6),d6
        move.l  (a6),d7
        rol.w   #4,d6
        and.w   #15,d6
        neg.w   d6
        add.w   #16,d6
        move.w  8(a6),d0
        move.w  d0,d1
        and.w   #63,d1
        lsr.w   #6,d0
        subq.w  #1,d0
        subq.w  #1,d1
        cmp.w   #16,d6
        beq.b   .alignedrow
.row:
        move.w  d1,d2
.word:
        moveq   #0,d3
        move.w  (a0)+,d3
        moveq   #0,d4
        move.w  (a1)+,d4
        cmp.w   d1,d2
        bne.b   .notfirst
        swap    d7
        and.w   d7,d3
        swap    d7
.notfirst:
        tst.w   d2
        bne.b   .notlast
        and.w   d7,d3
.notlast:
        lsl.l   d6,d3
        lsl.l   d6,d4
        move.l  (a3),d5
        eor.l   d5,d4
        and.l   d3,d4
        eor.l   d4,d5
        move.l  d5,(a3)
        addq.l  #2,a3
        dbf     d2,.word
        adda.w  a4,a0
        adda.w  a5,a1
        adda.w  a2,a3
        dbf     d0,.row
        bra.b   .out
.alignedrow:
        ; Shift 16 affects only the first destination word. Avoid overlapping
        ; longword reads/writes and both variable shifts for aligned sprites.
        move.w  d1,d2
.alignedword:
        move.w  (a0)+,d3
        move.w  (a1)+,d4
        cmp.w   d1,d2
        bne.b   .alignednotfirst
        swap    d7
        and.w   d7,d3
        swap    d7
.alignednotfirst:
        tst.w   d2
        bne.b   .alignednotlast
        and.w   d7,d3
.alignednotlast:
        move.w  (a3),d5
        eor.w   d5,d4
        and.w   d3,d4
        eor.w   d4,d5
        move.w  d5,(a3)+
        dbf     d2,.alignedword
        adda.w  a4,a0
        adda.w  a5,a1
        adda.w  a2,a3
        dbf     d0,.alignedrow
.out:
        movem.l (sp)+,d0/d6/a0-a1/a3-a4/a6
        rts
mask_sprite_params: dc.l 0

'''.replace('\n','\r\n')
s=s.replace('start_frame:\r\n',new+'start_frame:\r\n',1)
anchor='pl_fpu_new_render_040:\r\n        PL_START\r\n        PL_IFC4X 2\r\n        PL_ELSE\r\n';assert anchor in s
s=s.replace(anchor,anchor+'        PL_P    $4e53a,mask_sprite_040\r\n        PL_GA   $4e518,mask_sprite_params\r\n',1)
p.write_bytes(s.encode('latin1'))
