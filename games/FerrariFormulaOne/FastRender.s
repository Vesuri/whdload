; FR3 (FASTRAM_PLAN.md): Fast RAM shadows, source mirrors, copy point and
; publication. 68020+ fine payload, assembled only with FF1_FAST_RENDER.
; FR4 adds the blit redirection at the native sites (see below). FR5 runs
; a prefix of the draw stages redirected into the back shadow before the
; field wait, and publishes the rows they wrote after it (see FR5 below).
;
; Install (every driving entry, from the barrier) qualifies the CPU (030/040/
; 060) and the Chip layout. The first draw then makes one MEMF_FAST allocation
; for both bank shadows and the whole game graphics region and seeds them
; from Chip.
; Any failure selects today's path.
; Every lifecycle reset (loop exit, unload, rollback) releases the block
; before the payload's zero-initialized state is cleared, so the menus never
; see the allocation.
;
; Mirror table: entries 0 and 1 are the two banks, three planes of 10,320
; bytes each, as in the native bank table; the rest cover the game graphics
; from $cd30 up to bank 1 (FR4: driving draws sprites and rear-view mirror
; images from all of it, far beyond the FR1 census), padded to 16 bytes. The
; block is about 310 KiB, so Fast render builds reserve 256 KiB more ExpMem. The WHDLoad Kickstart 1.3 environment makes
; their Chip addresses fixed; the bank table and the live Chip hunk 46 anchor
; that layout, and a different layout selects today's path.
; Fast address = Chip address + delta; each mirror keeps the Chip address
; modulo 16.

FRS_INSTALLS equ 4
FRS_ACTIVE equ 8
FRS_REJECT_CPU equ 12
FRS_REJECT_LAYOUT equ 16
FRS_ALLOC_FAIL equ 20
FRS_SEEDS equ 24
FRS_RELEASES equ 28
FRS_PUBLISHES equ 32
FRS_FREE_BEFORE equ 36
FRS_LARGEST_BEFORE equ 40
FRS_MIN_FREE_AFTER equ 44
FRS_BLOCK_BYTES equ 48

FR_BANK_BYTES equ 3*10320
FR_PLANE_STRIDE equ 10320
FR_ROW_BYTES equ 48
FR_COPY_ROWS equ 200
FR_ROWS equ FR_BANK_BYTES/FR_ROW_BYTES   ; 645 rows of 48 bytes per bank
FR_ROWS_PAD equ FR_ROWS+1

; FR5 stages in the prefix: 1 = FR5a (clear $6b050 and background $6b950).
; The FULL diagnostic redirects every stage after the wait instead.
 IFD FF1_FAST_RENDER_FULL
FR_STAGES equ 0
 ELSE
FR_STAGES equ 1
 ENDC

FR5S_PREFIXES equ 4         ; prefix runs
FR5S_PUBLISHED equ 8        ; rows copied to Chip
FR5S_REFRESHED equ 12       ; rows read from Chip before a partial access
FR5S_FILLED equ 16          ; rows written whole by a CPU fill
FR5S_LONGS equ 4

FF1FastRenderInstall:
 movem.l d0-d1/a0-a1/a3,-(sp)
 move.w ccr,-(sp)
 lea FF1FastRenderStats(pc),a3
 addq.l #1,FRS_INSTALLS(a3)
 tst.w FF1FastRenderControl(pc)
 beq.w .done
 tst.l FF1FastRenderBlock(pc)
 bne.w .done
 lea start(pc),a0
 suba.l #FF1_HOST_CODE_SIZE,a0
 move.l FF1_HOST_ATTN(a0),d0
 andi.l #$8c,d0             ; AFF_68030 | AFF_68040 | AFF_68060
 bne.b .cpu
 addq.l #1,FRS_REJECT_CPU(a3)
 bra.w .done
.cpu:
 ; Layout anchors: the native bank table and the live Chip hunk 46.
 lea $66c92,a0
 lea FF1FastRenderBanks(pc),a1
 moveq #2*4-1,d1            ; two entries of three planes and a zero long
.bank:
 move.l (a0)+,d0
 cmp.l (a1)+,d0
 bne.w .layout
 dbf d1,.bank
 move.l public_table(pc),a0
 move.l 46*4(a0),d0
 lsl.l #2,d0
 addq.l #4,d0
 cmpi.l #$18d80,d0
 bne.w .layout
 lea FF1FastRenderPending(pc),a0
 move.w #1,(a0)             ; allocate and seed at the first draw
 bsr.w FF1FastRenderInstallSites
 bra.b .done
.layout:
 addq.l #1,FRS_REJECT_LAYOUT(a3)
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d1/a0-a1/a3
 rts

; First draw of an entry. The race-start loader buffers are gone by now.
; One MEMF_FAST block, all or nothing; failure keeps today's path.
FF1FastRenderAllocate:
 movem.l d0-d4/a0-a3/a6,-(sp)
 lea FF1FastRenderStats(pc),a3
 lea FF1FastRenderPending(pc),a0
 clr.w (a0)
 ; Size the block: every mirror keeps its Chip address modulo 16.
 lea FF1FastRenderMirrors(pc),a0
 moveq #16,d2               ; alignment slack
.size:
 move.l (a0)+,d0
 bmi.b .sized
 move.l (a0)+,d1
 sub.l d0,d1
 addi.l #31,d1
 andi.w #-16,d1
 add.l d1,d2
 bra.b .size
.sized:
 move.l d2,FRS_BLOCK_BYTES(a3)
 move.l $4.w,a6
 moveq #4,d1                ; MEMF_FAST
 jsr -216(a6)               ; AvailMem
 move.l d0,FRS_FREE_BEFORE(a3)
 moveq #4,d1
 bset #17,d1                ; MEMF_FAST | MEMF_LARGEST (no pointer-like immediate)
 jsr -216(a6)
 move.l d0,FRS_LARGEST_BEFORE(a3)
 move.l d2,d0
 moveq #5,d1                ; MEMF_PUBLIC | MEMF_FAST
 jsr -198(a6)               ; AllocMem
 tst.l d0
 bne.b .owned
 addq.l #1,FRS_ALLOC_FAIL(a3)
 bra.w .done
.owned:
 lea FF1FastRenderBlock(pc),a0
 move.l d0,(a0)+
 move.l d2,(a0)
 moveq #4,d1
 jsr -216(a6)
 cmp.l FRS_MIN_FREE_AFTER(a3),d0
 bhs.b .deltas
 move.l d0,FRS_MIN_FREE_AFTER(a3)
.deltas:
 ; delta = aligned cursor + (Chip & 15) - Chip
 move.l FF1FastRenderBlock(pc),d3
 addi.l #15,d3
 andi.w #-16,d3
 lea FF1FastRenderMirrors(pc),a0
 lea FF1FastRenderDelta(pc),a1
.place:
 move.l (a0)+,d0
 bmi.b .placed
 move.l (a0)+,d1
 move.l d0,d4
 andi.l #15,d4
 add.l d3,d4
 sub.l d0,d4
 move.l d4,(a1)+
 sub.l d0,d1
 addi.l #31,d1
 andi.w #-16,d1
 add.l d1,d3
 bra.b .place
.placed:
 ; Seed every mirror from Chip once the blitter is idle.
 tst.b $dff002
