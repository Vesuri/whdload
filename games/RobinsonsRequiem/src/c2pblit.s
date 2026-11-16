; The ECS game's chunky-to-planar conversion for the 68000 with the blitter (docs/performance.md,
; ECS plan step 11; docs/internals.md, "ECS improvements", item 7). RobinsonSRequiemEcs.asm
; includes it after c2p000.s; entered as _c2p000 is, with the same registers.
;
; _c2p000's exchanges, a 16-pixel block at a time: two pairs of chunky longwords packed into
; d0 and d2 (pixels 0-7 and 8-15; a 4-bit exchange and a byte select each), then an 8-bit
; and a 1-bit exchange of d0 with d2, the words routed (the 16-bit exchange) and a 2-bit
; exchange. Here the CPU packs and writes the four words to four streams in chip memory
; (S0 = d0.hi, S1 = d0.lo, S2 = d2.hi, S3 = d2.lo, a row of each after the other, 8W bytes a
; row for W blocks), and the blitter does the rest: three stages of the same exchange,
;   X' = (X & ~m) | ((Y >> s) & m)     ascending, A = X, B = Y shifted, C = m (LF $d8)
;   Y' = (Y & m) | ((X << s) & ~m)     descending, A = Y, B = X shifted, C = m (LF $e4)
; the bits shifted in from the next word landing where the mask takes A. Stages 1 (8 bits,
; m $00ff) and 2 (1 bit, $5555) pair S0 with S2 and S1 with S3, both lanes in one blit 2W
; words wide (X: S0 and S1, Y: S2 and S3), stream set 1 to set 2 and back. Stage 3 (2 bits,
; $3333) pairs S1 with S0 and S3 with S2 into the planes: plane 3 = X' (X S1, Y S0), plane
; 2 = X' (S3, S2), plane 1 = Y' (Y S0, X S1), plane 0 = Y' (S2, S3).
;
; Eight blits a band of rows, queued in that order: at the end of each row, when a band is
; written and the blitter is idle, the CPU starts the next blit, so the blitter works while
; the CPU converts the next rows. The bands are 32 rows, the first what is left over, and
; the last two 16 and 8, so that little is left after the last row: the CPU then starts the
; rest as each blit ends, and returns with the blitter idle (START's own blits, hunk 2,
; start without a wait). _cbinst allocates the streams (two sets) in chip memory and the
; blits' table and state in any; a rectangle of more than CBUF bytes of streams goes to
; _c2p000. tools/rr_ecsc2pcheck.py checks it against START's loop under Unicorn, with a
; model of the blitter.

CBUF    = 16000                         ; a stream set: 256 x 125 or 320 x 100 pixels
JOBSZ   = 28                            ; a blit's entry in the table
; the state, then the table
S_JN    = 0                             ; w: the next blit's entry (from the state)
S_KB    = 2                             ; w: its band
S_BR    = 4                             ; w: the bands the CPU has written
S_NB    = 6                             ; w: the bands
S_BRC   = 8                             ; w: rows left in the CPU's band
S_SZH   = 10                            ; w: the started band's rows << 6
S_8W    = 12                            ; w: a stream row (8W bytes)
S_PS    = 14                            ; w: a plane row (2W bytes + the modulo)
S_IB    = 16                            ; l: the started band's stream rows
S_IP    = 20                            ; l: and plane rows
S_LB    = 24                            ; l: to its last row, streams
S_LP    = 28                            ; l: and planes
S_PL    = 32                            ; 4 l: planes 0-3
S_BS    = 48                            ; 16 w: the bands' rows
TAB     = 80
CB_SIZE = TAB+8*JOBSZ

; a2 becomes _c2pblit when the memory is there
_cbinst
        IFND C2PBLIT_OFF
        movem.l d0-d1/a0-a1/a6,-(a7)
        move.l  4.w,a6
        move.l  #2*CBUF,d0
        moveq   #MEMF_CHIP,d1
        jsr     _LVOAllocMem(a6)
        lea     _cbbuf(pc),a0
        move.l  d0,(a0)
        beq     .x
        moveq   #CB_SIZE/4,d0
        lsl.l   #2,d0
        moveq   #MEMF_PUBLIC,d1
        jsr     _LVOAllocMem(a6)
        lea     _cbtab(pc),a0
        move.l  d0,(a0)
        bne     .ok
        move.l  _cbbuf(pc),a1
        move.l  #2*CBUF,d0
        jsr     _LVOFreeMem(a6)
        bra     .x
.ok     lea     _c2pblit(pc),a2
        IFD C2PCHECK
        move.l  #CK_SIZE,d0
        moveq   #MEMF_PUBLIC,d1
        jsr     _LVOAllocMem(a6)
        lea     _cbck(pc),a0
        move.l  d0,(a0)
        ENDC
