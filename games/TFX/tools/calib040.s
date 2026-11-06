; calib040 - 68040 instruction and memory timing for the TFX cost model.
;
; Run from a Shell on the real machine (no WHDLoad):  calib040 >RAM:calib.txt
; Each kernel runs with interrupts disabled for at most ~0.1 s, three times;
; the fastest run is reported as CPU cycles per operation at 40 MHz, measured
; with the E-clock (timer.device ReadEClock). Needs a 68040/060 with FPU.
;
; Build: vasmm68k_mot -Fhunkexe -nosym -m68040 -o calib040 calib040.s

_LVOForbid      = -132
_LVOPermit      = -138
_LVODisable     = -120
_LVOEnable      = -126
_LVOAllocMem    = -198
_LVOFreeMem     = -210
_LVOOpenLibrary = -552
_LVOCloseLibrary= -414
_LVOOpenDevice  = -444
_LVOCloseDevice = -450
_LVOVPrintf     = -954
_LVOReadEClock  = -60
MEMF_CHIP       = 2
MEMF_FAST       = 4
MEMF_CLEAR      = $10000
FASTSIZE        = 131072
CHIPSIZE        = 32768
REPEATS         = 3

        section code,code
start:
        movem.l d2-d7/a2-a6,-(sp)
        move.l  $4.w,a6
        lea     dosname(pc),a1
        moveq   #36,d0
        jsr     _LVOOpenLibrary(a6)
        lea     dosbase(pc),a0
        move.l  d0,(a0)
        beq     .exit
        lea     timername(pc),a0
        moveq   #0,d0
        lea     timereq(pc),a1
        moveq   #0,d1
        jsr     _LVOOpenDevice(a6)
        tst.l   d0
        bne     .closedos
        lea     timereq(pc),a0
        lea     timerbase(pc),a1
        move.l  20(a0),(a1)
        move.l  #FASTSIZE,d0
        move.l  #MEMF_FAST!MEMF_CLEAR,d1
        jsr     _LVOAllocMem(a6)
        lea     fastbuf(pc),a0
        move.l  d0,(a0)
        beq     .closetimer
        move.l  #CHIPSIZE,d0
        move.l  #MEMF_CHIP!MEMF_CLEAR,d1
        jsr     _LVOAllocMem(a6)
        lea     chipbuf(pc),a0
        move.l  d0,(a0)
        beq     .freefast

        lea     header(pc),a0
        bsr     print0
        lea     kernels(pc),a4
.next:
        move.l  (a4)+,d0                ; name
        beq.b   .done
        move.l  d0,a3
        move.l  (a4)+,a2                ; kernel
        move.l  (a4)+,d5                ; iterations (d7 for the kernel)
        move.l  (a4)+,d6                ; operations per iteration
        bsr     measure                 ; -> d0 best E-clock ticks
        bsr     report
        bra.b   .next
.done:
        move.l  $4.w,a6
        move.l  chipbuf(pc),a1
        move.l  #CHIPSIZE,d0
        jsr     _LVOFreeMem(a6)
.freefast:
        move.l  $4.w,a6
        move.l  fastbuf(pc),a1
        move.l  #FASTSIZE,d0
        jsr     _LVOFreeMem(a6)
.closetimer:
        move.l  $4.w,a6
        lea     timereq(pc),a1
        jsr     _LVOCloseDevice(a6)
.closedos:
        move.l  $4.w,a6
        move.l  dosbase(pc),a1
        jsr     _LVOCloseLibrary(a6)
.exit:
        movem.l (sp)+,d2-d7/a2-a6
        moveq   #0,d0
        rts

; a2 kernel, d5 iterations. Returns d0 = fewest E-clock ticks of REPEATS runs.
measure:
        movem.l d1-d7/a0-a6,-(sp)
        move.l  #$7fffffff,d4
        moveq   #REPEATS-1,d3