.blit:
 btst #6,$dff002
 bne.b .blit
 lea FF1FastRenderMirrors(pc),a2
 lea FF1FastRenderDelta(pc),a1
.range:
 move.l (a2)+,d0
 bmi.b .seeded
 move.l (a2)+,d1
 sub.l d0,d1
 lsr.l #2,d1
 subq.l #1,d1
 move.l d0,a0
 add.l (a1)+,d0
 move.l a1,-(sp)
 move.l d0,a1
.long:
 move.l (a0)+,(a1)+
 dbf d1,.long
 move.l (sp)+,a1
 bra.b .range
.seeded:
 lea FF1FastRenderActive(pc),a0
 move.w #1,(a0)
 addq.l #1,FRS_ACTIVE(a3)
 addq.l #1,FRS_SEEDS(a3)
.done:
 movem.l (sp)+,d0-d4/a0-a3/a6
 rts

; Lifecycle reset: release before the payload state is zeroed.
FF1FastRenderRelease:
 movem.l d0-d1/a0-a1/a6,-(sp)
 move.w ccr,-(sp)
 lea FF1FastRenderBlock(pc),a0
 move.l (a0),d0
 beq.b .done
 move.l d0,a1
 move.l 4(a0),d0
 clr.l (a0)+
 clr.l (a0)
 lea FF1FastRenderActive(pc),a0
 clr.l (a0)                 ; Active and Pending
 bsr.w FF1FastRenderRedirectOff
 move.l $4.w,a6
 jsr -210(a6)               ; FreeMem
 lea FF1FastRenderStats(pc),a0
 addq.l #1,FRS_RELEASES(a0)
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d1/a0-a1/a6
 rts

; B8Draw, after OwnBlitter and the H3 road preparation, before the field
; wait: allocate and seed on the first draw, then run the prefix stages
; redirected into the back shadow. A6 is B8Draw's frame.
;
; FR5 row tracking. The shadows are exact only where the prefix itself drew:
; the native stages after the copy point draw into Chip, so every other
; shadow row may be stale. Each prefix therefore starts with every bank row
; untrusted (0). A redirected access to an untrusted row first reads that
; row from Chip (1, fresh), unless a CPU fill writes the whole row; a write
; marks the row dirty (2). The publication copies exactly the dirty rows to
; Chip. Chip holds what the native stages would see at the same point:
; nothing draws between the prefix and the publication, and the blitter is
; idle before the first read.
FF1FastRenderPrefix:
 move.w ccr,-(sp)
 tst.w FF1FastRenderPending(pc)
 beq.b .stages
 bsr.w FF1FastRenderAllocate
.stages:
 IFNE FR_STAGES
 tst.w FF1FastRenderActive(pc)
 beq.b .done
 tst.w FF1FastRenderStages(pc)
 beq.b .done
 movem.l d0-d1/a0-a1,-(sp)
 lea FF1FastRenderRows(pc),a0
 move.w #(2*FR_ROWS_PAD)/2-1,d0
.clear:
 clr.w (a0)+
 dbf d0,.clear
 tst.b $dff002
.blit:
 btst #6,$dff002
 bne.b .blit
 bsr.w FF1FastRenderRefresh
 bsr.w FF1FastRenderRedirectOn
 lea FF1FastRenderTrack(pc),a0
 move.w #1,(a0)
 lea FF1FastRenderStageStats(pc),a0
 addq.l #1,FR5S_PREFIXES(a0)
 ; FR5a: the native clear and background, as B8Draw calls them.
 jsr $6b050.l
 move.w -$30(a6),d0
 ext.l d0
 move.l d0,-(sp)
 jsr $6b950.l
 addq.l #4,sp
 bsr.w FF1FastRenderRedirectOff
 lea FF1FastRenderStaged(pc),a0
 move.w #1,(a0)
 movem.l (sp)+,d0-d1/a0-a1
 ENDC
.done:
 move.w (sp)+,ccr
 rts

; B8Draw, after the field wait, before the first native stage: copy the
; rows the prefix wrote from the shadows to the Chip banks. Returns D0 = 1
; when the prefix ran the FR5a stages (B8Draw then skips them), else 0.
FF1FastRenderPublish:
 bsr.b FRPublishWork
 moveq #0,d0
 tst.w FF1FastRenderStaged(pc)
 beq.b .out
 move.l a0,-(sp)
 bsr.w FRPublishRows
 lea FF1FastRenderStaged(pc),a0
 clr.w (a0)
 move.l (sp)+,a0
 moveq #1,d0
.out:
 rts
FRPublishWork:
 move.w ccr,-(sp)
 tst.w FF1FastRenderActive(pc)
 beq.b .done
 movem.l d0-d1/a0-a2,-(sp)
 lea FF1FastRenderStats(pc),a0
 addq.l #1,FRS_PUBLISHES(a0)
 IFD FF1_FAST_RENDER_ROUNDTRIP
 ; Diagnostic: refresh the back shadow from Chip, then publish the whole
 ; displayed region. The Chip bank must end up unchanged.
 move.l $226ae,a0
 move.l (a0),a0
 bsr.w FF1FastRenderMap
 tst.l d0
 bne.b .out
 move.l a0,a1
 move.l $226ae,a0
 move.l (a0),a0
 move.w #FR_BANK_BYTES/4-1,d1
.read:
 move.l (a0)+,(a1)+
 dbf d1,.read
 move.l $226ae,a1
 move.l (a1),a1
 move.l a1,a0
 bsr.w FF1FastRenderMap
 bsr.w FF1FastRenderCopyBank
.out:
 ENDC
 IFD FF1_FAST_RENDER_FULL
 ; Diagnostic: every stage runs redirected into the shadows, and
 ; FF1FastRenderFinish publishes the complete back bank.
 bsr.w FF1FastRenderRefresh
 bsr.w FF1FastRenderRedirectOn
 ENDC
 movem.l (sp)+,d0-d1/a0-a2
.done:
 move.w (sp)+,ccr
 rts

; A0 = Chip address. Returns D0 = 0 and A0 = Fast mirror address, or D0 = -1
; and A0 unchanged when no mirror covers it. Other registers preserved.
FF1FastRenderMap:
 movem.l d1/a1-a2,-(sp)
 tst.w FF1FastRenderActive(pc)
 beq.b .miss
 lea FF1FastRenderMirrors(pc),a1
 lea FF1FastRenderDelta(pc),a2
.next:
 move.l (a1)+,d0
 bmi.b .miss
 move.l (a1)+,d1
 cmpa.l d0,a0
 blo.b .skip
 cmpa.l d1,a0
 bhs.b .skip
 adda.l (a2),a0
 moveq #0,d0
 bra.b .out
.skip:
 addq.l #4,a2
 bra.b .next
.miss:
 moveq #-1,d0
.out:
 movem.l (sp)+,d1/a1-a2
 rts

; A0 = Fast shadow bank, A1 = Chip bank. Copies the displayed region, bytes
; 4..43 of rows 0..199 in each of the three planes (24,000 bytes).
FF1FastRenderCopyBank:
 movem.l d0-d1/a0-a1,-(sp)
 addq.l #4,a0
 addq.l #4,a1
 moveq #3-1,d1
.plane:
 move.w #FR_COPY_ROWS-1,d0
