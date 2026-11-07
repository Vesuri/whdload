; Click inputs need a button release before they trigger again: release Enhanced frame
; rate, developer CUSTOM2 bit 8 (docs/click-inputs.md).
;
; The game polls its buttons as a level. h1:01b8c copies the pointer and buttons into
; $e036/$e038/$e03a(a4) for every UI (main panel, modal screens, combat, save-name
; editor); the button hit test h6:007da returns a gadget's id whenever the left button bit
; is set, and modal screens also treat "button down, no gadget" as a click outside. So a
; held button repeats its command on every poll, and with faster rendering or 25 Hz game
; timing the U-turn flips the heading back and forth and toggles repeat.
;
; _click_filter turns the button word into press events: a press passes once, then the
; buttons read as released until every button has been released. Holding stays a level
; only on the main panel's movement gadgets (walk, run, strafe, turn, the compass ring),
; which the hit test reports while the press that started on them continues.
; With the 25 Hz timing the main tick and combat take their buttons from history
; (_sim_input_pointer, _sim_combat_pointer); they feed the filter instead, and combat's
; live read at h9:00404, which history overwrites, does not.

CLICK_MAIN_LIST = $b8a6-$10000		; -18266(a4): the main panel's gadget list

_click_install
        movem.l d0-a6,-(sp)
        move.l (_custom2,pc),d0
        btst #8,d0
        beq .done
        move.l (_custom1,pc),d1
        bne .done
        move.l (_hunks+4,pc),a2
        move.l (_h6,pc),a3
        move.l (_hunks+9*4,pc),a4
        ; The rest lies beyond 16-bit reach of the tag list (clicks_hooks.s).
        lea (_click_install,pc),a0
        adda.l #_click_patch-_click_install,a0
        jsr (a0)
        move.l a0,d1
        bne .bad
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
.done   movem.l (sp)+,d0-a6
        rts
.bad    bra _c2p_abort