.rep:
        movem.l d3-d5/a2,-(sp)
        move.l  $4.w,a6
        jsr     _LVOForbid(a6)
        jsr     _LVODisable(a6)
        move.l  timerbase(pc),a6
        lea     eclock0(pc),a0
        jsr     _LVOReadEClock(a6)
        lea     efreq(pc),a0
        move.l  d0,(a0)
        movem.l (sp),d3-d5/a2
        move.l  d5,d7
        move.l  fastbuf(pc),a0
        move.l  chipbuf(pc),a1
        jsr     (a2)
        move.l  timerbase(pc),a6
        lea     eclock1(pc),a0
        jsr     _LVOReadEClock(a6)
        move.l  $4.w,a6
        jsr     _LVOEnable(a6)
        jsr     _LVOPermit(a6)
        movem.l (sp)+,d3-d5/a2
        move.l  eclock1+4(pc),d0
        sub.l   eclock0+4(pc),d0
        cmp.l   d4,d0
        bhs.b   .notbest
        move.l  d0,d4
.notbest:
        dbf     d3,.rep
        move.l  d4,d0
        movem.l (sp)+,d1-d7/a0-a6
        rts

; a3 name, d0 ticks, d5 iterations, d6 ops/iteration.
report:
        movem.l d0-d7/a0-a6,-(sp)
        fmove.l d0,fp0
        fmul.l  #40000000,fp0
        fdiv.l  efreq(pc),fp0
        fmove.l d5,fp1
        fmul.l  d6,fp1
        fdiv.x  fp1,fp0                 ; cycles per operation at 40 MHz
        fmul.l  #100,fp0
        fmove.l fp0,d1
        lea     args(pc),a0
        move.l  a3,(a0)+
        divul.l #100,d2:d1
        move.l  d1,(a0)+
        move.l  d2,(a0)+
        move.l  d0,(a0)+
        lea     line(pc),a0
        bsr     print
        movem.l (sp)+,d0-d7/a0-a6
        rts

print0: lea     args(pc),a1
print:  movem.l d0-d3/a0-a1/a6,-(sp)
        move.l  a0,d1
        lea     args(pc),a0
        move.l  a0,d2
        move.l  dosbase(pc),a6
        jsr     _LVOVPrintf(a6)
        movem.l (sp)+,d0-d3/a0-a1/a6
        rts

; ---------------------------------------------------------------- kernels
; In: d7 iterations, a0 fast buffer (128 KB), a1 chip buffer (32 KB).
; Register kernels repeat one instruction 16 times per iteration.
REP16   macro
        rept    16
        \1
        endr
        endm

k_add:  moveq   #3,d1
.l:     REP16   <add.l d1,d2>
        subq.l  #1,d7
        bne.b   .l
        rts
k_mulsw: move.l #$1234,d1
        move.l  #$5678,d2
.l:     REP16   <muls.w d1,d2>
        subq.l  #1,d7
        bne.b   .l
        rts
k_mulsl: move.l #$12345,d1
        move.l  #$6789,d2
.l:     REP16   <muls.l d1,d2>
        subq.l  #1,d7
        bne.b   .l
        rts
; Divides need a fresh dividend: report per (move + divide) pair.
k_divsw: move.w #1234,d1
        move.l  #1000000,d3
.l:     rept    8
        move.l  d3,d2
        divs.w  d1,d2
        endr
        subq.l  #1,d7
        bne.b   .l
        rts
k_divsl: move.l #1234,d1
        move.l  #100000000,d3
.l:     rept    8
        move.l  d3,d2
        divs.l  d1,d2
        endr
        subq.l  #1,d7
        bne.b   .l
        rts
; One projected coordinate, as in the original Project integer path.
k_proj_int:
        move.w  #1234,d1
        move.l  #1000000,d3
        move.w  #160,a5
.l:     rept    4
        move.l  d3,d2
        divs.w  d1,d2
        bvs.b   *+4
        add.w   a5,d2
        endr
        subq.l  #1,d7
        bne.b   .l
        rts
; One projected coordinate, as in project_fpu_040 (round-to-zero, clamp).
k_proj_fpu:
        fmove.l fpcr,-(sp)
        fmove.l #$10,fpcr
        move.w  #1234,d1
        move.l  #1000000,d3
        move.w  #160,a5