.row:
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 lea FR_ROW_BYTES-40(a0),a0
 lea FR_ROW_BYTES-40(a1),a1
 dbf d0,.row
 lea FR_PLANE_STRIDE-FR_COPY_ROWS*FR_ROW_BYTES(a0),a0
 lea FR_PLANE_STRIDE-FR_COPY_ROWS*FR_ROW_BYTES(a1),a1
 dbf d1,.plane
 movem.l (sp)+,d0-d1/a0-a1
 rts

; ---------------------------------------------------------------------------
; FR4: blit redirection at the native sites (FASTRAM_PLAN.md FR4).
;
; Every driving entry that qualifies patches the eleven FR1 blit sites and
; the instruments' WritePixel call in the public race copy, inside the
; lifecycle patch transaction, so the ledger restores every word on exit:
; - the three base-register routines ($24ae0 bitmap, $6ac4a road lines,
;   $32d50 cars) load their custom-chip base from FF1FastRenderRegs;
; - the two absolute-operand routines ($6ba18 cockpit, the $6c310 cockpit
;   fill) write the Fast register image permanently;
; - each BLTSIZE write calls FF1FastRenderSize (or FRSizeAbs), and each
;   BLTBDAT write in the line routine calls FastRenderBDAT when redirected.
; FF1FastRenderRegs is the custom chip ($dff000) unless a redirected stage
; is running, so the base-register sites write the hardware directly and the
; absolute-operand sites flush their own registers before BLTSIZE. While
; redirected, BLTSIZE runs the FR2 software blitter on the Fast copies:
; every enabled channel's whole span is translated through the mirror table
; (destinations into any mirror of the region), and any pointer outside
; it, or an unsupported blit form, takes the production fault exit. The image
; keeps Chip addresses between blits, so a continuation BLTSIZE translates
; again. WaitBlit and OwnBlitter keep their native calls; with every blit of
; a redirected stage synchronous they return at once.
; The CPU writers of redirected stages (H5 bitmap, H10 clear, H11 clock, H13
; gauge strips, H4 demo text, the H9 fill scan) translate their pointers with
; FF1FastRenderTarget.
; FR5a runs the clear and background in the prefix (FF1FastRenderPrefix);
; every later stage still writes the hardware.
; FF1_FAST_RENDER_FULL is a diagnostic that redirects the whole draw and
; publishes the complete back bank at the end of B8Draw.

FRSITE_24C18 equ 0          ; $24ae0 BLTSIZE at $24c14
FRSITE_24DB8 equ 1          ; $24ae0 BLTSIZE at $24db4
FRSITE_6AD8A equ 2          ; road line, first plane
FRSITE_6ADDE equ 3          ; road line, second plane
FRSITE_FILL equ 4           ; FF1RenderFill (H9)
FRSITE_32DFA equ 5          ; car mask
FRSITE_32E6C equ 6          ; car colour plane
FRSITE_32F02 equ 7          ; car cookie-cut
FRSITE_6C55C equ 8          ; cockpit rectangle fill
FRSITE_6BBEC equ 9          ; cockpit/gauge composition
FRSITE_PIXEL equ 10         ; WritePixel, counted per plane written

FR4S_SOFT equ 4             ; 16 longs: software blits per site
FR4S_HARD equ 68            ; 16 longs: hardware blits per patched site
FR4S_REDIRECTS equ 132
FR4S_FAULTS equ 136
FR4S_FAULT_REASON equ 140   ; 1 pointer, 2 blit form, 3 CPU target, 4 native fallback, 5 RastPort,
                            ; 6 prefix write outside the banks, 7 untracked prefix CPU write
FR4S_FAULT_SITE equ 144
FR4S_SITE_INSTALLS equ 148
FR4S_LONGS equ 37

; Mirror table entries a destination may write. The drawing writes scratch
; and the rear-view mirror bitmaps all through the game graphics (FR4
; census), so every mirror of the region is writable.
FR_WRITABLE equ (1<<FR_MIRRORS)-1