.x      movem.l (a7)+,d0-d1/a0-a1/a6
        ENDC
        rts

; blits: con0, con1, cdat, flags (1 descending, 2 stage 3), then A, B and D: set << 2 + the
; stream, or $100 + the plane
_cbtmpl dc.w    $0dd8,$8000,$00ff,0,0,2,4+0
        dc.w    $0de4,$8002,$00ff,1,2,0,4+2
        dc.w    $0dd8,$1000,$5555,0,4+0,4+2,0
        dc.w    $0de4,$1002,$5555,1,4+2,4+0,2
        dc.w    $0dd8,$2000,$3333,2,1,0,$103
        dc.w    $0dd8,$2000,$3333,2,3,2,$102
        dc.w    $0de4,$2002,$3333,3,0,1,$101
        dc.w    $0de4,$2002,$3333,3,2,3,$100

_c2pblit
        IFD C2PCHECK
        lea     _ckregs(pc),a3
        movem.l d6-d7/a0-a2/a6,(a3)
        ENDC
        moveq   #0,d0
        move.w  d6,d0
        addq.w  #1,d0                   ; W
        moveq   #0,d1
        move.w  d7,d1
        addq.w  #1,d1                   ; rows
        move.w  d0,d2
        lsl.w   #3,d2
        mulu    d1,d2
        cmp.l   #CBUF,d2
        bhi     _c2p000
        move.l  _cbtab(pc),a5
        move.l  a1,S_PL(a5)
        lea     C2P_ECSBPL(a1),a3
        move.l  a3,S_PL+4(a5)
        move.l  a2,S_PL+8(a5)
        lea     C2P_ECSBPL(a2),a3
        move.l  a3,S_PL+12(a5)
        move.l  _cbbuf(pc),a2           ; the streams
        add.w   d0,d0                   ; d0 2W: a stream's row
        move.w  a6,d7                   ; the plane modulo
        lea     _cbtmpl(pc),a3
        lea     TAB(a5),a4
        moveq   #7,d6
.job    moveq   #0,d2
        moveq   #0,d3
        move.l  (a3)+,(a4)+             ; con0, con1
        move.w  (a3)+,d4                ; cdat
        move.w  (a3)+,d5                ; flags
        move.w  d0,d3                   ; stages 1 and 2: 2W words wide, the other 2W skipped
        add.w   d3,d3
        move.w  d3,d2
        btst    #1,d5
        beq     .wide
        move.w  d0,d3                   ; stage 3: W wide, 3W skipped, into the planes
        add.w   d0,d3
        add.w   d0,d3
        move.w  d3,(a4)+
        move.w  d3,(a4)+
        move.w  d7,(a4)+
        move.w  d0,d2
        bra     .mods
.wide   move.w  d3,(a4)+
        move.w  d3,(a4)+
        move.w  d3,(a4)+
.mods   move.w  d4,(a4)+
        lsr.w   #1,d2
        move.w  d2,(a4)+                ; width
        move.w  d5,(a4)+
        bsr     .ptr
        bsr     .ptr
        bsr     .ptr
        dbf     d6,.job
        move.w  d0,d2
        lsl.w   #2,d2
        move.w  d2,S_8W(a5)
        add.w   d0,d7
        move.w  d7,S_PS(a5)
; the bands, from the end 8, 16, then 32s, the first what is left
        lea     S_BS(a5),a1
        moveq   #0,d5                   ; the bands
        move.w  d1,d2
        moveq   #8,d3
        cmp.w   d3,d2
        bhs     .l8
        move.w  d2,d3
.l8     sub.w   d3,d2                   ; d3 the last band
        moveq   #16,d4
        cmp.w   d4,d2
        bhs     .l16
        move.w  d2,d4
.l16    sub.w   d4,d2                   ; d4 the one before
        beq     .n32
        move.w  d2,d6
        add.w   #31,d6
        lsr.w   #5,d6
        move.w  d6,d5
        subq.w  #1,d6
        lsl.w   #5,d6
        sub.w   d6,d2
        move.w  d2,(a1)+                ; the first
        move.w  d5,d6
        subq.w  #1,d6
        bra     .t32
.f32    move.w  #32,(a1)+
.t32    dbf     d6,.f32
.n32    tst.w   d4
        beq     .n16
        move.w  d4,(a1)+
        addq.w  #1,d5
.n16    move.w  d3,(a1)+
        addq.w  #1,d5
        clr.w   (a1)
        move.w  d5,S_NB(a5)
        move.w  #TAB,S_JN(a5)
        clr.w   S_KB(a5)
        clr.w   S_BR(a5)
        move.w  S_BS(a5),d3
        move.w  d3,S_BRC(a5)
        bsr     .bandv
