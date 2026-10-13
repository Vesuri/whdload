; Register frames for the opt-in 68000 all-car conversion callbacks.
; Not installed by this module. The caller supplies the callback-specific
; clobbers from UpdateHooks, augmented for the all-car context below.
; D0/A0: per-car lookup. D4: all-car heading input. D7: velocity input.
; D0 remains the first saved register so callbacks returning through saved D0
; retain their stack offset. CCR is saved/restored separately by the caller.
; Both instructions are MC68000-safe; repeated registers form a single mask.
FF1Coarse200Save macro
 movem.l \1/d0/d4/d7/a0,-(sp)
 endm
FF1Coarse200Restore macro
 movem.l (sp)+,\1/d0/d4/d7/a0
 endm