; Barrier, qualified entry: check every site against the original game,
; then patch. A signature mismatch takes the production fault exit.
FF1FastRenderInstallSites:
 move.l a0,-(sp)
 cmpi.l #$247c00df,$24b0e
 bne.w .bad
 cmpi.w #$f000,$24b12
 bne.w .bad
 cmpi.l #$35400058,$24c14
 bne.w .bad
 cmpi.l #$04440001,$24c18
 bne.w .bad
 cmpi.l #$35400058,$24db4
 bne.w .bad
 cmpi.l #$06450001,$24db8
 bne.w .bad
 cmpi.l #$207c00df,$6acce
 bne.w .bad
 cmpi.w #$f000,$6acd2
 bne.w .bad
 cmpi.l #$31400072,$6ad6c
 bne.w .bad
 cmpi.l #$317c8000,$6ad70
 bne.w .bad
 cmpi.w #$0074,$6ad74
 bne.w .bad
 cmpi.l #$31440058,$6ad86
 bne.w .bad
 cmpi.l #$4a790006,$6ad8a
 bne.w .bad
 cmpi.w #$ade4,$6ad8e
 bne.w .bad
 cmpi.l #$31400072,$6adc0
 bne.w .bad
 cmpi.l #$317c8000,$6adc4
 bne.w .bad
 cmpi.w #$0074,$6adc8
 bne.w .bad
 cmpi.l #$31430062,$6add6
 bne.w .bad
 cmpi.l #$31440058,$6adda
 bne.w .bad
 cmpi.l #$227c00df,$32db4
 bne.w .bad
 cmpi.w #$f000,$32db8
 bne.w .bad
 cmpi.l #$33400058,$32df6
 bne.w .bad
 cmpi.w #$3840,$32dfa
 bne.w .bad
 cmpi.l #$334c0058,$32e68
 bne.w .bad
 cmpi.l #$4eb90002,$32e6c
 bne.w .bad
 cmpi.w #$a130,$32e70
 bne.w .bad
 cmpi.l #$33400058,$32efe
 bne.w .bad
 cmpi.l #$d6fc0001,$32f02
 bne.w .bad
 cmpi.l #$33c000df,$6bbe6
 bne.w .bad
 cmpi.w #$f058,$6bbea
 bne.w .bad
 cmpi.l #$33fc0dcc,$6c554
 bne.w .bad
 cmpi.l #$00dff058,$6c558
 bne.w .bad
 cmpi.l #$4eb90002,$66a46
 bne.w .bad
 cmpi.w #$a1b0,$66a4a
 bne.w .bad
 cmpi.l #$00dff046,$6baaa
 bne.w .bad
 cmpi.l #$00dff044,$6bab6
 bne.w .bad
 cmpi.l #$00dff044,$6bac0
 bne.w .bad
 cmpi.l #$00dff064,$6bad4
 bne.w .bad
 cmpi.l #$00dff062,$6bae4
 bne.w .bad
 cmpi.l #$00dff040,$6bb02
 bne.w .bad
 cmpi.l #$00dff042,$6bb0a
 bne.w .bad
 cmpi.l #$00dff066,$6bb1e
 bne.w .bad
 cmpi.l #$00dff060,$6bb24
 bne.w .bad
 cmpi.l #$00dff048,$6bb76
 bne.w .bad
 cmpi.l #$00dff054,$6bb96
 bne.w .bad
 cmpi.l #$00dff04c,$6bbb4
 bne.w .bad
 cmpi.l #$00dff050,$6bbce
 bne.w .bad
 cmpi.l #$00dff042,$6c4fe
 bne.w .bad
 cmpi.l #$00dff066,$6c506
 bne.w .bad
 cmpi.l #$00dff040,$6c526
 bne.w .bad
 cmpi.l #$00dff040,$6c530
 bne.w .bad
 cmpi.l #$00dff054,$6c550
 bne.w .bad
 ; Base registers.
 move.w #$4eb9,$24b0e
 lea FRTBaseA2(pc),a0
 move.l a0,$24b10
 move.w #$4eb9,$6acce
 lea FRTBaseA0(pc),a0
 move.l a0,$6acd0
 move.w #$4eb9,$32db4
 lea FRTBaseA1(pc),a0
 move.l a0,$32db6
 ; BLTSIZE writes, each with its displaced following instruction.
 move.w #$4eb9,$24c14
 lea FRT24c14(pc),a0
 move.l a0,$24c16
 move.w #$4e71,$24c1a
 move.w #$4eb9,$24db4
 lea FRT24db4(pc),a0
 move.l a0,$24db6
 move.w #$4e71,$24dba
 move.w #$4eb9,$6ad86
 lea FRT6ad86(pc),a0
 move.l a0,$6ad88
 move.l #$4e714e71,$6ad8c
 move.w #$4eb9,$6add6       ; $6adde stays: a branch target
 lea FRT6add6(pc),a0
 move.l a0,$6add8
 move.w #$4e71,$6addc
 move.w #$4eb9,$32df6
 lea FRT32df6(pc),a0
 move.l a0,$32df8
 move.w #$4eb9,$32e68
 lea FRT32e68(pc),a0
 move.l a0,$32e6a
 move.l #$4e714e71,$32e6e
 move.w #$4eb9,$32efe
 lea FRT32efe(pc),a0
 move.l a0,$32f00
 move.w #$4e71,$32f04
 move.w #$4eb9,$6bbe6
 lea FRT6bbe6(pc),a0
 move.l a0,$6bbe8
 move.w #$4eb9,$6c554
 lea FRT6c554(pc),a0
 move.l a0,$6c556
 move.w #$4e71,$6c55a
 ; BLTBDAT writes of the line routine.
 move.w #$4eb9,$6ad6c
 lea FRTBdatA0(pc),a0
 move.l a0,$6ad6e
 move.l #$4e714e71,$6ad72
 move.w #$4eb9,$6adc0
 move.l a0,$6adc2
 move.l #$4e714e71,$6adc6
 ; The instruments' WritePixel call.
 lea FF1FastRenderWritePixel(pc),a0
 move.l a0,$66a48
 ; Absolute operands of $6ba18 and the $6c310 cockpit fill.
 lea FF1FastRenderImage+$06(pc),a0
 move.l a0,$6baaa
 lea FF1FastRenderImage+$04(pc),a0
 move.l a0,$6bab6
 lea FF1FastRenderImage+$04(pc),a0
 move.l a0,$6bac0
 lea FF1FastRenderImage+$24(pc),a0
 move.l a0,$6bad4
 lea FF1FastRenderImage+$22(pc),a0
 move.l a0,$6bae4
 lea FF1FastRenderImage+$00(pc),a0
 move.l a0,$6bb02
 lea FF1FastRenderImage+$02(pc),a0
 move.l a0,$6bb0a
 lea FF1FastRenderImage+$26(pc),a0
 move.l a0,$6bb1e
 lea FF1FastRenderImage+$20(pc),a0
 move.l a0,$6bb24
 lea FF1FastRenderImage+$08(pc),a0
 move.l a0,$6bb76
 lea FF1FastRenderImage+$14(pc),a0
 move.l a0,$6bb96
 lea FF1FastRenderImage+$0c(pc),a0
 move.l a0,$6bbb4
 lea FF1FastRenderImage+$10(pc),a0
 move.l a0,$6bbce
 lea FF1FastRenderImage+$02(pc),a0
 move.l a0,$6c4fe
 lea FF1FastRenderImage+$26(pc),a0
 move.l a0,$6c506
 lea FF1FastRenderImage+$00(pc),a0
 move.l a0,$6c526
 lea FF1FastRenderImage+$00(pc),a0
 move.l a0,$6c530
 lea FF1FastRenderImage+$14(pc),a0
 move.l a0,$6c550
 lea FF1FastRenderSiteStats(pc),a0
 addq.l #1,FR4S_SITE_INSTALLS(a0)
 move.l (sp)+,a0
 rts
.bad:
 bra.l FF1ProductionFault

; Patched native code. Each thunk replaces its instructions exactly,
; including the condition codes the following native instruction reads.
; No patched span except its first word is a native branch target.
FRTBaseA0:                  ; movea.l #$dff000,a0
 movea.l FF1FastRenderRegs(pc),a0
 rts
FRTBaseA1:                  ; movea.l #$dff000,a1
 movea.l FF1FastRenderRegs(pc),a1
 rts
FRTBaseA2:                  ; movea.l #$dff000,a2
 movea.l FF1FastRenderRegs(pc),a2
 rts
FRT24c14:                   ; move.w d0,88(a2); subi.w #1,d4
 movem.l d1/a0,-(sp)
 move.l a2,a0
 moveq #FRSITE_24C18,d1
 bsr.w FF1FastRenderSize
 movem.l (sp)+,d1/a0
 subq.w #1,d4
 rts
FRT24db4:                   ; move.w d0,88(a2); addi.w #1,d5
 movem.l d1/a0,-(sp)
 move.l a2,a0
 moveq #FRSITE_24DB8,d1
 bsr.w FF1FastRenderSize
 movem.l (sp)+,d1/a0
 addq.w #1,d5
 rts
FRT6ad86:                   ; move.w d4,88(a0); tst.w $6ade4
 movem.l d0-d1,-(sp)
 move.w d4,d0
 moveq #FRSITE_6AD8A,d1
 bsr.w FF1FastRenderSize
 movem.l (sp)+,d0-d1
 tst.w $6ade4
 rts
FRT6add6:                   ; move.w d3,98(a0); move.w d4,88(a0)
 move.w d3,$62(a0)
 movem.l d0-d1,-(sp)
 move.w d4,d0
 moveq #FRSITE_6ADDE,d1
 bsr.w FF1FastRenderSize
 movem.l (sp)+,d0-d1
 rts
FRT32df6:                   ; move.w d0,88(a1); movea.w d0,a4
 movem.l d1/a0,-(sp)
 move.l a1,a0
 moveq #FRSITE_32DFA,d1
 bsr.w FF1FastRenderSize
 movem.l (sp)+,d1/a0
 movea.w d0,a4
 rts
FRT32e68:                   ; move.w a4,88(a1); jsr $2a130
 movem.l d0-d1/a0,-(sp)
 move.w a4,d0
 move.l a1,a0
 moveq #FRSITE_32E6C,d1
 bsr.w FF1FastRenderSize
 movem.l (sp)+,d0-d1/a0
 jmp $2a130