; the CPU: d5 $0f0f0f0f, d6.w the blocks and d6.h 6W, d7.w W - 1 and d7.h the chunky
; modulo, a1-a4 S0-S3, a5 the state, a6 the custom chips
        move.l  _c2pmod(pc),a3
        move.w  (a3),d7
        swap    d7
        move.w  d0,d7
        lsr.w   #1,d7
        subq.w  #1,d7
        move.w  d0,d6
        add.w   d0,d6
        add.w   d0,d6
        swap    d6
        lea     (a2),a1
        lea     (a1,d0.w),a2
        lea     (a2,d0.w),a3
        lea     (a3,d0.w),a4
        lea     $dff000,a6
        move.l  #$0f0f0f0f,d5
        move.w  d1,-(a7)
        subq.w  #1,(a7)
.row    move.w  d7,d6
.blk    movem.l (a0)+,d0-d3             ; pixels 0-3, 4-7, 8-11, 12-15
        move.l  d1,d4                   ; _c2p000's pack, each word written as it is ready
        lsr.l   #4,d4
        eor.l   d0,d4
        and.l   d5,d4
        eor.l   d4,d0
        lsl.l   #4,d4
        eor.l   d4,d1
        move.b  d1,d0
        move.w  d0,(a1)+                ; S0
        swap    d0
        swap    d1
        move.b  d1,d0
        move.w  d0,(a2)+                ; S1
        move.l  d3,d4
        lsr.l   #4,d4
        eor.l   d2,d4
        and.l   d5,d4
        eor.l   d4,d2
        lsl.l   #4,d4
        eor.l   d4,d3
        move.b  d3,d2
        move.w  d2,(a3)+                ; S2
        swap    d2
        swap    d3
        move.b  d3,d2
        move.w  d2,(a4)+                ; S3
        dbf     d6,.blk
        swap    d7
        adda.w  d7,a0
        swap    d7
        swap    d6
        adda.w  d6,a1
        adda.w  d6,a2
        adda.w  d6,a3
        adda.w  d6,a4
        swap    d6
        move.w  S_KB(a5),d0             ; a band written and the blitter idle: the next blit
        cmp.w   S_BR(a5),d0
        bhs     .nk
        btst    #6,2(a6)
        bne     .nk
        bsr     .kick
.nk     subq.w  #1,S_BRC(a5)
        bne     .nb
        move.w  S_BR(a5),d0             ; a band written
        addq.w  #1,d0
        move.w  d0,S_BR(a5)
        add.w   d0,d0
        move.w  S_BS(a5,d0.w),S_BRC(a5)
.nb     subq.w  #1,(a7)
        bcc     .row
        addq.l  #2,a7
.drain  move.w  S_KB(a5),d0
        cmp.w   S_NB(a5),d0
        bhs     .done
        tst.b   2(a6)
.wt     btst    #6,2(a6)
        bne     .wt
        bsr     .kick
        bra     .drain
.done   tst.b   2(a6)
.wd     btst    #6,2(a6)
        bne     .wd
        IFD C2PCHECK
        bsr     _cbcheck
        ENDC
        movem.l (a7)+,d0-a6
        rts


; the next blit; a5 the state, a6 the custom chips; d0-d4 changed
.kick   move.l  a4,-(a7)
        move.l  a5,a4
        adda.w  (a5),a4                 ; S_JN
        move.l  (a4)+,$40(a6)           ; BLTCON0, BLTCON1
        moveq   #-1,d0
        move.l  d0,$44(a6)              ; BLTAFWM, BLTALWM
        move.l  (a4)+,$62(a6)           ; BLTBMOD, BLTAMOD
        move.w  (a4)+,$66(a6)           ; BLTDMOD
        move.w  (a4)+,$70(a6)           ; BLTCDAT
        move.w  (a4)+,d1
        move.w  (a4)+,d2
        movem.l (a4),d0/d3/d4
        btst    #0,d2
        beq     .asc
        add.l   S_LB(a5),d0             ; descending: from the band's last row
        add.l   S_LB(a5),d3
        btst    #1,d2
        bne     .lp
        add.l   S_LB(a5),d4
        bra     .asc
.lp     add.l   S_LP(a5),d4
.asc    move.l  d0,$50(a6)              ; BLTAPT
        move.l  d3,$4c(a6)              ; BLTBPT
        move.l  d4,$54(a6)              ; BLTDPT
        or.w    S_SZH(a5),d1
        move.w  d1,$58(a6)              ; BLTSIZE: started
        move.l  S_IB(a5),d0
        add.l   d0,(a4)+
        add.l   d0,(a4)+
        btst    #1,d2
        beq     .ib
        move.l  S_IP(a5),d0
