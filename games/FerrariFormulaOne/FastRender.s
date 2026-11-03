; FR3 (FASTRAM_PLAN.md): Fast RAM shadows, source mirrors, copy point and
; publication. 68020+ fine payload, assembled only with FF1_FAST_RENDER.
; Nothing is drawn in Fast RAM yet. The prefix is empty, so the publication
; copy is empty, and native drawing runs unchanged in Chip.
;
; Install (every driving entry, from the barrier) qualifies the CPU (030/040/
; 060) and the Chip layout. The first draw then makes one MEMF_FAST allocation
; for both bank shadows and every FR1 drawing source and seeds them from Chip.
; Any failure selects today's path.
; Every lifecycle reset (loop exit, unload, rollback) releases the block
; before the payload's zero-initialized state is cleared, so the menus never
; see the allocation.
;
; Mirror table: entries 0 and 1 are the two banks, three planes of 10,320
; bytes each, as in the native bank table; the rest are the FR1 census Chip
; sources, padded to 16 bytes. The WHDLoad Kickstart 1.3 environment makes
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
; (none in FR3).
FF1FastRenderPrefix:
 move.w ccr,-(sp)
 tst.w FF1FastRenderPending(pc)
 beq.b .done
 bsr.w FF1FastRenderAllocate
.done:
 move.w (sp)+,ccr
 rts

; B8Draw, after the field wait, before the first native stage: copy the
; region owned by the prefix from the back shadow to the back Chip bank.
; The FR3 prefix is empty, so nothing is copied.
FF1FastRenderPublish:
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

; Immutable equal-layout A/B preset, outside the lifecycle zero ranges.
FF1FastRenderControl: dc.w 1
 even
; Expected bank table at $66c92: plane pointers of bank 0 and bank 1.
FF1FastRenderBanks:
 dc.l $18f48,$1b798,$1dfe8,0
 dc.l $528d8,$55128,$57978,0
; Mirrors: Chip start, Chip end (exclusive); -1 ends the table.
FF1FastRenderMirrors:
 dc.l $18f48,$18f48+FR_BANK_BYTES   ; bank 0 shadow
 dc.l $528d8,$528d8+FR_BANK_BYTES   ; bank 1 shadow
 dc.l $cd30,$cd80                   ; cockpit/gauge table
 dc.l $cf50,$d3e0                   ; glyphs, text, pit strings
 dc.l $17230,$17260                 ; small car image
 dc.l $18d80,$18e10                 ; Chip hunk 46
 dc.l $22650,$229d0                 ; flag/HUD image
 dc.l $23e10,$28e40                 ; car images and masks
 dc.l $34ba0,$34d00                 ; car images and masks
 dc.l $35f70,$3c8a0                 ; cockpit image planes
 dc.l $41390,$42900                 ; gauge/cockpit composition scratch
 dc.l $45470,$459f0                 ; car images and masks
 dc.l $49790,$49a60                 ; mirror bitmap
 dc.l $4b560,$4ba30                 ; HUD images
 dc.l $50180,$50450                 ; mirror bitmap
 dc.l $518e0,$527f0                 ; car-mask and colour scratch
 dc.l -1
FR_MIRRORS equ 16
; Diagnostics; the nonzero tag keeps the counters across lifecycle resets.
FF1FastRenderStats:
 dc.l 'FR3S',0,0,0,0,0,0,0,0,0,0,-1,0
; Zero-initialized lifecycle state.
FF1FastRenderBlock: dc.l 0
FF1FastRenderBlockBytes: dc.l 0
FF1FastRenderActive: dc.w 0
FF1FastRenderPending: dc.w 0
FF1FastRenderDelta: ds.l FR_MIRRORS