FRT32efe:                   ; move.w d0,88(a1); adda.w #1,a3
 movem.l d1/a0,-(sp)
 move.l a1,a0
 moveq #FRSITE_32F02,d1
 bsr.w FF1FastRenderSize
 movem.l (sp)+,d1/a0
 addq.w #1,a3
 rts
FRT6bbe6:                   ; move.w d0,$dff058
 movem.l d1/a0-a1,-(sp)
 lea FRFlush6ba18(pc),a1
 moveq #FRSITE_6BBEC,d1
 bsr.w FRSizeAbs
 movem.l (sp)+,d1/a0-a1
 rts
FRT6c554:                   ; move.w #$dcc,$dff058
 movem.l d0-d1/a0-a1,-(sp)
 move.w #$dcc,d0
 lea FRFlush6c310(pc),a1
 moveq #FRSITE_6C55C,d1
 bsr.w FRSizeAbs
 movem.l (sp)+,d0-d1/a0-a1
 rts
FRTBdatA0:                  ; move.w d0,114(a0); move.w #$8000,116(a0)
 cmpa.l #$dff000,a0
 bne.b .soft
 move.w d0,$72(a0)
 bra.b .adat
.soft:
 lea $40(a0),a0             ; base -> image
 bsr.l FastRenderBDAT
 lea -$40(a0),a0
.adat:
 move.w #$8000,$74(a0)
 rts

; Registers an absolute-operand routine writes (bit 8: a pointer longword),
; flushed from the image to the custom chip before its hardware BLTSIZE.
FRFlush6ba18: dc.w $46,$44,$64,$62,$40,$42,$66,$60,$148,$154,$14c,$150,-1
FRFlush6c310: dc.w $42,$66,$40,$154,-1
; Pointer and modulo offsets of channels A, B, C and D in the image.
FRChanTab: dc.w $10,$24,$0c,$22,$08,$20,$14,$26

; Absolute-operand routines. A1 = flush list, D0.w = BLTSIZE, D1 = site.
FRSizeAbs:
 lea FF1FastRenderImage-$40(pc),a0   ; register base of the image
 tst.w FF1FastRenderRedirect(pc)
 bne.b FF1FastRenderSize
 movem.l d2/a2,-(sp)
 lea $dff000,a2
.flush:
 move.w (a1)+,d2
 bmi.b .go
 bclr #8,d2
 bne.b .long
 move.w (a0,d2.w),(a2,d2.w)
 bra.b .flush
.long:
 move.l (a0,d2.w),(a2,d2.w)
 bra.b .flush
.go:
 move.l a2,a0
 movem.l (sp)+,d2/a2
 ; fall through: the custom-chip base starts the hardware blit

; A0 = register base: the custom chip, or the image - $40 (native code
; addresses BLTCON0 as $40 from its base). D0.w = BLTSIZE, D1 = site.
; All registers are preserved.
FF1FastRenderSize:
 cmpa.l #$dff000,a0
 bne.b .soft
 move.w d0,$58(a0)
 movem.l d1/a0,-(sp)
 lea FF1FastRenderSiteStats+FR4S_HARD(pc),a0
 lsl.w #2,d1
 addq.l #1,(a0,d1.w)
 movem.l (sp)+,d1/a0
 rts
.soft:
 movem.l d0-d7/a0-a6,-(sp)
 lea $40(a0),a0             ; base -> image
 move.w d0,FRB_SIZE(a0)
 lea FF1FastRenderSite(pc),a1
 move.w d1,(a1)
 lea FF1FastRenderSiteStats+FR4S_SOFT(pc),a1
 lsl.w #2,d1
 addq.l #1,(a1,d1.w)
 bsr.w FRTranslate
 bne.w FF1FastRenderFault
 bsr.l FastRenderBlit
 tst.l d0
 beq.b .done
 moveq #2,d0
 bra.w FF1FastRenderFault
.done:
 bsr.w FRUntranslate
 movem.l (sp)+,d0-d7/a0-a6
 rts

; A0 = image with BLTSIZE. Translates each enabled channel pointer to its
; Fast copy after checking that the channel's complete span lies in one
; mirror (a writable one for D). D0 = 0, or 1 for a pointer outside.
; Uses D1-D7/A1/A3.
FRTranslate:
 lea FF1FastRenderXDelta(pc),a3
 clr.l (a3)
 clr.l 4(a3)
 clr.l 8(a3)
 clr.l 12(a3)
 lea FRChanTab(pc),a1
 move.w FRB_CON0(a0),d7
 move.w FRB_CON1(a0),d6
 moveq #0,d5
 move.w FRB_SIZE(a0),d5
 move.l d5,d4
 andi.w #$3f,d5             ; width in words, 0 = 64
 bne.b .h
 moveq #64,d5
.h:
 lsr.l #6,d4                ; height, 0 = 1024
 bne.b .v
 move.l #1024,d4
.v:
 btst #0,d6
 bne.w .line
 moveq #0,d3                ; channel 0 = A .. 3 = D
.chan:
 moveq #11,d0
 sub.w d3,d0
 btst d0,d7
 beq.w .next
 move.w 2(a1,d3.w*4),d0     ; offset of the last word from the first:
 move.w (a0,d0.w),d0        ; (V - 1) * (2H + mod) + 2(H - 1),
 andi.w #$fffe,d0           ; negated in descending mode
 ext.l d0
 add.l d5,d0
 add.l d5,d0
 move.l d4,d1
 subq.l #1,d1
 muls.l d1,d0
 add.l d5,d0
 add.l d5,d0
 subq.l #2,d0
 btst #1,d6
 beq.b .asc
 neg.l d0
.asc:
 move.w (a1,d3.w*4),d1
 move.l (a0,d1.w),d1
 bclr #0,d1                 ; first word
 move.l d1,d2
 add.l d0,d2                ; last word
 cmp.l d1,d2
 bge.b .ordered
 exg d1,d2
.ordered:
 move.l d1,d0               ; lowest byte
 move.l d2,d1
 addq.l #1,d1               ; highest byte
 movem.l d0-d1,16(a3)       ; the Chip span, for FR5 tracking
 IFD FF1_FAST_RENDER_CHIPREAD
 movem.l d0-d1,-(sp)
 bsr.w FRSpan
 bne.b .found
 movem.l (sp)+,d0-d1
 cmpi.l #$80000,d1          ; logged and accessed in place
 bhs.w .miss
 bsr.w FRLogChipRead
 bra.w .next
.found:
 addq.l #8,sp
 ELSE
 bsr.w FRSpan
 beq.w .miss
 ENDC
 cmpi.w #3,d3
 bne.b .store
 move.l #FR_WRITABLE,d2
 btst d1,d2
 beq.w .miss
.store:
 tst.w FF1FastRenderTrack(pc)
 beq.b .stored
 bsr.w FRTrackChannel
 bne.w .outside
.stored:
 move.w (a1,d3.w*4),d1
 add.l d0,(a0,d1.w)
 move.l d0,(a3,d3.w*4)
.next:
 addq.w #1,d3
 cmpi.w #4,d3
 blo.w .chan
 moveq #0,d0
 rts
.miss:
 moveq #1,d0
 rts
.outside:
 moveq #6,d0
 rts