.l:     rept    4
        fmove.l d3,fp0
        fdiv.w  d1,fp0
        fmove.l fp0,d2
        cmp.l   #32767,d2
        bgt.b   *+12
        cmp.l   #-32768,d2
        blt.b   *+4
        add.w   a5,d2
        endr
        subq.l  #1,d7
        bne.b   .l
        fmove.l (sp)+,fpcr
        rts
k_fadd: fmove.l #1,fp1
        fmove.l #3,fp0
.l:     REP16   <fadd.x fp1,fp0>
        subq.l  #1,d7
        bne.b   .l
        rts
k_fmul: fmove.s #1.0000001,fp1
        fmove.l #3,fp0
.l:     REP16   <fmul.x fp1,fp0>
        subq.l  #1,d7
        bne.b   .l
        rts
k_fdiv: fmove.s #1.0000001,fp1
        fmove.l #3,fp0
.l:     REP16   <fdiv.x fp1,fp0>
        subq.l  #1,d7
        bne.b   .l
        rts
k_fsqrt: fmove.l #12345,fp1
.l:     REP16   <fsqrt.x fp1,fp0>
        subq.l  #1,d7
        bne.b   .l
        rts
k_bfextu: move.l #$12345678,d1
.l:     REP16   <bfextu d1{27:5},d2>
        subq.l  #1,d7
        bne.b   .l
        rts
k_bfins: moveq  #-1,d6
        moveq   #5,d3
        moveq   #9,d4
.l:     REP16   <bfins d6,(a0){d3:d4}>
        subq.l  #1,d7
        bne.b   .l
        rts
; Memory streams: 16 longword operations per inner iteration, whole buffer per outer.
k_fast_w:
        move.l  a0,a2
.o:     move.l  a2,a0
        move.w  #65536/64-1,d6
.l:     REP16   <move.l d1,(a0)+>
        dbf     d6,.l
        subq.l  #1,d7
        bne.b   .o
        rts
k_fast_r:
        move.l  a0,a2
.o:     move.l  a2,a0
        move.w  #65536/64-1,d6
.l:     REP16   <move.l (a0)+,d1>
        dbf     d6,.l
        subq.l  #1,d7
        bne.b   .o
        rts
k_fast_cmpm:
        move.l  a0,a2
.o:     move.l  a2,a0
        lea     65536(a2),a1
        move.w  #65536/64-1,d6
.l:     REP16   <cmpm.l (a0)+,(a1)+>
        dbf     d6,.l
        subq.l  #1,d7
        bne.b   .o
        rts
k_chip_w:
        move.l  a1,a2
.o:     move.l  a2,a1
        move.w  #CHIPSIZE/64-1,d6
.l:     REP16   <move.l d1,(a1)+>
        dbf     d6,.l
        subq.l  #1,d7
        bne.b   .o
        rts
k_chip_r:
        move.l  a1,a2
.o:     move.l  a2,a1
        move.w  #CHIPSIZE/64-1,d6
.l:     REP16   <move.l (a1)+,d1>
        dbf     d6,.l
        subq.l  #1,d7
        bne.b   .o
        rts
; Masked sprite merge, one word for one plane per operation, 40 words/row.
; Original tfx.020 inner loop ($4e57a), including per-word edge tests.
k_mask_old:
        move.l  a0,a2
        move.l  d7,-(sp)                ; iteration counter
        move.l  #$ffff0000,d7           ; first/last word masks
        moveq   #12,d6                  ; shift 16-4
        lea     8192(a2),a1             ; data
.o:     move.l  a2,a0
        lea     16384(a2),a3            ; destination
        moveq   #39,d1
        move.w  d1,d2
.w:     moveq   #0,d3
        move.w  (a0)+,d3
        moveq   #0,d4
        move.w  (a1)+,d4
        cmp.w   d1,d2
        bne.b   .nf
        swap    d7
        and.w   d7,d3
        swap    d7
.nf:    tst.w   d2
        bne.b   .nl
        and.w   d7,d3
.nl:    lsl.l   d6,d3
        lsl.l   d6,d4
        and.l   d3,d4
        not.l   d3
        move.l  (a3),d5
        and.l   d3,d5
        or.l    d4,d5
        move.l  d5,(a3)
        addq.l  #2,a3
        dbf     d2,.w
        lea     -80(a1),a1
        subq.l  #1,(sp)
        bne.b   .o
        addq.l  #4,sp
        rts
