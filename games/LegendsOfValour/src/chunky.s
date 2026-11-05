; W2: use Exec PUBLIC memory for only the 20,000-byte chunky buffer, on any CPU.
; Keep the game's pool allocator/free for a failed allocation. No other pool is changed.
_w2_install
		movem.l d0-a6,-(sp)
		move.l (_custom2,pc),d0
		btst #1,d0
		beq .done
		move.l (_custom1,pc),d0
		tst.l d0
		bne .done
		move.l (_hunks+4,pc),a0
		cmp.l #$48784e20,($22c6,a0)
		bne .bad
		cmp.l #$6100fe08,($22ca,a0)
		bne .bad
		cmp.l #$2eacdfc2,($2760,a0)
		bne .bad
		cmp.l #$4eba02e4,($2764,a0)
		bne .bad
		lea (_w2_alloc_resume+2,pc),a1
		lea ($22ce,a0),a2
		move.l a2,(a1)
		lea (_w2_free_resume+2,pc),a1
		lea ($2768,a0),a2
		move.l a2,(a1)
		lea (_w2_pool_alloc+2,pc),a1
		lea ($20d4,a0),a2
		move.l a2,(a1)
		lea (_w2_pool_free+2,pc),a1
		lea ($2a4a,a0),a2
		move.l a2,(a1)
	; PERF_RANGE h1:022c6 8 bit=1
		move.w #$4ef9,($22c6,a0)
		lea (_w2_alloc,pc),a1
		move.l a1,($22c8,a0)
		move.w #$4e71,($22cc,a0)
	; PERF_RANGE h1:02760 8 bit=1
		move.w #$4ef9,($2760,a0)
		lea (_w2_free,pc),a1
		move.l a1,($2762,a0)
		move.w #$4e71,($2766,a0)
		move.l (_resload,pc),a2
		jsr (resload_FlushCache,a2)
.done		movem.l (sp)+,d0-a6
		rts
.bad		lea (_w2_badcode,pc),a0
		bra _c2p_abort

; Preserve the game's argument slot; callable dispatchers also support VERIFY cycles.
_w2_alloc	pea 20000.w
		bsr _w2_allocate_dispatch
	IFD VERIFY
		movem.l d1-a6,-(sp)
		move.l (_custom5,pc),d1
		btst #3,d1
		beq .nocycle
		move.l d0,-(sp)
		bsr _w2_free_dispatch
		addq.l #4,sp
		move.l (_w2_owned,pc),d1
		tst.l d1
		bne _w2_verify_bad
		movem.l (sp)+,d1-a6
		bsr _w2_allocate_dispatch
		lea (_w2_cycles,pc),a0
		addq.l #1,(a0)
		bra _w2_alloc_resume
.nocycle	movem.l (sp)+,d1-a6
	ENDC
_w2_alloc_resume dc.w $4ef9
		dc.l 0

; Argument size at 4(SP), exactly as for the game's allocator.
_w2_allocate_dispatch
		movem.l d1-a6,-(sp)
	IFD VERIFY
		move.l (_custom5,pc),d0
		btst #2,d0		;force failure of the PUBLIC attempt only
		bne .failed
	ENDC
		move.l #20000,d0
		moveq #MEMF_PUBLIC,d1
		move.l 4.w,a6
		jsr (_LVOAllocMem,a6)
		lea (_w2_owned,pc),a0
		move.l d0,(a0)
	IFD VERIFY
		move.l d0,a1
		jsr (_LVOTypeOfMem,a6)
		lea (_w2_memflags,pc),a0
		move.l d0,(a0)
		move.l (_w2_owned,pc),d0
	ENDC
		tst.l d0
		beq .failed
		movem.l (sp)+,d1-a6
		rts
.failed		movem.l (sp)+,d1-a6
		bra _w2_pool_alloc

_w2_free	move.l (-8254,a4),(sp)
		bsr _w2_free_dispatch
_w2_free_resume dc.w $4ef9
		dc.l 0

; Argument pointer at 4(SP). Only an allocation we own uses FreeMem.
_w2_free_dispatch
		movem.l d0-a6,-(sp)
		move.l (64,sp),a1
		lea (_w2_owned,pc),a0
		cmp.l (a0),a1
		bne .pool
		move.l a1,d0
		beq .pool
		clr.l (a0)
		move.l #20000,d0
		move.l 4.w,a6
		jsr (_LVOFreeMem,a6)
		movem.l (sp)+,d0-a6
		rts
.pool		movem.l (sp)+,d0-a6
		bra _w2_pool_free
_w2_pool_alloc dc.w $4ef9
		dc.l 0
_w2_pool_free dc.w $4ef9
		dc.l 0
		CNOP 0,4
_w2_owned	dc.l 0
_w2_badcode	dc.b "W2: unexpected AMIGA2 allocation/free entry",0
		EVEN
	IFD VERIFY
_w2_verify_bad	lea (_w2_badcycle,pc),a0
		bra _c2p_abort
_w2_badcycle	dc.b "W2: allocation still owned after free",0
		EVEN
		CNOP 0,4
_w2_memflags	dc.l 0
_w2_cycles	dc.l 0
	ENDC