.line:
 ; C and D start at the first pixel; APT is the error term. Over V pixels
 ; the line moves at most V - 1 rows and V - 1 pixels, in the directions
 ; of the octant bits: Y by SUD ? SUL : AUL, X by SUD ? AUL : SUL.
 move.w FRB_CMOD(a0),d0
 andi.w #$fffe,d0
 ext.l d0
 move.l d4,d1
 subq.l #1,d1
 muls.l d1,d0               ; Y travel in bytes
 btst #4,d6
 beq.b .yaul
 btst #3,d6
 bra.b .ydir
.yaul:
 btst #2,d6
.ydir:
 beq.b .ydone
 neg.l d0
.ydone:
 move.l d4,d1
 addi.l #15,d1
 lsr.l #4,d1
 add.l d1,d1                ; X travel in bytes, rounded up to a word
 btst #4,d6
 beq.b .xsul
 btst #2,d6
 bra.b .xdir
.xsul:
 btst #3,d6
.xdir:
 beq.b .xdone
 neg.l d1
.xdone:
 moveq #0,d2                ; lowest offset
 moveq #1,d5                ; highest offset
 tst.l d0
 bmi.b .ylow
 add.l d0,d5
 bra.b .x
.ylow:
 add.l d0,d2
.x:
 tst.l d1
 bmi.b .xlow
 add.l d1,d5
 bra.b .span
.xlow:
 add.l d1,d2
.span:
 moveq #2,d3                ; C, then D
.lchan:
 moveq #11,d0
 sub.w d3,d0
 btst d0,d7
 beq.b .lnext
 move.w (a1,d3.w*4),d1
 move.l (a0,d1.w),d1
 bclr #0,d1
 move.l d1,d0
 add.l d2,d0
 add.l d5,d1
 movem.l d0-d1,16(a3)
 IFD FF1_FAST_RENDER_CHIPREAD
 movem.l d0-d1,-(sp)
 bsr.w FRSpan
 bne.b .lfound
 movem.l (sp)+,d0-d1
 cmpi.l #$80000,d1
 bhs.w .miss
 bsr.w FRLogChipRead
 bra.b .lnext
.lfound:
 addq.l #8,sp
 ELSE
 bsr.w FRSpan
 beq.w .miss
 ENDC
 move.l #FR_WRITABLE,d4
 btst d1,d4
 beq.w .miss
 tst.w FF1FastRenderTrack(pc)
 beq.b .ltracked
 bsr.w FRTrackChannel
 bne.w .outside
.ltracked:
 move.w (a1,d3.w*4),d1
 add.l d0,(a0,d1.w)
 move.l d0,(a3,d3.w*4)
.lnext:
 addq.w #1,d3
 cmpi.w #4,d3
 blo.b .lchan
 moveq #0,d0
 rts


 IFD FF1_FAST_RENDER_CHIPREAD
; Diagnostic: D0 = lowest byte, D1 = highest byte of a span below $80000
; outside the mirrors, accessed in place in Chip; D3 = channel. Each span is
; logged once (unless an entry contains it); C and D spans carry bit 30.
FRLogChipRead:
 movem.l d0-d3/a2,-(sp)
 cmpi.w #2,d3
 blo.b .src
 bset #30,d0
 bset #30,d1
.src:
 lea FF1FastRenderChipReads(pc),a2
 addq.l #1,(a2)+            ; spans read in place
 move.l (a2)+,d3            ; entries in use
 move.l d3,d2
 bra.b .test
.scan:
 cmp.l (a2),d0
 blo.b .next
 cmp.l 4(a2),d1
 bls.b .out                 ; already covered
.next:
 addq.l #8,a2
.test:
 dbf d2,.scan
 cmpi.l #FR_CHIPREAD_ENTRIES,d3
 bhs.b .full
 move.l d0,(a2)+
 move.l d1,(a2)
 lea FF1FastRenderChipReads+4(pc),a2
 addq.l #1,(a2)
 bra.b .out
.full:
 lea FF1FastRenderChipReads+8+8*FR_CHIPREAD_ENTRIES(pc),a2
 addq.l #1,(a2)             ; spans not logged
.out:
 movem.l (sp)+,d0-d3/a2
 rts
 ENDC

; FR5 tracking of one translated channel. D1 = mirror index, D3 = channel
; (3 = D), 16(A3)/20(A3) = Chip span. Bank spans are tracked. A destination
; outside the banks returns NZ: the native stages after the copy point
; would read that range in Chip. Registers preserved.
FRTrackChannel:
 cmpi.l #2,d1
 bhs.b .other
 movem.l d0-d3,-(sp)
 move.l d1,d2
 cmpi.w #3,d3
 seq d3
 andi.l #1,d3               ; 1 = write
 movem.l 16(a3),d0-d1
 bsr.b FRTrackSpan
 movem.l (sp)+,d0-d3
 cmp.w d0,d0                ; Z: tracked
 rts
.other:
 cmpi.w #3,d3
 beq.b .write
 cmp.w d0,d0
 rts
.write:
 tst.w d3                   ; NZ
 rts

; D0 = lowest Chip byte, D1 = highest Chip byte + 1, both in bank D2 (0/1).
; D3 = 0 read, 1 write, 2 a fill that writes every byte of the span.
; Untrusted rows are first read from Chip, except rows a fill covers
; whole; written rows become dirty. Registers preserved.
FRTrackSpan:
 movem.l d0-d7/a0-a2,-(sp)
 lea FF1FastRenderMirrors(pc),a0
 move.l (a0,d2.w*8),d4      ; Chip bank
 lea FF1FastRenderDelta(pc),a0
 move.l (a0,d2.w*4),d7      ; Fast - Chip
 lea FF1FastRenderRows(pc),a2
 mulu.w #FR_ROWS_PAD,d2
 adda.l d2,a2
 sub.l d4,d0
 sub.l d4,d1
 cmp.l d0,d1
 bls.w .fault
 cmpi.l #FR_BANK_BYTES,d1
 bhi.w .fault
 move.l d0,d5
 divu.l #FR_ROW_BYTES,d5    ; first row
 move.l d1,d6
 subq.l #1,d6
 divu.l #FR_ROW_BYTES,d6    ; last row
.row:
 move.l d5,d2
 mulu.w #FR_ROW_BYTES,d2    ; row offset
 cmpi.w #2,d3
 bne.b .touch
 cmp.l d2,d0
 bhi.b .touch
 move.l d2,a0
 lea FR_ROW_BYTES(a0),a0
 cmpa.l d1,a0
 bhi.b .touch
 move.b #2,(a2,d5.l)
 lea FF1FastRenderStageStats(pc),a0
 addq.l #1,FR5S_FILLED(a0)
 bra.b .next
.touch:
 tst.b (a2,d5.l)
 bne.b .fresh
 move.l d4,a0
 adda.l d2,a0               ; Chip row
 lea (a0,d7.l),a1           ; its shadow row
 rept FR_ROW_BYTES/4
 move.l (a0)+,(a1)+
 endr
 move.b #1,(a2,d5.l)
 lea FF1FastRenderStageStats(pc),a0
 addq.l #1,FR5S_REFRESHED(a0)
.fresh:
 tst.w d3
 beq.b .next
 move.b #2,(a2,d5.l)
.next:
 addq.l #1,d5
 cmp.l d6,d5
 bls.b .row
 movem.l (sp)+,d0-d7/a0-a2
 rts
