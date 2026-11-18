; START's 24-bit pointers above 16 MB (docs/internals.md, "24-bit pointers"), for both
; slaves. START keeps a flag in the top byte of some pointers and masks it off with andi.l
; #$ffffff before using them; among them are the map's 3D elements' pointers into the
; objects' frames, which are in START's fast pool (the slave's ExpMem). With ExpMem above
; 16 MB those pointers lose their address's top byte and the map faults. When ExpMem's low
; 24 bits start at $200000 or above (above every chip address) and it does not cross a
; 16 MB boundary, each andi.l (_m24sites: hunk, register, offset; its bytes checked first,
; 0280+n 00ff ffff) becomes jsr _m24d<n>: the same mask, and a result within ExpMem's low
; 24 bits gets ExpMem's top byte back, so START sees its pointers as with ExpMem below
; 16 MB. Needs _hunk0, _hunk1, _hunk2, _expmem and _expmemsize; assembled for the 68000.
; M24_OFF (a test define): never patched.
;
; _m24patch: d0 0 when ExpMem is below 16 MB or the sites are patched, -1 when they cannot
; be (the caller then keeps the objects' frames out of the fast pool); the other registers
; kept.

_m24patch
        movem.l d1-d3/a0-a2,-(a7)
        move.l  _expmem(pc),d0
        cmp.l   #$ffffff,d0
        bls     .ok
        IFD M24_OFF
        bra     .no
        ENDC
        move.l  d0,d1
        and.l   #$ffffff,d1
        cmp.l   #$200000,d1
        blo     .no
        move.l  d0,d2
        add.l   _expmemsize(pc),d2
        subq.l  #1,d2
        eor.l   d0,d2
        and.l   #$ff000000,d2
        bne     .no                     ; across a 16 MB boundary
        lea     _m24lo(pc),a1
        move.l  d1,(a1)+
        add.l   _expmemsize(pc),d1
        move.l  d1,(a1)+                ; _m24hi
        and.l   #$ff000000,d0
        move.l  d0,(a1)                 ; _m24top
        moveq   #0,d3                   ; 0: check every site, 1: patch
.pass   lea     _m24sites(pc),a2
.site   move.w  (a2)+,d0                ; hunk
        bmi     .last
        move.w  (a2)+,d1                ; register
        move.l  _hunk0(pc),a0
        subq.w  #1,d0
        bmi     .h
        move.l  _hunk1(pc),a0
        subq.w  #1,d0
        bmi     .h
        move.l  _hunk2(pc),a0
.h      add.l   (a2)+,a0
        tst.w   d3
        bne     .put
        move.w  #$0280,d0               ; andi.l #$ffffff,Dn
        add.w   d1,d0
        cmp.w   (a0),d0
        bne     .no
        cmp.l   #$00ffffff,2(a0)
        bne     .no
        bra     .site
.put    move.w  #$4eb9,(a0)+            ; jsr _m24d<n>
        lea     _m24d0(pc),a1
        mulu    #_m24d1-_m24d0,d1
        add.l   d1,a1
        move.l  a1,(a0)
        bra     .site
.last   addq.w  #1,d3
        cmp.w   #2,d3
        blo     .pass
.ok     moveq   #0,d0
        bra     .out
.no     moveq   #-1,d0
.out    movem.l (a7)+,d1-d3/a0-a2
        rts

M24     MACRO
_m24d\1 and.l   #$ffffff,d\1
        cmp.l   _m24lo(pc),d\1
        blo.b   .x\@
        cmp.l   _m24hi(pc),d\1
        bhs.b   .x\@
        or.l    _m24top(pc),d\1
.x\@    rts
        ENDM
        M24     0
        M24     1
        M24     2
        M24     3

_m24lo          dc.l    0               ; ExpMem's low 24 bits
_m24hi          dc.l    0               ; and its end's
_m24top         dc.l    0               ; its top byte
