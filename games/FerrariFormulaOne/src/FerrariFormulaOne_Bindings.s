; Bind a candidate's game-address operands to the native DOS hunk table.
; Default-off, 68000-safe. The table is generated from instruction operands
; and explicit signature/relocation records, never by scanning arbitrary data
; for values that happen to look like pointers.
 ifnd FF1_PUBLIC_BINDINGS
FF1_PUBLIC_BINDINGS equ 0
 endc
 ifne FF1_PUBLIC_BINDINGS
; Record: target offset.l, hunk table byte offset.w, shift.w (0 or 16),
; hunk-relative addend.l, expected target word.w, reserved.w. Offset -1 ends.
; A0=candidate base, A1=records (writable expected words), A2=DOS BPTR table.
; D0=0 success, -1 invalid/changed operand. Other registers preserved.
; Caller owns the candidate, excludes concurrent execution, and flushes cache
; before publishing any entry. No native hunk ownership changes are made.
; Validate every record before modifying any operand. Reapplication is allowed:
; successful writes update the expected words for the next overlay generation.
FF1ApplyBindings:
 movem.l d1-d5/a0-a5,-(sp)
 move.l a0,a3
 move.l a1,a4
.check:
 move.l (a1),d0
 cmpi.l #-1,d0
 beq.b .write_start
 tst.l d0
 bmi.w .bad
 btst #0,d0
 bne.w .bad
 move.w 4(a1),d1
 andi.w #3,d1
 bne.w .bad
 move.w 6(a1),d1
 beq.b .shift_ok
 cmpi.w #16,d1
 bne.w .bad
.shift_ok:
 move.l a3,a5
 adda.l d0,a5
 move.w (a5),d2
 cmp.w 12(a1),d2
 bne.w .bad
 bsr.w .resolve
 tst.l d0
 bmi.w .bad
 adda.w #16,a1
 bra.b .check
.write_start:
 move.l a4,a1
.write:
 move.l (a1),d0
 cmpi.l #-1,d0
 beq.b .ok
 move.l a3,a5
 adda.l d0,a5
 bsr.w .resolve
 move.w d2,(a5)
 move.w d2,12(a1)
 adda.w #16,a1
 bra.b .write
.ok:
 moveq #0,d0
 bra.b .done
.bad:
 moveq #-1,d0
.done:
 movem.l (sp)+,d1-d5/a0-a5
 rts
.resolve:
 moveq #0,d1
 move.w 4(a1),d1
 cmpi.w #208*4,d1           ; SPS 0481's table has slots 0..208
 bhi.b .invalid
 move.l 0(a2,d1.w),d2
 beq.b .invalid
 move.l d2,d3
 andi.l #$c0000000,d3
 bne.b .invalid
 lsl.l #2,d2               ; BPTR -> segment header
 addq.l #4,d2              ; skip link, reach hunk contents
 bcs.b .invalid
 add.l 8(a1),d2
 bcs.b .invalid
 move.w 6(a1),d1
 lsr.l d1,d2
 moveq #0,d0
 rts
.invalid:
 moveq #-1,d0
 rts
 endc