.fault:
 moveq #1,d0
 bra.w FF1FastRenderFault

; Publication: copy every dirty row of both banks from its shadow to Chip.
FRPublishRows:
 movem.l d0-d3/a0-a3,-(sp)
 lea FF1FastRenderStageStats(pc),a3
 moveq #0,d3                ; bank
.bank:
 lea FF1FastRenderMirrors(pc),a0
 move.l (a0,d3.w*8),a0      ; Chip bank
 lea FF1FastRenderDelta(pc),a1
 move.l (a1,d3.w*4),d1
 lea FF1FastRenderRows(pc),a2
 move.w d3,d0
 mulu.w #FR_ROWS_PAD,d0
 adda.l d0,a2
 move.w #FR_ROWS-1,d2
.row:
 cmpi.b #2,(a2)+
 bne.b .skip
 lea (a0,d1.l),a1
 rept FR_ROW_BYTES/4
 move.l (a1)+,(a0)+
 endr
 addq.l #1,FR5S_PUBLISHED(a3)
 dbf d2,.row
 bra.b .done
.skip:
 lea FR_ROW_BYTES(a0),a0
 dbf d2,.row
.done:
 addq.w #1,d3
 cmpi.w #2,d3
 blo.b .bank
 movem.l (sp)+,d0-d3/a0-a3
 rts

; Image pointers back to Chip addresses after the blit.
FRUntranslate:
 lea FF1FastRenderXDelta(pc),a3
 lea FRChanTab(pc),a1
 moveq #3,d3
.u:
 move.l (a3,d3.w*4),d0
 beq.b .n
 move.w (a1,d3.w*4),d1
 sub.l d0,(a0,d1.w)
.n:
 dbf d3,.u
 rts

; D0 = lowest byte, D1 = highest byte. Returns D0 = Fast - Chip delta and
; D1 = mirror index when both lie in the same mirror, else D0 = 0 (Z set).
FRSpan:
 movem.l d2/a0-a1,-(sp)
 move.l d1,a1
 move.l d0,a0
 move.l d0,d2
 bsr.w FRLookup
 bmi.b .miss
 move.l a0,d1
 sub.l d2,d1                ; delta
 move.l d0,d2               ; index
 move.l a1,a0
 move.l d1,a1
 bsr.w FRLookup
 bmi.b .miss
 cmp.l d2,d0
 bne.b .miss
 move.l d2,d1
 move.l a1,d0
 bra.b .out
.miss:
 moveq #0,d0
.out:
 movem.l (sp)+,d2/a0-a1
 tst.l d0
 rts

; A0 = Chip address. Returns D0 = mirror index and A0 = its Fast address,
; or D0 = -1 (N set) and A0 unchanged.
FRLookup:
 movem.l d1/a1-a2,-(sp)
 lea FF1FastRenderMirrors(pc),a1
 lea FF1FastRenderDelta(pc),a2
 moveq #0,d0
.next:
 move.l (a1)+,d1
 bmi.b .miss
 cmpa.l d1,a0
 blo.b .skip
 cmpa.l (a1),a0
 bhs.b .skip
 adda.l (a2,d0.w*4),a0
 bra.b .out
.skip:
 addq.l #4,a1
 addq.l #1,d0
 bra.b .next
.miss:
 moveq #-1,d0
.out:
 movem.l (sp)+,d1/a1-a2
 tst.l d0
 rts

; A0 = Chip address a CPU writer of a redirected stage is about to write.
; While redirected it becomes the Fast copy; an address outside the
; writable mirrors takes the production fault exit. Other registers and
; the condition codes are preserved.
FF1FastRenderTarget:
 move.w ccr,-(sp)
 tst.w FF1FastRenderRedirect(pc)
 bne.b .map
 move.w (sp)+,ccr
 rts
.map:
 movem.l d0-d1,-(sp)
 bsr.w FRLookup
 bmi.b .fault
 move.l #FR_WRITABLE,d1
 btst d0,d1
 beq.b .fault
 ; A prefix stage's CPU writes must be tracked: only the fill below is.
 tst.w FF1FastRenderTrack(pc)
 bne.b .untracked
 movem.l (sp)+,d0-d1
 move.w (sp)+,ccr
 rts
.fault:
 moveq #3,d0
 bra.w FF1FastRenderFault
.untracked:
 moveq #7,d0
 bra.w FF1FastRenderFault

; A0 = Chip address of a CPU fill of D7.w whole 48-byte rows (H10). As
; FF1FastRenderTarget, and in a prefix stage the rows become dirty.
FF1FastRenderTargetRows:
 move.w ccr,-(sp)
 tst.w FF1FastRenderRedirect(pc)
 bne.b .map
 move.w (sp)+,ccr
 rts
.map:
 movem.l d0-d3,-(sp)
 move.l a0,d2
 bsr.w FRLookup
 bmi.b .fault
 move.l #FR_WRITABLE,d1
 btst d0,d1
 beq.b .fault
 tst.w FF1FastRenderTrack(pc)
 beq.b .out
 cmpi.l #2,d0
 bhs.b .outside
 exg d0,d2                  ; D0 = Chip start, D2 = bank
 moveq #0,d1
 move.w d7,d1
 mulu.w #FR_ROW_BYTES,d1
 add.l d0,d1
 moveq #2,d3
 bsr.w FRTrackSpan
.out:
 movem.l (sp)+,d0-d3
 move.w (sp)+,ccr
 rts
.fault:
 moveq #3,d0
 bra.w FF1FastRenderFault
.outside:
 moveq #6,d0
 bra.w FF1FastRenderFault

; A native fallback that would draw into Chip while redirected.
FF1FastRenderNativeGuard:
 move.w ccr,-(sp)
 tst.w FF1FastRenderRedirect(pc)
 bne.b .fault
 move.w (sp)+,ccr
 rts
.fault:
 moveq #4,d0
 bra.w FF1FastRenderFault

; Replaces the instruments' JSR to the WritePixel stub $2a1b0 (stack:
; RastPort, x, y). Redirected, the CPU writes the pixel into the Fast bank
; with the OS semantics in use here: no layer, JAM1 or JAM2, FgPen in the
; planes under Mask, and nothing outside the bitmap. Otherwise the stub runs.
FF1FastRenderWritePixel:
 tst.w FF1FastRenderRedirect(pc)
 bne.b .soft
 jmp $2a1b0
.soft:
 movem.l d0-d5/a0-a2,-(sp)
 move.l 40(sp),a1           ; RastPort
 move.l 44(sp),d0           ; x
 move.l 48(sp),d1           ; y
 tst.l (a1)                 ; rp_Layer
 bne.w .fault
 move.b 28(a1),d3           ; rp_DrawMode: JAM1 or JAM2
 andi.b #$fe,d3
 bne.w .fault
 move.l 4(a1),a2            ; rp_BitMap
 moveq #0,d3
 move.w (a2),d3             ; bm_BytesPerRow
 move.l d3,d4
 lsl.l #3,d4
 cmp.l d4,d0
 bhs.b .out
 moveq #0,d4
 move.w 2(a2),d4            ; bm_Rows
 cmp.l d4,d1
 bhs.b .out
 mulu.w d3,d1
 move.l d0,d4
 lsr.l #3,d4
 add.l d4,d1                ; byte offset in each plane
 not.w d0
 andi.w #7,d0               ; bit
 move.b 25(a1),d4           ; rp_FgPen
 move.b 24(a1),d5           ; rp_Mask
 moveq #0,d3
 move.b 5(a2),d3            ; bm_Depth
 lea 8(a2),a2               ; bm_Planes
 lea FF1FastRenderSiteStats+FR4S_SOFT+4*FRSITE_PIXEL(pc),a1
 bra.b .test
