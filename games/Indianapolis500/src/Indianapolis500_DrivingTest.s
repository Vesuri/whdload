; Diagnostic only: enter Practice (1) or Race (2) through the native menu, then hold
; the native accelerator key. This file is absent from normal builds.
driving_test_magic dc.b 'I5DR'
driving_test_ticks dc.l 0
driving_test_ready dc.w 0

driving_test_start
 movem.l d0-a6,-(sp)
 move.l motion_game(pc),a0
 adda.l #$2a59c,a0
 jsr (a0)
 lea driving_test_ready(pc),a0
 move.w #1,(a0)
 move.l motion_game(pc),a0
 adda.l #$7e4,a0
 jsr (a0)
 movem.l (sp)+,d0-a6
 rts

driving_test_menu
 move.l a0,-(sp)
 move.l motion_game(pc),a0
 adda.l #$28000,a0
 IFEQ DRIVING_TEST-2
 cmp.w #8,$3b0e(a0)        ; Main menu vs race-length submenu
 bne.s .race_length
 move.w #4,$3b0c(a0)       ; Race
 bra.s .selected
.race_length clr.w $3b0c(a0) ; first race-length choice (10 laps)
.selected
 ELSE
 move.w #2,$3b0c(a0)       ; native Main menu: Practice
 ENDC
 move.l (sp)+,a0
 rts

driving_test_input
 move.l a0,-(sp)
 lea driving_test_ready(pc),a0
 tst.w (a0)
 beq.s .native
 lea driving_test_ticks(pc),a0
 addq.l #1,(a0)
 move.l motion_game(pc),a0
 adda.l #$10000,a0
 bset #0,-$61e4(a0)        ; held keypad/up accelerator, game:9e1c
.native move.l motion_game(pc),a0
 adda.l #$10000,a0
 addq.w #1,-$64d8(a0)      ; original game:9b28 counter and CCR
 move.l (sp)+,a0
 rts
