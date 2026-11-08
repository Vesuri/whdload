; VERIFY/TIMING_PROJECTILE only. Launch through the native spell-projectile
; routine, preserving item/slot allocation, position, velocity and region setup.
; This isolates projectile stepping; it is not a spell-menu/resource-cost test.
_timing_projectile_launch
        movem.l d0-a6,-(sp)
        move.w (_timing_study_armed,pc),d0
        beq .done
        lea (_timing_projectile_launched,pc),a0
        tst.w (a0)
        bne .done
        move.w #1,(a0)
        move.l (_hunks+5*4,pc),a0
        IFD TIMING_THROW
        ; Select a known native projectile item for this physics-only fixture.
        ; Restore the previous equipped item after the native throw operation.
        move.w (h11_00334-$8000,a4),-(sp)
        move.w #55,(h11_00334-$8000,a4)
        lea (h5_0195c,a0),a0
        jsr (a0)
        move.w (sp)+,(h11_00334-$8000,a4)
        ELSE
        lea (h5_019aa,a0),a0
        move.l #10,-(sp)
        jsr (a0)
        addq.l #4,sp
        ENDC
.done   movem.l (sp)+,d0-a6
        rts
_timing_projectile_launched dc.w 0
