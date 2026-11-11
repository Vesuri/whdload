; Bind a candidate's game-address operands to the native DOS hunk table.
; Default-off, 68000-safe. The table is generated from instruction operands
; and explicit signature/relocation records, never by scanning arbitrary data
; for values that happen to look like pointers.
 ifnd FF1_PUBLIC_BINDINGS
FF1_PUBLIC_BINDINGS equ 0
 endc
 ifne FF1_PUBLIC_BINDINGS
; Table (tools/bindings.py): hunk count.w, then per used hunk its DOS table byte
; offset.w, previous base.l and new base.l; then records of delta.w from the
; previous record's offset (0 ends), hunk index.b, kind.b (0 long, 1 high word,
; 2 low word) and hunk-relative addend.w. An operand's expected value is the
; hunk's previous base plus the addend.
; A0=candidate base, A1=table (writable bases), A2=DOS BPTR table.
; D0=0 success, -1 invalid/changed operand. Other registers preserved.
; Caller owns the candidate, excludes concurrent execution, and flushes cache
; before publishing any entry. No native hunk ownership changes are made.
; Validate every record before modifying any operand. Reapplication is allowed:
; successful writes make the new bases the previous ones for the next overlay
; generation.
FF1ApplyBindings:
 movem.l d1-d5/a0-a5,-(sp)
 move.l a0,a3
 move.w (a1)+,d5
 move.l a1,a4
 move.w d5,d4
 bra.b .next_hunk
.hunk:
 moveq #0,d1
 move.w (a1)+,d1
 cmpi.w #208*4,d1           ; SPS 0481's table has slots 0..208
 bhi.w .bad
 move.l 0(a2,d1.w),d2
 beq.w .bad
 move.l d2,d3
 andi.l #$c0000000,d3
 bne.w .bad
 lsl.l #2,d2               ; BPTR -> segment header
 addq.l #4,d2              ; skip link, reach hunk contents
 move.l d2,d3
 addi.l #$10000,d3          ; every addend is a word
 bcs.w .bad
 addq.l #4,a1
 move.l d2,(a1)+
.next_hunk:
 dbf d4,.hunk
 move.l a1,a5
 move.l a3,a0
.check:
 move.w (a1)+,d0
 beq.b .write_start
 adda.w d0,a0
 bsr.b .entry
 tst.b d4
 beq.b .check_long
 cmpi.b #2,d4
 bhi.b .bad
 beq.b .check_word
 swap d2
.check_word:
 cmp.w (a0),d2
 bne.b .bad
 bra.b .check
.check_long:
 cmp.l (a0),d2
 bne.b .bad
 bra.b .check
.write_start:
 move.l a5,a1
 move.l a3,a0
.write:
 move.w (a1)+,d0
 beq.b .bases
 adda.w d0,a0
 bsr.b .entry
 tst.b d4
 beq.b .write_long
 cmpi.b #2,d4
 beq.b .write_word
 swap d3
.write_word:
 move.w d3,(a0)
 bra.b .write
.write_long:
 move.l d3,(a0)
 bra.b .write
.bases:
 move.l a4,a1
 bra.b .next_base
.base:
 move.l 6(a1),2(a1)
 lea 10(a1),a1
.next_base:
 dbf d5,.base
 moveq #0,d0
 bra.b .done
.bad:
 moveq #-1,d0
.done:
 movem.l (sp)+,d1-d5/a0-a5
 rts
; A1=record after its delta. D2=previous value, D3=new value, D4=kind; A1 advanced.
.entry:
 moveq #0,d1
 move.b (a1)+,d1
 move.b (a1)+,d4
 moveq #0,d3
 move.w (a1)+,d3
 move.w d1,d2
 lsl.w #2,d1
 add.w d2,d1
 add.w d1,d1               ; index * 10
 move.l 2(a4,d1.w),d2
 add.l d3,d2
 add.l 6(a4,d1.w),d3
 rts
 endc
