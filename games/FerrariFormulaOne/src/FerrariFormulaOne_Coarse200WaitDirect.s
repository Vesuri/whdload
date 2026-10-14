; C4-only direct routing of measured native absolute WaitBlit calls.
; Keep the existing R1 idle/busy helper and all of its settling/status reads.
; Only JSR destination operands change; return addresses and registers match.
; The hunk transaction records/restores each operand on exit and unload.
; Validate every call before modifying any, in both equal-layout arms.
FF1C4InstallWaitDirect:
 cmpi.w #$4ef9,$2a130
 bne.w C1Fault
 lea FF1C4WaitIdle(pc),a1
 cmpa.l $2a132,a1
 bne.w C1Fault
 lea $24dc6,a0
 bsr.w .check
 lea $6ad46,a0
 bsr.w .check
 lea $24b9c,a0
 bsr.w .check
 lea $24c28,a0
 bsr.w .check
 lea $32e12,a0
 bsr.w .check
 lea $6ad94,a0
 bsr.w .check
 lea $32e6c,a0
 bsr.w .check
 lea $24c82,a0
 bsr.w .check
 lea $32dae,a0
 bsr.w .check
 lea $6bb36,a0
 bsr.w .check
 lea $6b0fc,a0
 bsr.w .check
 lea $24d18,a0
 bsr.w .check
 lea $6c516,a0
 bsr.w .check
 lea $6b082,a0
 bsr.w .check
 lea $6baa0,a0
 bsr.w .check
 lea $6ac16,a0
 bsr.w .check
 lea $654e6,a0
 bsr.w .check
 lea $6b054,a0
 bsr.w .check
 lea $6abc6,a0
 bsr.w .check
 lea $6c4f4,a0
 bsr.w .check
 move.w C4WaitDirectControl(pc),-(sp)
 tst.w (sp)+
 bne.w .done
 lea FF1C4WaitIdle(pc),a1
 move.l a1,$24dc8
 move.l a1,$6ad48
 move.l a1,$24b9e
 move.l a1,$24c2a
 move.l a1,$32e14
 move.l a1,$6ad96
 move.l a1,$32e6e
 move.l a1,$24c84
 move.l a1,$32db0
 move.l a1,$6bb38
 move.l a1,$6b0fe
 move.l a1,$24d1a
 move.l a1,$6c518
 move.l a1,$6b084
 move.l a1,$6baa2
 move.l a1,$6ac18
 move.l a1,$654e8
 move.l a1,$6b056
 move.l a1,$6abc8
 move.l a1,$6c4f6
.done:
 rts
.check:
 cmpi.w #$4eb9,(a0)
 bne.w C1Fault
 lea $2a130,a1
 cmpa.l 2(a0),a1
 bne.w C1Fault
 rts
C4WaitDirectControl: dc.w 1