.plane:
 move.l (a2)+,a0
 btst #0,d5
 beq.b .skip
 adda.l d1,a0
 bsr.w FF1FastRenderTarget
 addq.l #1,(a1)
 btst #0,d4
 beq.b .clear
 bset d0,(a0)
 bra.b .skip
.clear:
 bclr d0,(a0)
.skip:
 lsr.b #1,d4
 lsr.b #1,d5
.test:
 dbf d3,.plane
.out:
 movem.l (sp)+,d0-d5/a0-a2
 rts
.fault:
 moveq #5,d0
 bra.w FF1FastRenderFault

; D0 = reason. Never draws into an unknown address: record it and leave
; through the production fault exit.
FF1FastRenderFault:
 lea FF1FastRenderSiteStats(pc),a1
 addq.l #1,FR4S_FAULTS(a1)
 move.l d0,FR4S_FAULT_REASON(a1)
 moveq #0,d0
 move.w FF1FastRenderSite(pc),d0
 move.l d0,FR4S_FAULT_SITE(a1)
 bsr.w FF1FastRenderRedirectOff
 bra.l FF1ProductionFault

; Redirect the drawing that follows into the Fast copies (only when active).
FF1FastRenderRedirectOn:
 movem.l a0-a1,-(sp)
 tst.w FF1FastRenderActive(pc)
 beq.b .done
 lea FF1FastRenderImage-$40(pc),a1   ; register base of the image
 lea FF1FastRenderRegs(pc),a0
 move.l a1,(a0)
 lea FF1FastRenderRedirect(pc),a0
 move.w #1,(a0)
 lea FF1FastRenderSiteStats(pc),a0
 addq.l #1,FR4S_REDIRECTS(a0)
.done:
 movem.l (sp)+,a0-a1
 rts
FF1FastRenderRedirectOff:
 move.l a0,-(sp)
 lea FF1FastRenderRegs(pc),a0
 move.l #$dff000,(a0)
 lea FF1FastRenderRedirect(pc),a0
 clr.w (a0)
 lea FF1FastRenderTrack(pc),a0
 clr.w (a0)
 move.l (sp)+,a0
 rts

; The mirror written by native CPU code outside the draw (the cockpit/gauge
; table and the glyph/text range share their extent with the audio
; descriptors) is refreshed from Chip before a redirected draw.
FF1FastRenderRefresh:
 movem.l d0-d1/a0-a2,-(sp)
 lea FF1FastRenderMirrors+2*8(pc),a2
 lea FF1FastRenderDelta+2*4(pc),a1
 moveq #1-1,d1
.range:
 move.l (a2)+,a0
 move.l (a2)+,d0
 sub.l a0,d0
 lsr.l #2,d0
 subq.l #1,d0
 move.l a1,-(sp)
 move.l (a1),a1
 adda.l a0,a1
.long:
 move.l (a0)+,(a1)+
 dbf d0,.long
 move.l (sp)+,a1
 addq.l #4,a1
 dbf d1,.range
 movem.l (sp)+,d0-d1/a0-a2
 rts

; B8Draw, after the last stage and its WaitBlit, before the buffer views are
; restored. Ends a redirected section; the diagnostic publishes the bank.
FF1FastRenderFinish:
 move.w ccr,-(sp)
 tst.w FF1FastRenderRedirect(pc)
 beq.b .done
 bsr.w FF1FastRenderRedirectOff
 IFD FF1_FAST_RENDER_FULL
 movem.l d0/a0-a1,-(sp)
 move.l $226ae,a1
 move.l (a1),a1             ; plane 0: the start of the back bank
 move.l a1,a0
 bsr.w FF1FastRenderMap
 tst.l d0
 bne.b .out
 move.w #FR_BANK_BYTES/4-1,d0
.copy:
 move.l (a0)+,(a1)+
 dbf d0,.copy
.out:
 movem.l (sp)+,d0/a0-a1
 ENDC
.done:
 move.w (sp)+,ccr
 rts

; Immutable equal-layout A/B preset, outside the lifecycle zero ranges.
FF1FastRenderControl: dc.w 1
; Immutable preset: 1 = run the FR5 prefix stages, 0 = empty prefix (FR4).
FF1FastRenderStages: dc.w 1
 even
; Expected bank table at $66c92: plane pointers of bank 0 and bank 1.
FF1FastRenderBanks:
 dc.l $18f48,$1b798,$1dfe8,0
 dc.l $528d8,$55128,$57978,0
; Mirrors: Chip start, Chip end (exclusive); -1 ends the table.
FF1FastRenderMirrors:
 dc.l $18f48,$18f48+FR_BANK_BYTES   ; bank 0 shadow
 dc.l $528d8,$528d8+FR_BANK_BYTES   ; bank 1 shadow
 dc.l $cd30,$d3e0                   ; cockpit/gauge table, glyphs, text
 dc.l $d3e0,$18f48                  ; game graphics up to bank 0
 dc.l $18f48+FR_BANK_BYTES,$528d8   ; game graphics up to bank 1
 dc.l -1
FR_MIRRORS equ 5
; Diagnostics; the nonzero tag keeps the counters across lifecycle resets.
FF1FastRenderStats:
 dc.l 'FR3S',0,0,0,0,0,0,0,0,0,0,-1,0
FF1FastRenderSiteStats:
 dc.l 'FR4S'
 dcb.l FR4S_LONGS,0
FF1FastRenderStageStats:
 dc.l 'FR5S'
 dcb.l FR5S_LONGS,0
 IFD FF1_FAST_RENDER_CHIPREAD
FR_CHIPREAD_ENTRIES equ 512
; 'FR4C', spans read in place, entries, entries x (low, high), unlogged.
 dc.l 'FR4C'
FF1FastRenderChipReads:
 dcb.l 2+2*FR_CHIPREAD_ENTRIES+1,0
 ENDC
; Register base of the patched base-register sites: the custom chip, or the
; image - $40 while redirected. Nonzero, so the lifecycle reset keeps it; every
; release and redirect end restores the custom chip.
FF1FastRenderRegs: dc.l $dff000
; Zero-initialized lifecycle state.
FF1FastRenderBlock: dc.l 0
FF1FastRenderBlockBytes: dc.l 0
FF1FastRenderActive: dc.w 0
FF1FastRenderPending: dc.w 0
FF1FastRenderDelta: ds.l FR_MIRRORS
FF1FastRenderRedirect: dc.w 0
FF1FastRenderSite: dc.w 0
FF1FastRenderXDelta: ds.l 6         ; channel deltas A-D, then the Chip span
FF1FastRenderTrack: dc.w 0
FF1FastRenderStaged: dc.w 0
FF1FastRenderRows: ds.b 2*FR_ROWS_PAD
FF1FastRenderImage: ds.b $3c         ; FRB_IMAGE: registers $040-$075 and B state
