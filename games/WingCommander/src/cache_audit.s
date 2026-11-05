; VERIFY-only terminating audit, adapted from Hard Drivin's cache audit.
; Ordinary builds never include this code. Original SetCPU executes first.
; Both follow-up API queries have zero change masks. All targets are 020+.
cache_audit:
        jsr     96(a2)
        moveq   #0,d0
        moveq   #0,d1
        jsr     96(a2)
        move.l  d0,d2
        moveq   #0,d0
        moveq   #0,d1
        jsr     16(a2)
        move.l  d0,d4
        movea.l 4.w,a6
        lea     .read_cacr(pc),a5
        jsr     -30(a6)
        move.l  d0,-(sp)
        move.l  d4,-(sp)
        move.l  d2,-(sp)
        move.l  slave+$1ddc(pc),-(sp)
        lea     .message(pc),a0
        jsr     136(a2)
        lea     16(sp),sp
        clr.l   -(sp)
        jmp     4(a2)
.read_cacr:
        movec   cacr,d0
        rte
.message:
        dc.b    "WC_CACHE attn=%08lx setup=%08lx cache_api=%08lx cacr=%08lx",0
        cnop    0,4