; Step-2 inner loop: precomputed shifted/edge-masked longword masks.
k_mask_new:
        move.l  a0,a2
        moveq   #12,d6
        lea     8192(a2),a1
        lea     32768(a2),a4            ; mask longs, nonzero
        move.l  a4,a5
        moveq   #39,d0
.fill:  move.l  #$000ffff0,(a5)+
        dbf     d0,.fill
.o:     move.l  a4,a5
        lea     16384(a2),a3
        moveq   #39,d2
.w:     move.l  (a5)+,d3
        beq.b   .skip
        move.w  (a1)+,d4
        lsl.l   d6,d4
        and.l   d3,d4
        not.l   d3
        and.l   (a3),d3
        or.l    d4,d3
        move.l  d3,(a3)
        addq.l  #2,a3
        dbf     d2,.w
        bra.b   .row
.skip:  addq.l  #2,a1
        addq.l  #2,a3
        dbf     d2,.w
.row:   lea     -80(a1),a1
        subq.l  #1,d7
        bne.b   .o
        rts

KENT    macro   ; name, kernel, iterations, ops per iteration
        dc.l    \1,\2,\3,\4
        endm
kernels:
        KENT    n_add,k_add,65536,16
        KENT    n_mulsw,k_mulsw,16384,16
        KENT    n_mulsl,k_mulsl,16384,16
        KENT    n_divsw,k_divsw,16384,8
        KENT    n_divsl,k_divsl,8192,8
        KENT    n_proj_int,k_proj_int,16384,4
        KENT    n_proj_fpu,k_proj_fpu,16384,4
        KENT    n_fadd,k_fadd,16384,16
        KENT    n_fmul,k_fmul,16384,16
        KENT    n_fdiv,k_fdiv,4096,16
        KENT    n_fsqrt,k_fsqrt,2048,16
        KENT    n_bfextu,k_bfextu,32768,16
        KENT    n_bfins,k_bfins,16384,16
        KENT    n_fast_w,k_fast_w,8,16384
        KENT    n_fast_r,k_fast_r,8,16384
        KENT    n_fast_cmpm,k_fast_cmpm,8,16384
        KENT    n_chip_w,k_chip_w,4,8192
        KENT    n_chip_r,k_chip_r,4,8192
        KENT    n_mask_old,k_mask_old,4096,40
        KENT    n_mask_new,k_mask_new,4096,40
        dc.l    0

n_add:      dc.b "add.l Dn,Dn",0
n_mulsw:    dc.b "muls.w",0
n_mulsl:    dc.b "muls.l",0
n_divsw:    dc.b "move.l+divs.w",0
n_divsl:    dc.b "move.l+divs.l",0
n_proj_int: dc.b "project coord, divs.w",0
n_proj_fpu: dc.b "project coord, fdiv",0
n_fadd:     dc.b "fadd.x",0
n_fmul:     dc.b "fmul.x",0
n_fdiv:     dc.b "fdiv.x",0
n_fsqrt:    dc.b "fsqrt.x",0
n_bfextu:   dc.b "bfextu Dn",0
n_bfins:    dc.b "bfins Dn,(An)",0
n_fast_w:   dc.b "fast move.l write",0
n_fast_r:   dc.b "fast move.l read",0
n_fast_cmpm: dc.b "fast cmpm.l",0
n_chip_w:   dc.b "chip move.l write",0
n_chip_r:   dc.b "chip move.l read",0
n_mask_old: dc.b "mask word, original",0
n_mask_new: dc.b "mask word, step 2",0
header:     dc.b "calib040: cycles per operation at 40 MHz (fewest of 3 runs)",10,0
line:       dc.b "%-24s %4ld.%02ld   (%ld E-clock ticks)",10,0
dosname:    dc.b "dos.library",0
timername:  dc.b "timer.device",0
        even
dosbase:    dc.l 0
timerbase:  dc.l 0
fastbuf:    dc.l 0
chipbuf:    dc.l 0
efreq:      dc.l 0
eclock0:    dc.l 0,0
eclock1:    dc.l 0,0
args:       dc.l 0,0,0,0
timereq:    ds.b 40
