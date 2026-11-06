; FR8 (FASTRAM_PLAN.md) diagnostic: a per-frame pacing log. Assembled only
; with FF1_FAST_RENDER_PACING, never in the release or the FR candidate.
;
; Each published frame writes one 32-byte entry to a ring of FR8_ENTRIES.
; An event is the field counter (schedule_context, low word) and the beam
; line (VPOSR/VHPOSR, 0-312) at that point:
;   FR8E_BEGIN  the last tick of the frame begins (schedule_begin, after its
;               wait for a due tick)
;   FR8E_PREP   B8Draw's road preparation, after the LoadView request of
;               the frame before
;   FR8E_DRAWN  the staged draw has ended (FR_B8Cut, before the field wait)
;   FR8E_COPY   the field wait has ended; the publication starts
;   FR8E_DONE   the publication has ended
; FR8E_TICKS is the completed tick count at DONE, FR8E_PULSES the number of
; ticks with the native 100 ms pulse (opponent update) since the frame
; before, FR8E_BANK the low word of the Chip bank published (plane 0), FR8E_WRITTEN
; the FR7 longword count at DONE. FR8Count counts every entry written;
; entry n is at (n mod FR8_ENTRIES)*32. The log is dcb data, which the
; lifecycle reset leaves alone.

FR8_ENTRIES equ 1024
FR8_ENTRY equ 48
FR8E_TICKS equ 0
FR8E_PULSES equ 4
FR8E_BANK equ 6
FR8E_BEGIN equ 8
FR8E_PREP equ 12
FR8E_DRAWN equ 16
FR8E_COPY equ 20
FR8E_DONE equ 24
FR8E_WRITTEN equ 28
FR8E_VBL equ 32                 ; at the copy: the field's VBL service, field and line
FR8E_REQ equ 36                 ; the last LoadView request before this frame: field, line
FR8E_REQKIND equ 40             ; 1 early (FF1FastRenderShow), 0 B8Draw
FR8E_REQBANK equ 42             ; $66f88 at the request

; D0.w = event offset. Stores the field and beam line in the current entry.
; All registers and the condition codes are kept.
FR8Mark:
 move.w ccr,-(sp)
 movem.l d1-d2/a0-a1,-(sp)
 lea (FR8Current.l,pc),a0
 adda.w d0,a0
 lea (schedule_context.l,pc),a1
.again:
 move.l FF1T_FIELDS(a1),d1
 move.l $dff004,d2
 cmp.l FF1T_FIELDS(a1),d1
 bne.b .again
 lsr.l #8,d2
 andi.w #$1ff,d2
 move.w d1,(a0)+
 move.w d2,(a0)
 movem.l (sp)+,d1-d2/a0-a1
 move.w (sp)+,ccr
 rts

; schedule_begin, after the tick is due and events_pulse is set.
FR8MarkBegin:
 move.w ccr,-(sp)
 move.l d0,-(sp)
 moveq #FR8E_BEGIN,d0
 bsr.w FR8Mark
 move.l a0,-(sp)
 lea (events_pulse.l,pc),a0
 tst.w (a0)
 beq.b .out
 lea (FR8Current.l,pc),a0
 addq.w #1,FR8E_PULSES(a0)
.out:
 move.l (sp)+,a0
 move.l (sp)+,d0
 move.w (sp)+,ccr
 rts

; 4(sp) = $226ae, the back bank's table entry, pushed by B8Draw: the stages
; repoint it later, and this file follows public_bind, so a native address
; here would not be bound.
FR8MarkPrep:
 move.w ccr,-(sp)
 movem.l d0/a0-a1,-(sp)
 moveq #FR8E_PREP,d0
 bsr.w FR8Mark
 lea (FR8Current.l,pc),a0
 move.l 18(sp),a1
 move.l (a1),d0
 move.w d0,FR8E_BANK(a0)
 movem.l (sp)+,d0/a0-a1
 move.w (sp)+,ccr
 rts

FR8MarkDrawn:
 move.l d0,-(sp)
 moveq #FR8E_DRAWN,d0
 bsr.w FR8Mark
 move.l (sp)+,d0
 rts

FR8MarkCopy:
 move.l d0,-(sp)
 moveq #FR8E_COPY,d0
 bsr.w FR8Mark
 move.l a0,-(sp)
 lea (FR8Current.l,pc),a0
 move.l FR8VblMark(pc),FR8E_VBL(a0)
 move.l (sp)+,a0
 move.l (sp)+,d0
 rts

; The game's VBL server (schedule_vbl), after the field count: the field and
; beam line it ran at. Graphics' VBL server loads COP2LC from LOFlist, and the
; 1.3 copinit list jumps to COP2LC at line 12, so a later service shows the
; previous view for one more field. All registers and the CCR are kept.
FR8Vbl:
 move.w ccr,-(sp)
 movem.l d0/a0,-(sp)
 lea (schedule_context.l,pc),a0
 move.w FF1T_FIELDS+2(a0),d0
 lea FR8VblMark(pc),a0
 move.w d0,(a0)+
 move.l $dff004,d0
 lsr.l #8,d0
 andi.w #$1ff,d0
 move.w d0,(a0)
 movem.l (sp)+,d0/a0
 move.w (sp)+,ccr
 rts

; After a LoadView request (D0.w = 1 early, 0 B8Draw): its field, line and
; bank, for the next frame's entry. All registers and the CCR are kept.
FR8Request:
 move.w ccr,-(sp)
 movem.l d0-d1/a0-a1,-(sp)
 lea (FR8Current.l,pc),a0
 move.w d0,FR8E_REQKIND(a0)
 move.w $66f88,FR8E_REQBANK(a0)
 moveq #FR8E_REQ,d0
 bsr.w FR8Mark
 movem.l (sp)+,d0-d1/a0-a1
 move.w (sp)+,ccr
 rts

; After the publication: complete the entry and append it to the ring.
FR8MarkDone:
 move.w ccr,-(sp)
 movem.l d0-d1/a0-a1,-(sp)
 moveq #FR8E_DONE,d0
 bsr.w FR8Mark
 lea (FR8Current.l,pc),a0
 lea (schedule_context.l,pc),a1
 move.l FF1T_TICKS(a1),FR8E_TICKS(a0)
 lea (FF1FastRenderCopyStats.l,pc),a1
 move.l FR7S_WRITTEN(a1),FR8E_WRITTEN(a0)
 lea (FR8Count.l,pc),a1
 move.l (a1),d0
 addq.l #1,(a1)
 andi.l #FR8_ENTRIES-1,d0
 mulu.w #FR8_ENTRY,d0
 lea (FR8Log.l,pc),a1
 adda.l d0,a1
 moveq #FR8_ENTRY/4-1,d1
.copy:
 move.l (a0)+,(a1)+
 dbf d1,.copy
 lea (FR8Current.l,pc),a0
 clr.w FR8E_PULSES(a0)
 movem.l (sp)+,d0-d1/a0-a1
 move.w (sp)+,ccr
 rts

 even
FR8Tag: dc.l 'FR8L'
FR8Count: dcb.l 1,0
FR8EntryBytes: dc.w FR8_ENTRY
FR8VblMark: dc.w 0,0
FR8Current: dcb.b FR8_ENTRY,0
FR8Log: dcb.b FR8_ENTRIES*FR8_ENTRY,0