.ib     add.l   d0,(a4)
        move.w  (a5),d0
        add.w   #JOBSZ,d0
        cmp.w   #TAB+8*JOBSZ,d0
        blo     .j
        move.w  S_KB(a5),d3             ; the band's last blit: the next band
        addq.w  #1,d3
        move.w  d3,S_KB(a5)
        add.w   d3,d3
        move.w  S_BS(a5,d3.w),d3
        beq     .z
        bsr     .bandv
.z      move.w  #TAB,d0
.j      move.w  d0,(a5)
        move.l  (a7)+,a4
        rts

; the band of d3.w rows (1-32) to start next: its BLTSIZE height, its rows in the streams
; and planes and its last row's; a5 the state; d3 and d4 changed
.bandv  move.w  d3,d4
        lsl.w   #6,d4
        move.w  d4,S_SZH(a5)
        move.w  S_8W(a5),d4
        mulu    d3,d4
        move.l  d4,S_IB(a5)
        sub.w   S_8W(a5),d4
        move.l  d4,S_LB(a5)
        move.w  S_PS(a5),d4
        mulu    d3,d4
        move.l  d4,S_IP(a5)
        sub.w   S_PS(a5),d4
        move.l  d4,S_LP(a5)
        rts

; a blit's pointer from the template's code at (a3)+ to (a4)+: a2 the streams, a5 the state,
; d0 2W, d2 the width, d5 the flags; d3 and d4 changed
.ptr    move.w  (a3)+,d3
        btst    #8,d3
        beq     .buf
        and.w   #3,d3
        lsl.w   #2,d3
        move.l  S_PL(a5,d3.w),d4
        bra     .desc
.buf    moveq   #3,d4
        and.w   d3,d4
        mulu    d0,d4
        btst    #2,d3
        beq     .s1
        add.l   #CBUF,d4
.s1     add.l   a2,d4
.desc   btst    #0,d5
        beq     .put
        add.l   d2,d4                   ; the row's last word
        add.l   d2,d4
        subq.l  #2,d4
.put    move.l  d4,(a4)+
        rts

        IFD C2PCHECK
; A test build's check: the same rectangle again by _c2p000 into a copy of the planes (planes
; 0 and 2 at CK_P0 and CK_P2 of _cbck, each with its pair C2P_ECSBPL on), compared word for
; word with what the blits wrote; _ckcalls counts the conversions, _ckbad those that differed.
CK_P0   = 0
CK_P2   = 2*C2P_ECSBPL
CK_SIZE = 4*C2P_ECSBPL
_cbcheck
        lea     _ckregs(pc),a3          ; the entry's registers
        movem.l (a3),d6-d7/a0-a2/a6
        move.l  _cbck(pc),d0
        beq     .ckx
        move.l  a1,-(a7)
        move.l  a2,-(a7)
        move.l  d0,a3
        lea     CK_P0(a3),a1
        lea     CK_P2(a3),a2
        pea     .ckb(pc)                ; as START enters it: its return, then the registers
        movem.l d0-a6,-(a7)
        bra     _c2p000
.ckb    move.l  (a7)+,a4                ; the planes' plane 2
        move.l  (a7)+,a5                ; and plane 0
        move.l  _cbck(pc),a3
        lea     _ckcalls(pc),a0
        addq.l  #1,(a0)
        move.w  d6,d5                   ; a plane row: 2W + the modulo
        addq.w  #1,d5
        add.w   d5,d5
        add.w   a6,d5
        moveq   #3,d4                   ; planes 0, 1 (a5), 2, 3 (a4)
.ckp    move.l  a5,a0
        lea     CK_P0(a3),a1
        btst    #1,d4
        bne     .ck0
        move.l  a4,a0
        lea     CK_P2(a3),a1
.ck0    btst    #0,d4
        bne     .ck1
        lea     C2P_ECSBPL(a0),a0
        lea     C2P_ECSBPL(a1),a1
.ck1    move.w  d7,d3                   ; rows - 1
.ckr    move.w  d6,d2                   ; blocks - 1
        move.l  a0,d0
        move.l  a1,d1
.ckw    cmpm.w  (a0)+,(a1)+
        bne     .bad
        dbf     d2,.ckw
        move.l  d0,a0
        move.l  d1,a1
        adda.w  d5,a0
        adda.w  d5,a1
        dbf     d3,.ckr
        dbf     d4,.ckp
        bra     .ckx
.bad    lea     _ckbad(pc),a0
        addq.l  #1,(a0)
.ckx    rts
        ENDC

_cbbuf  dc.l    0                       ; the streams: two sets of CBUF bytes, chip memory
_cbtab  dc.l    0                       ; the state and the blits' table (CB_SIZE)
        IFD C2PCHECK
_cbck   dc.l    0                       ; the check's copy of the planes (CK_SIZE)
_ckcalls dc.l   0
_ckbad  dc.l    0
_ckregs dc.l    0,0,0,0,0,0                 ; d6, d7, a0-a2, a6 at the entry
        ENDC
