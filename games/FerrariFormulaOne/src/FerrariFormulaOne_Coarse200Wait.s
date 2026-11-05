; C4-only idle shortcut for the native graphics WaitBlit wrapper.
; Installed inside the existing hunk transaction; exit/unload restores it.
; Two custom-chip reads retain the old Agnus busy-bit settling requirement.
; Busy calls use the unchanged graphics.library wait and its CIA delay.
FF1C4InstallWaitIdle:
 move.w C4WaitIdleControl(pc),-(sp)
 tst.w (sp)+
 bne.w .done
 cmpi.w #$2f0e,$2a130
 bne.w C1Fault
 cmpi.w #$2c79,$2a132
 bne.w C1Fault
 cmpi.w #$0002,$2a134
 bne.w C1Fault
 cmpi.w #$43c8,$2a136
 bne.w C1Fault
 cmpi.w #$4eae,$2a138
 bne.w C1Fault
 cmpi.w #$ff1c,$2a13a
 bne.w C1Fault
 cmpi.w #$2c5f,$2a13c
 bne.w C1Fault
 cmpi.w #$4e75,$2a13e
 bne.w C1Fault
 lea FF1C4WaitIdle(pc),a0
 move.w #$4ef9,$2a130
 move.l a0,$2a132
 move.w #$4e71,$2a136
.done:
 rts
FF1C4WaitIdle:
 tst.b $dff002
 btst #6,$dff002
 beq.b .idle
 move.l a6,-(sp)
 move.l $243c8,a6
 jmp $2a138
.idle:
 ; Match the original gfx_WaitBlit final status/CCR read.
 tst.b $dff002
 rts
C4WaitIdleControl: dc.w 0
