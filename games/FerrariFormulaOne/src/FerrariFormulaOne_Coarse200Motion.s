; 68000 200 ms ownership callbacks, ported from UpdateHooks all-car branch.
; Only included by the experimental complete C4 integration.
; Preserve Q16 state and all reset/contact/save writers; no rational /5 carry.
; Q02 native ownership checks: 56 position snapshot/reset/restore cases,
; 40 cold velocity writes, and all 28 car pairs in both contact directions.
; Contact exchanges longitudinal tails; native sideways impulses replace only
; the integer word. Position assignment takes the source tail with the new
; native integer. Final Q02 checks also cover scalar-speed resets/exchange,
; 432 work/wall/recovery writers, 96 off-road writes and 72 full multi-segment
; paths on A500 and A500+Fast: 768 cases per profile, each suite restored before
; 20 ordinary updates. Bounded forced-wall debt is accounted without deletion.
; Evidence: tmp/dev/manifest/step5-c4-q02-validation.json. Real modal Q03 remains
; separate; these ownership checks do not establish keyboard or menu behavior.
FF1PlayerContext macro
 bsr.w \2
 endm
install_velocity:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #7,d0
 blo.w .done
 cmpi.w #$33d0,$671e6
 bne.w .bad
 cmpi.w #$0003,$671e8
 bne.w .bad
 cmpi.w #$2f96,$671ea
 bne.w .bad
 cmpi.w #$30b9,$685a6
 bne.w .bad
 cmpi.w #$0003,$685a8
 bne.w .bad
 cmpi.w #$2f96,$685aa
 bne.w .bad
 cmpi.w #$33ee,$67bcc
 bne.w .bad
 cmpi.w #$fff2,$67bce
 bne.w .bad
 cmpi.w #$0003,$67bd0
 bne.w .bad
 cmpi.w #$2f94,$67bd2
 bne.w .bad
 cmpi.w #$3039,$6dc96
 bne.w .bad
 cmpi.w #$0003,$6dc98
 bne.w .bad
 cmpi.w #$2f94,$6dc9a
 bne.w .bad
 cmpi.w #$3239,$6dd44
 bne.w .bad
 cmpi.w #$0003,$6dd46
 bne.w .bad
 cmpi.w #$2fbc,$6dd48
 bne.w .bad
 cmpi.w #$3039,$6e084
 bne.w .bad
 cmpi.w #$0003,$6e086
 bne.w .bad
 cmpi.w #$2fbc,$6e088
 bne.w .bad
 cmpi.w #$302e,$6e2ae
 bne.w .bad
 cmpi.w #$000e,$6e2b0
 bne.w .bad
 cmpi.w #$4cdf,$6e2b2
 bne.w .bad
 cmpi.w #$000c,$6e2b4
 bne.w .bad
 cmpi.w #$3080,$68990
 bne.w .bad
 cmpi.w #$202f,$68992
 bne.w .bad
 cmpi.w #$0000,$68994
 bne.w .bad
 cmpi.w #$4250,$689a0
 bne.w .bad
 cmpi.w #$206f,$689a2
 bne.w .bad
 cmpi.w #$0000,$689a4
 bne.w .bad
 cmpi.w #$3081,$68b98
 bne.w .bad
 cmpi.w #$322f,$68b9a
 bne.w .bad
 cmpi.w #$0000,$68b9c
 bne.w .bad
 cmpi.w #$30bc,$68baa
 bne.w .bad
 cmpi.w #$00c8,$68bac
 bne.w .bad
 cmpi.w #$4a6f,$68bae
 bne.w .bad
 cmpi.w #$0000,$68bb0
 bne.w .bad
 cmpi.w #$3081,$6e95e
 bne.w .bad
 cmpi.w #$2040,$6e960
 bne.w .bad
 cmpi.w #$d1fc,$6e962
 bne.w .bad
 cmpi.w #$0006,$6e964
 bne.w .bad
 cmpi.w #$f14c,$6e966
 bne.w .bad
 cmpi.w #$3081,$6e968
 bne.w .bad
 cmpi.w #$202e,$6e96a
 bne.w .bad
 cmpi.w #$fffc,$6e96c
 bne.w .bad
 cmpi.w #$3084,$6917a
 bne.w .bad
 cmpi.w #$3d44,$6917c
 bne.w .bad
 cmpi.w #$fff6,$6917e
 bne.w .bad
 cmpi.w #$33c0,$68386
 bne.w .bad
 cmpi.w #$0003,$68388
 bne.w .bad
 cmpi.w #$2f94,$6838a
 bne.w .bad
 cmpi.w #$33c0,$6e2a4
 bne.w .bad
 cmpi.w #$0003,$6e2a6
 bne.w .bad
 cmpi.w #$2f96,$6e2a8
 bne.w .bad
 cmpi.w #$33c0,$6e2ec
 bne.w .bad
 cmpi.w #$0003,$6e2ee
 bne.w .bad
 cmpi.w #$2f96,$6e2f0
 bne.w .bad
 cmpi.w #$33c0,$69b36
 bne.w .bad
 cmpi.w #$0003,$69b38
 bne.w .bad
 cmpi.w #$2f96,$69b3a
 bne.w .bad
 cmpi.w #$33c0,$69b50
 bne.w .bad
 cmpi.w #$0003,$69b52
 bne.w .bad
 cmpi.w #$2f96,$69b54
 bne.w .bad
 cmpi.w #$3081,$6ee00
 bne.w .bad
 cmpi.w #$322e,$6ee02
 bne.w .bad
 cmpi.w #$000e,$6ee04
 bne.w .bad
 cmpi.w #$3081,$6ee16
 bne.w .bad
 cmpi.w #$0c6e,$6ee18
 bne.w .bad
 cmpi.w #$00c8,$6ee1a
 bne.w .bad
 cmpi.w #$0012,$6ee1c
 bne.w .bad
 cmpi.w #$33c0,$6993a
 bne.w .bad
 cmpi.w #$0003,$6993c
 bne.w .bad
 cmpi.w #$2f94,$6993e
 bne.w .bad
 cmpi.w #$33c0,$69a0a
 bne.w .bad
 cmpi.w #$0003,$69a0c
 bne.w .bad
 cmpi.w #$2f94,$69a0e
 bne.w .bad
 cmpi.w #$33c1,$6998e
 bne.w .bad
 cmpi.w #$0003,$69990
 bne.w .bad
 cmpi.w #$2f96,$69992
 bne.w .bad
 cmpi.w #$33c1,$69a5e
 bne.w .bad
 cmpi.w #$0003,$69a60
 bne.w .bad
 cmpi.w #$2f96,$69a62
 bne.w .bad
 cmpi.w #$30b9,$68576
 bne.w .bad
 cmpi.w #$0003,$68578
 bne.w .bad
 cmpi.w #$2fbe,$6857a
 bne.w .bad
 cmpi.w #$3080,$6897e
 bne.w .bad
 cmpi.w #$202f,$68980
 bne.w .bad
 cmpi.w #$0000,$68982
 bne.w .bad
 cmpi.w #$3080,$68b84
 bne.w .bad
 cmpi.w #$302f,$68b86
 bne.w .bad
 cmpi.w #$0000,$68b88
 bne.w .bad
 cmpi.w #$33c0,$672f0
 bne.w .bad
 cmpi.w #$0003,$672f2
 bne.w .bad
 cmpi.w #$2fbe,$672f4
 bne.w .bad
 cmpi.w #$33c0,$673fc
 bne.w .bad
 cmpi.w #$0003,$673fe
 bne.w .bad
 cmpi.w #$2fbe,$67400
 bne.w .bad
 cmpi.w #$33c0,$67426
 bne.w .bad
 cmpi.w #$0003,$67428
 bne.w .bad
 cmpi.w #$2fbe,$6742a
 bne.w .bad
 cmpi.w #$33c0,$67438
 bne.w .bad
 cmpi.w #$0003,$6743a
 bne.w .bad
 cmpi.w #$2fbe,$6743c
 bne.w .bad
 cmpi.w #$33c0,$6744a
 bne.w .bad
 cmpi.w #$0003,$6744c
 bne.w .bad
 cmpi.w #$2fbe,$6744e
 bne.w .bad
 cmpi.w #$33c0,$67476
 bne.w .bad
 cmpi.w #$0003,$67478
 bne.w .bad
 cmpi.w #$2fbe,$6747a
 bne.w .bad
 cmpi.w #$33c0,$675c0
 bne.w .bad
 cmpi.w #$0003,$675c2
 bne.w .bad
 cmpi.w #$2fbe,$675c4
 bne.w .bad
 cmpi.w #$33c0,$6766c
 bne.w .bad
 cmpi.w #$0003,$6766e
 bne.w .bad
 cmpi.w #$2fbe,$67670
 bne.w .bad
 cmpi.w #$33c0,$6768e
 bne.w .bad
 cmpi.w #$0003,$67690
 bne.w .bad
 cmpi.w #$2fbe,$67692
 bne.w .bad
 cmpi.w #$33c0,$676e0
 bne.w .bad
 cmpi.w #$0003,$676e2
 bne.w .bad
 cmpi.w #$2fbe,$676e4
 bne.w .bad
 cmpi.w #$33c1,$69970
 bne.w .bad
 cmpi.w #$0003,$69972
 bne.w .bad
 cmpi.w #$2fbe,$69974
 bne.w .bad
 cmpi.w #$33c1,$69a42
 bne.w .bad
 cmpi.w #$0003,$69a44
 bne.w .bad
 cmpi.w #$2fbe,$69a46
 bne.w .bad
 cmpi.w #$33d0,$6721c
 bne.w .bad
 cmpi.w #$0003,$6721e
 bne.w .bad
 cmpi.w #$2fc0,$67220
 bne.w .bad
 cmpi.w #$33c0,$679fe
 bne.w .bad
 cmpi.w #$0003,$67a00
 bne.w .bad
 cmpi.w #$2fbe,$67a02
 bne.w .bad
 cmpi.w #$33c0,$6838c
 bne.w .bad
 cmpi.w #$0003,$6838e
 bne.w .bad
 cmpi.w #$2fbe,$68390
 bne.w .bad
 cmpi.w #$33fc,$694ce
 bne.w .bad
 cmpi.w #$0064,$694d0
 bne.w .bad
 cmpi.w #$0003,$694d2
 bne.w .bad
 cmpi.w #$2fbe,$694d4
 bne.w .bad
 cmpi.w #$33c0,$69b30
 bne.w .bad
 cmpi.w #$0003,$69b32
 bne.w .bad
 cmpi.w #$2fbe,$69b34
 bne.w .bad
 cmpi.w #$33c0,$69b4a
 bne.w .bad
 cmpi.w #$0003,$69b4c
 bne.w .bad
 cmpi.w #$2fbe,$69b4e
 bne.w .bad
 lea velocity_671e6(pc),a0
 move.w #$4ef9,$671e6
 move.l a0,$671e8
 lea velocity_685a6(pc),a0
 move.w #$4ef9,$685a6
 move.l a0,$685a8
 lea velocity_67bcc(pc),a0
 move.w #$4ef9,$67bcc
 move.l a0,$67bce
 move.w #$4e71,$67bd2
 lea velocity_6dc96(pc),a0
 move.w #$4ef9,$6dc96
 move.l a0,$6dc98
 lea velocity_6dd44(pc),a0
 move.w #$4ef9,$6dd44
 move.l a0,$6dd46
 lea velocity_6e084(pc),a0
 move.w #$4ef9,$6e084
 move.l a0,$6e086
 lea velocity_6e2ae(pc),a0
 move.w #$4ef9,$6e2ae
 move.l a0,$6e2b0
 move.w #$4e71,$6e2b4
 lea velocity_68990(pc),a0
 move.w #$4ef9,$68990
 move.l a0,$68992
 lea velocity_689a0(pc),a0
 move.w #$4ef9,$689a0
 move.l a0,$689a2
 lea velocity_68b98(pc),a0
 move.w #$4ef9,$68b98
 move.l a0,$68b9a
 lea velocity_68baa(pc),a0
 move.w #$4ef9,$68baa
 move.l a0,$68bac
 move.w #$4e71,$68bb0
 lea velocity_6e95e(pc),a0
 move.w #$4ef9,$6e95e
 move.l a0,$6e960
 move.w #$4e71,$6e964
 move.w #$4e71,$6e966
 lea velocity_6e968(pc),a0
 move.w #$4ef9,$6e968
 move.l a0,$6e96a
 lea velocity_6917a(pc),a0
 move.w #$4ef9,$6917a
 move.l a0,$6917c
 lea velocity_68386(pc),a0
 move.w #$4ef9,$68386
 move.l a0,$68388
 lea velocity_6e2a4(pc),a0
 move.w #$4ef9,$6e2a4
 move.l a0,$6e2a6
 lea velocity_6e2ec(pc),a0
 move.w #$4ef9,$6e2ec
 move.l a0,$6e2ee
 lea velocity_69b36(pc),a0
 move.w #$4ef9,$69b36
 move.l a0,$69b38
 lea velocity_69b50(pc),a0
 move.w #$4ef9,$69b50
 move.l a0,$69b52
 lea velocity_6ee00(pc),a0
 move.w #$4ef9,$6ee00
 move.l a0,$6ee02
 lea velocity_6ee16(pc),a0
 move.w #$4ef9,$6ee16
 move.l a0,$6ee18
 move.w #$4e71,$6ee1c
 lea velocity_6993a(pc),a0
 move.w #$4ef9,$6993a
 move.l a0,$6993c
 lea velocity_69a0a(pc),a0
 move.w #$4ef9,$69a0a
 move.l a0,$69a0c
 lea velocity_6998e(pc),a0
 move.w #$4ef9,$6998e
 move.l a0,$69990
 lea velocity_69a5e(pc),a0
 move.w #$4ef9,$69a5e
 move.l a0,$69a60
 lea velocity_68576(pc),a0
 move.w #$4ef9,$68576
 move.l a0,$68578
 lea velocity_6897e(pc),a0
 move.w #$4ef9,$6897e
 move.l a0,$68980
 lea velocity_68b84(pc),a0
 move.w #$4ef9,$68b84
 move.l a0,$68b86
 lea velocity_672f0(pc),a0
 move.w #$4ef9,$672f0
 move.l a0,$672f2
 lea velocity_673fc(pc),a0
 move.w #$4ef9,$673fc
 move.l a0,$673fe
 lea velocity_67426(pc),a0
 move.w #$4ef9,$67426
 move.l a0,$67428
 lea velocity_67438(pc),a0
 move.w #$4ef9,$67438
 move.l a0,$6743a
 lea velocity_6744a(pc),a0
 move.w #$4ef9,$6744a
 move.l a0,$6744c
 lea velocity_67476(pc),a0
 move.w #$4ef9,$67476
 move.l a0,$67478
 lea velocity_675c0(pc),a0
 move.w #$4ef9,$675c0
 move.l a0,$675c2
 lea velocity_6766c(pc),a0
 move.w #$4ef9,$6766c
 move.l a0,$6766e
 lea velocity_6768e(pc),a0
 move.w #$4ef9,$6768e
 move.l a0,$67690
 lea velocity_676e0(pc),a0
 move.w #$4ef9,$676e0
 move.l a0,$676e2
 lea velocity_69970(pc),a0
 move.w #$4ef9,$69970
 move.l a0,$69972
 lea velocity_69a42(pc),a0
 move.w #$4ef9,$69a42
 move.l a0,$69a44
 lea velocity_6721c(pc),a0
 move.w #$4ef9,$6721c
 move.l a0,$6721e
 lea velocity_679fe(pc),a0
 move.w #$4ef9,$679fe
 move.l a0,$67a00
 lea velocity_6838c(pc),a0
 move.w #$4ef9,$6838c
 move.l a0,$6838e
 lea velocity_694ce(pc),a0
 move.w #$4ef9,$694ce
 move.l a0,$694d0
 move.w #$4e71,$694d4
 lea velocity_69b30(pc),a0
 move.w #$4ef9,$69b30
 move.l a0,$69b32
 lea velocity_69b4a(pc),a0
 move.w #$4ef9,$69b4a
 move.l a0,$69b4c
 lea $2275a,a0
 lea speed_shadow(pc),a1
 moveq #7,d0
.init_speed:
 move.w (a0)+,(a1)+
 clr.w (a1)+
 clr.w (a1)+
 dbra d0,.init_speed
 lea velocity_installed(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #16,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
velocity_671e6:
 dc.w $33d0,$0003,$2f96
 IFD FF1_C4_HOOK_P5
C4P5Gate_velocity_671e6 equ *
 bra.w .p5_original
 ; The displaced native instruction still runs at its original point.
 ; Defer only the shadow callback to the last adjacent load/store hook.
 jmp $671ec
.p5_original:
 ENDC
C4SaveMask000 equ *
 movem.l a0/a1/d0/d1/d2/d4/d7,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_load
 move.w (sp)+,ccr
C4SaveMask001 equ *
 movem.l (sp)+,a0/a1/d0/d1/d2/d4/d7
 jmp $671ec
velocity_685a6:
 dc.w $30b9,$0003,$2f96
 IFD FF1_C4_HOOK_P5
C4P5Gate_velocity_685a6 equ *
 bra.w .p5_original
 ; Native loads/stores between the combined callbacks neither call out nor
 ; consume these shadow values. Keep their instructions and CCR intact.
 movem.l d0/a0-a1,-(sp)
 move.w sr,-(sp)
 bsr.w bridge_context
 tst.l d0
 bmi.w fine_fault
 bsr.w bridge_store
 bsr.w velocity_speed_store
 bsr.w velocity_store
 move.w (sp)+,ccr
 movem.l (sp)+,d0/a0-a1
 jmp $685ac
.p5_original:
 ENDC
C4SaveMask002 equ *
 movem.l a0/d0/d4/d7,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_store
 move.w (sp)+,ccr
C4SaveMask003 equ *
 movem.l (sp)+,a0/d0/d4/d7
 jmp $685ac
velocity_67bcc:
 dc.w $33ee,$fff2,$0003,$2f94
C4SaveMask004 equ *
 movem.l a0/a1/a2/d0/d1/d2/d4/d7,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_rotate
 move.w (sp)+,ccr
C4SaveMask005 equ *
 movem.l (sp)+,a0/a1/a2/d0/d1/d2/d4/d7
 jmp $67bd4
velocity_6dc96:
 dc.w $3039,$0003,$2f94
C4SaveMask006 equ *
 movem.l a0/a1/a2/a4/d0/d1/d2/d4/d7,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_project
 move.w (sp)+,ccr
C4SaveMask007 equ *
 movem.l (sp)+,a0/a1/a2/a4/d0/d1/d2/d4/d7
 jmp $6dc9c
velocity_6dd44:
 dc.w $3239,$0003,$2fbc
C4SaveMask008 equ *
 movem.l a0/a4/d0/d1/d4/d7,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_raw
 move.w (sp)+,ccr
C4SaveMask009 equ *
 movem.l (sp)+,a0/a4/d0/d1/d4/d7
 jmp $6dd4a
velocity_6e084:
 dc.w $3039,$0003,$2fbc
C4SaveMask010 equ *
 movem.l a0/a4/d0/d1/d2/d4/d7,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_limit
 move.w (sp)+,ccr
C4SaveMask011 equ *
 movem.l (sp)+,a0/a4/d0/d1/d2/d4/d7
 jmp $6e08a
velocity_6e2ae:
 dc.w $302e,$000e,$4cdf,$000c
C4SaveMask012 equ *
 movem.l a0/a1/a2/a4/d0/d1/d2/d4/d7,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_returned
 move.w (sp)+,ccr
C4SaveMask013 equ *
 movem.l (sp)+,a0/a1/a2/a4/d0/d1/d2/d4/d7
 jmp $6e2b6
velocity_68990:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_cold_x
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $3080,$202f,$0000
 jmp $68996
velocity_689a0:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_cold_z
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $4250,$206f,$0000
 jmp $689a6
velocity_68b98:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_cold_x
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $3081,$322f,$0000
 jmp $68b9e
velocity_68baa:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_cold_z200
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $30bc,$00c8,$4a6f,$0000
 jmp $68bb2
velocity_6e95e:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_cold_x
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $3081,$2040,$d1fc,$0006,$f14c
 jmp $6e968
velocity_6e968:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_cold_z
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $3081,$202e,$fffc
 jmp $6e96e
velocity_6917a:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_swap_z
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $3084,$3d44,$fff6
 jmp $69180
velocity_68386:
 dc.w $33c0,$0003,$2f94
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_reset_work
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6838c
velocity_6e2a4:
 dc.w $33c0,$0003,$2f96
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_reset_work
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6e2aa
velocity_6e2ec:
 dc.w $33c0,$0003,$2f96
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_reset_work
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6e2f2
velocity_69b36:
 dc.w $33c0,$0003,$2f96
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_clamp_z
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69b3c
velocity_69b50:
 dc.w $33c0,$0003,$2f96
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_clamp_z
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69b56
velocity_6ee00:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_impulse_x
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $3081,$322e,$000e
 jmp $6ee06
velocity_6ee16:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_impulse_x
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $3081,$0c6e,$00c8,$0012
 jmp $6ee1e
velocity_6993a:
 dc.w $33c0,$0003,$2f94
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_offroad_right
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69940
velocity_69a0a:
 dc.w $33c0,$0003,$2f94
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_offroad_left
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69a10
velocity_6998e:
 dc.w $33c1,$0003,$2f96
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_offroad_z
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69994
velocity_69a5e:
 dc.w $33c1,$0003,$2f96
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_offroad_z
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69a64
velocity_68576:
 dc.w $30b9,$0003,$2fbe
 IFD FF1_C4_HOOK_P5
C4P5Gate_velocity_68576 equ *
 bra.w .p5_original
 ; The displaced native instruction still runs at its original point.
 ; Defer only the shadow callback to the last adjacent load/store hook.
 jmp $6857c
.p5_original:
 ENDC
C4SaveMask014 equ *
 movem.l a0/a1/d0/d4/d7,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_store
 move.w (sp)+,ccr
C4SaveMask015 equ *
 movem.l (sp)+,a0/a1/d0/d4/d7
 jmp $6857c
velocity_6897e:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_cold
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $3080,$202f,$0000
 jmp $68984
velocity_68b84:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_cold
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $3080,$302f,$0000
 jmp $68b8a
velocity_672f0:
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_672f0
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $672f6
velocity_673fc:
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_673fc
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $67402
velocity_67426:
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_67426
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6742c
velocity_67438:
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_67438
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6743e
velocity_6744a:
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_6744a
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $67450
velocity_67476:
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_67476
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6747c
velocity_675c0:
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_675c0
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $675c6
velocity_6766c:
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_6766c
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $67672
velocity_6768e:
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_6768e
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $67694
velocity_676e0:
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_676e0
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $676e6
velocity_69970:
 dc.w $33c1,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_69970
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69976
velocity_69a42:
 dc.w $33c1,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_69a42
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69a48
velocity_6721c:
 dc.w $33d0,$0003,$2fc0
 IFD FF1_C4_HOOK_P5
C4P5Gate_velocity_6721c equ *
 bra.w .p5_original
 ; Native loads/stores between the combined callbacks neither call out nor
 ; consume these shadow values. Keep their instructions and CCR intact.
 movem.l d0-d2/a0-a1,-(sp)
 move.w sr,-(sp)
 bsr.w velocity_load
 bsr.w bridge_context
 tst.l d0
 bmi.w fine_fault
 bsr.w bridge_load
 bsr.w velocity_speed_load
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d2/a0-a1
 jmp $67222
.p5_original:
 ENDC
C4SaveMask016 equ *
 movem.l a0/a1/d0/d4/d7,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_load
 move.w (sp)+,ccr
C4SaveMask017 equ *
 movem.l (sp)+,a0/a1/d0/d4/d7
 jmp $67222
velocity_679fe:
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_feedback
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $67a04
velocity_6838c:
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68392
velocity_694ce:
 dc.w $33fc,$0064,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $694d6
velocity_69b30:
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69b36
velocity_69b4a:
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69b50
velocity_context:
 moveq #0,d0
 move.w $32fbc,d0
 cmpi.w #7,d0
 bhi.w velocity_fault

 IFD FF1_C4_CONTEXT_P5
C4P5VelocityGate equ *
 ; Exact eight-car offsets, without a runtime dispatch cost. A0 is scratch.
 ; MOVEA/ADDA preserve X; the word lookup matches MULU's N/Z/V/C.
 move.l d0,a0
 adda.w d0,a0
 move.w .p5_offsets(pc,a0.w),d0
 ELSE
 mulu.w #12,d0
 ENDC
 lea velocity_shadow(pc),a0
 adda.l d0,a0
 rts
 IFD FF1_C4_CONTEXT_P5
.p5_offsets: dc.w 0,12,24,36,48,60,72,84
 ENDC
velocity_sync:
 FF1PlayerContext velocity_shadow,velocity_context
 move.w $32f94,d0
 move.w $32f96,d1
 bsr.w FF1VelocityReset
 rts
velocity_load:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.w velocity_sync
 FF1PlayerContext velocity_shadow,velocity_context
 move.w $32fbc,d2
 lea velocity_initialized(pc),a1
 bset d2,(a1)
 bne.w velocity_check
 bsr.w velocity_sync
 clr.l 8(a0)
 rts
velocity_store:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.w velocity_sync
 FF1PlayerContext velocity_shadow,velocity_context
 bra.w velocity_check
velocity_rotate:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.w velocity_sync
 FF1PlayerContext velocity_shadow,velocity_context
 lea 8(a0),a1
 moveq #0,d2
 move.w -16(a6),d2
 andi.l #1023,d2
 add.l d2,d2
 lea $2180c,a2
 move.w (a2,d2.l),d1
 lea $21a0c,a2
 move.w (a2,d2.l),d0
 bsr.w FF1VelocityRotateCarry020
 tst.l d1
 bne.w velocity_fault

 move.w (a0),$32f94
 move.w 4(a0),$32f96
 rts
velocity_check:
 rts
velocity_workspace:
 lea velocity_scratch(pc),a4
 rts
velocity_project:
 bsr.w velocity_workspace
 move.w 10(a6),2(a4)
 moveq #0,d0
 move.w 10(a6),d0
 andi.l #1023,d0
 add.l d0,d0
 lea $2180c,a0
 move.w (a0,d0.l),d1
 lea $21a0c,a0
 move.w (a0,d0.l),d2
 move.w 14(a6),d0
 swap d0
 clr.w d0
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .integer_speed
 move.l speed_work(pc),d0
.integer_speed:
 lea 24(a4),a0
 bsr.w FF1VelocityProject020
 tst.l d1
 bne.w velocity_fault

 FF1PlayerContext velocity_shadow,velocity_context
 move.l (a0),40(a4)
 move.l 4(a0),44(a4)
 move.l 8(a0),48(a4)
 lea 40(a4),a0
 lea 24(a4),a1
 lea 52(a4),a2
 bsr.w FF1VelocityDerivative20
 tst.l d1
 bne.w velocity_fault

 ; Retained bridge layout includes zero carry words; subtract them exactly.
 move.w 48(a4),d0
 ext.l d0
 sub.l d0,52(a4)
 bvs.w velocity_fault

 move.w 50(a4),d0
 ext.l d0
 sub.l d0,56(a4)
 bvs.w velocity_fault

 bsr.w velocity_coefficients
 lea 52(a4),a0
 bsr.w FF1VelocityRotate020
 tst.l d1
 bne.w velocity_fault

 rts
velocity_raw:
 bsr.w velocity_workspace
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .native
 move.w 52(a4),-12(a6)
 move.w 56(a4),-10(a6)
 move.w -12(a6),d0
 muls.w d0,d0
 move.w -10(a6),d1
 muls.w d1,d1
 add.l d1,d0
 bsr.w FF1SquareRootU32
 cmpi.l #32767,d0
 bhi.w velocity_fault

 move.l d0,d7
 move.l d0,6(sp)
.native:
 move.w -12(a6),32(a4)
 move.w -10(a6),34(a4)
 move.w d7,36(a4)
 rts
velocity_limit:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 bsr.w velocity_workspace
 moveq #0,d2
 move.w 36(a4),d2
 beq.b .zero
 move.w -8(a6),38(a4)
 move.w 32(a4),d0
 move.w 38(a4),d1
 bsr.w FF1VelocityLimit020
 tst.l d1
 bne.w velocity_fault

 move.w d0,-12(a6)
 move.w 34(a4),d0
 move.w 38(a4),d1
 bsr.w FF1VelocityLimit020
 tst.l d1
 bne.w velocity_fault

 move.w d0,-10(a6)
 rts
.zero:
 clr.w 38(a4)
 clr.w -12(a6)
 clr.w -10(a6)
.done:
 rts
velocity_returned:
 bsr.w velocity_workspace
 move.w -12(a6),20(a4)
 move.w -10(a6),22(a4)
 move.w 20(a4),d0
 swap d0
 clr.w d0
 move.l d0,60(a4)
 move.w 22(a4),d0
 swap d0
 clr.w d0
 move.l d0,64(a4)
 bsr.w velocity_coefficients
 neg.w d1
 lea 60(a4),a0
 bsr.w FF1VelocityRotate020
 tst.l d1
 bne.w velocity_fault

 move.l 40(a4),68(a4)
 move.l 44(a4),72(a4)
 move.l 48(a4),76(a4)
 lea 68(a4),a0
 lea 76(a4),a1
 lea 60(a4),a2
 bsr.w FF1VelocityApply20
 tst.l d1
 bne.w velocity_fault

 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.w .native
 FF1PlayerContext velocity_shadow,velocity_context
 move.l 68(a4),(a0)
 move.l 72(a4),4(a0)
 move.l 76(a4),8(a0)
 lea speed_work(pc),a1
 bsr.w FF1SpeedFromVelocity020
 tst.l d1
 bne.w velocity_fault

 tst.l (a1)
 bne.b .moving
 clr.l (a0)
 clr.l 4(a0)
 clr.l 8(a0)
 clr.l 68(a4)
 clr.l 72(a4)
 clr.l 76(a4)
.moving:
 move.w (a0),$32f94
 move.w 4(a0),$32f96
 moveq #0,d0
 move.w (a1),d0
 move.l d0,6(sp)
.native:
 rts
velocity_coefficients:
 moveq #0,d2
 move.w 2(a4),d2
 andi.l #1023,d2
 add.l d2,d2
 lea $2180c,a0
 move.w (a0,d2.l),d1
 lea $21a0c,a0
 move.w (a0,d2.l),d0
 rts
velocity_fault_x:
 moveq #21,d0
 bra.b velocity_failcode
velocity_fault_z:
 moveq #22,d0
 bra.b velocity_failcode
velocity_fault:
 moveq #17,d0
velocity_failcode:
 lea error(pc),a0
 move.l d0,(a0)
velocity_stop:
 IFD FF1_PRODUCTION
 bra.w C1Fault
 ELSE
 IFD FF1_C4_BLIT_GUARD
 bsr.w FF1C4BlitRestore
.halt: bra.b .halt
 ELSE
 bra.b velocity_stop
 ENDC
 ENDC
velocity_initialized: dc.w 0
velocity_installed: dc.l 0
velocity_loads: dc.l 0
velocity_stores: dc.l 0
velocity_rotations: dc.l 0
velocity_projects: dc.l 0
velocity_raws: dc.l 0
velocity_records_count: dc.l 0
velocity_shadow: ds.b 96
velocity_cold_x:
 suba.l #$6f13c,a0
 moveq #0,d4
 moveq #0,d5
 bra.b velocity_cold
velocity_cold_z:
 moveq #0,d5
 bra.b velocity_cold_z_common
velocity_cold_z200:
 move.l #$00c80000,d5
velocity_cold_z_common:
 suba.l #$6f14c,a0
 moveq #4,d4
velocity_cold:
 move.l a0,d0
 FF1PlayerContext velocity_shadow,velocity_array_context
 move.l d5,(a0,d4.w)
 lsr.w #1,d4
 clr.w 8(a0,d4.w)
 rts
velocity_array_context:
 cmpi.l #14,d0
 bhi.w velocity_fault

 btst #0,d0
 bne.w velocity_fault

 mulu.w #6,d0
 lea velocity_shadow(pc),a0
 adda.l d0,a0
 rts
velocity_swap_z:
 bsr.w velocity_speed_swap
 move.l a0,d6
 subi.l #$6f14c,d6
 move.l d3,d0
 FF1PlayerContext velocity_shadow,velocity_array_context
 move.l a0,a2
 move.l d6,d0
 FF1PlayerContext velocity_shadow,velocity_array_context
 move.l 4(a0),d0
 move.w 10(a0),d1
 move.l 4(a2),4(a0)
 move.w 10(a2),10(a0)
 move.l d0,4(a2)
 move.w d1,10(a2)
 rts
velocity_cold_writes: dc.l 0
velocity_swaps: dc.l 0
velocity_reset_work:
 bsr.w velocity_sync
 clr.l 8(a0)
 rts
velocity_clamp_z:
 FF1PlayerContext velocity_shadow,velocity_context
 move.w $32f96,4(a0)
 clr.w 6(a0)
 clr.w 10(a0)
 rts
velocity_impulse_x:
 ; D1 holds the newly computed native word; preserve fractional tail/carry.
 move.w d1,d4
 move.l a0,d0
 subi.l #$6f13c,d0
 FF1PlayerContext velocity_shadow,velocity_array_context
 move.w d4,(a0)
 rts
velocity_work_resets: dc.l 0
velocity_clamps: dc.l 0
velocity_impulses: dc.l 0
velocity_offroad_right:
 move.w $2aaa6,d4
 ext.l d4
 moveq #0,d5
 bra.b velocity_offroad
velocity_offroad_left:
 move.w $2aaa6,d4
 ext.l d4
 neg.l d4
 moveq #0,d5
 bra.b velocity_offroad
velocity_offroad_z:
 move.l d7,d4
 neg.l d4
 moveq #4,d5
velocity_offroad:
 FF1PlayerContext velocity_shadow,velocity_context
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 beq.b .fine
 lea $32f94,a1
 move.w d5,d0
 lsr.w #1,d0
 move.w (a1,d0.w),(a0,d5.w)
 bra.b .count
.fine:
 cmpi.l #-32768,d4
 blt.w velocity_fault

 cmpi.l #32767,d4
 bgt.w velocity_fault

 swap d4
 clr.w d4
 suba.w #8,sp
 clr.l (sp)
 clr.l 4(sp)
 move.l d4,(sp,d5.w)
 move.l sp,a2
 lea 8(a0),a1
 bsr.w FF1VelocityApply20
 adda.w #8,sp
 tst.l d1
 bne.w velocity_fault

 move.w (a0),$32f94
 move.w 4(a0),$32f96
.count:
 rts
velocity_offroads: dc.l 0
velocity_speed_rate_672f0:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 move.l d7,d0
 move.l #$672f0,d6
 bsr.w C4WeightedSpeedRate
 move.l d0,6(sp)
.done:
 rts
velocity_speed_rate_673fc:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 move.l d7,d0
 move.l #$673fc,d6
 bsr.w C4WeightedSpeedRate
 move.l d0,6(sp)
.done:
 rts
velocity_speed_rate_67426:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 move.l d7,d0
 move.l #$67426,d6
 bsr.w C4WeightedSpeedRate
 move.l d0,6(sp)
.done:
 rts
velocity_speed_rate_67438:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 move.l d7,d0
 move.l #$67438,d6
 bsr.w C4WeightedSpeedRate
 move.l d0,6(sp)
.done:
 rts
velocity_speed_rate_6744a:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 move.l d7,d0
 move.l #$6744a,d6
 bsr.w C4WeightedSpeedRate
 move.l d0,6(sp)
.done:
 rts
velocity_speed_rate_67476:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 move.l d7,d0
 move.l #$67476,d6
 bsr.w velocity_speed_rate
 move.l d0,6(sp)
.done:
 rts
velocity_speed_rate_675c0:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 move.l d7,d0
 move.l #$675c0,d6
 bsr.w velocity_speed_rate
 move.l d0,6(sp)
.done:
 rts
velocity_speed_rate_6766c:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 move.l d7,d0
 move.l #$6766c,d6
 bsr.w velocity_speed_rate
 move.l d0,6(sp)
.done:
 rts
velocity_speed_rate_6768e:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 move.l d7,d0
 move.l #$6768e,d6
 bsr.w C4WeightedSpeedRate
 move.l d0,6(sp)
.done:
 rts
velocity_speed_rate_676e0:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 move.l d7,d0
 move.l #$676e0,d6
 bsr.w C4WeightedSpeedRate
 move.l d0,6(sp)
.done:
 rts
velocity_speed_rate_69970:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 move.l d1,d0
 move.l #$69970,d6
 bsr.w velocity_speed_rate
 move.l d0,10(sp)
.done:
 rts
velocity_speed_rate_69a42:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 move.l d1,d0
 move.l #$69a42,d6
 bsr.w velocity_speed_rate
 move.l d0,10(sp)
.done:
 rts
velocity_speed_context:
 moveq #0,d0
 move.w $32fbc,d0
 add.l d0,d0
velocity_speed_array:
 cmpi.l #14,d0
 bhi.w velocity_fault

 btst #0,d0
 bne.w velocity_fault

 mulu.w #3,d0
 lea speed_shadow(pc),a0
 adda.l d0,a0
 rts
velocity_speed_reset:
 lea speed_work(pc),a0
 move.w $32fbe,d0
 bra.b velocity_speed_reset_store
velocity_speed_load:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .native
 FF1PlayerContext speed_shadow,velocity_speed_context
 move.w (a0),d0
 cmp.w $32fc0,d0
 bne.w velocity_fault

 lea speed_work(pc),a1
 move.l (a0),(a1)
 move.w 4(a0),4(a1)
 rts
.native:
 lea speed_work(pc),a0
 move.w $32fc0,d0
velocity_speed_reset_store:
 swap d0
 clr.w d0
 move.l d0,(a0)
 clr.w 4(a0)
 rts
velocity_speed_feedback:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.w velocity_speed_reset
 move.w speed_work(pc),d0
 cmp.w $32fbe,d0
 bne.w velocity_fault

 rts
velocity_speed_store:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 FF1PlayerContext speed_shadow,velocity_speed_context
 lea speed_work(pc),a1
 move.w (a1),d0
 cmp.w $32fbe,d0
 bne.w velocity_fault

 move.l (a1),(a0)
 move.w 4(a1),4(a0)
.done:
 rts
velocity_speed_cold:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 move.l a0,d0
 subi.l #$2275a,d0
 FF1PlayerContext speed_shadow,velocity_speed_array
 move.w d7,d0
 swap d0
 clr.w d0
 move.l d0,(a0)
 clr.w 4(a0)
.done:
 rts
velocity_speed_swap:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 movem.l d0-d3/a0-a2,-(sp)
 move.l a0,d2
 subi.l #$6f14c,d2
 move.l d3,d0
 FF1PlayerContext speed_shadow,velocity_speed_array
 move.l a0,a2
 move.l d2,d0
 FF1PlayerContext speed_shadow,velocity_speed_array
 move.l (a0),d0
 move.w 4(a0),d1
 move.l (a2),(a0)
 move.w 4(a2),4(a0)
 move.l d0,(a2)
 move.w d1,4(a2)
 movem.l (sp)+,d0-d3/a0-a2
.done:
 rts
velocity_speed_rate:
 lea speed_work(pc),a0
 moveq #2,d1
 bsr.w FF1SpeedRatePulses200
 tst.l d1
 bne.w velocity_fault

 move.w (a0),d0
 ext.l d0
 move.w d0,$32fbe
 rts
speed_work: ds.b 6
speed_shadow: ds.b 48
speed_records_count: dc.l 0
speed_loads: dc.l 0
speed_stores: dc.l 0
speed_cold_writes: dc.l 0
speed_swaps: dc.l 0
install_position_bridge:
 movem.l d0-d2/a0-a1,-(sp)
 cmpi.w #7,d0
 blo.w bridge_install_done
 cmpi.w #$33d0,$6720e
 bne.w bridge_install_bad
 cmpi.w #$0003,$67210
 bne.w bridge_install_bad
 cmpi.w #$2fc4,$67212
 bne.w bridge_install_bad
 cmpi.w #$30b9,$68546
 bne.w bridge_install_bad
 cmpi.w #$0003,$68548
 bne.w bridge_install_bad
 cmpi.w #$2fc4,$6854a
 bne.w bridge_install_bad
 cmpi.w #$33c1,$67b52
 bne.w bridge_install_bad
 cmpi.w #$0003,$67b54
 bne.w bridge_install_bad
 cmpi.w #$2fc4,$67b56
 bne.w bridge_install_bad
 cmpi.w #$33c0,$67a12
 bne.w bridge_install_bad
 cmpi.w #$0003,$67a14
 bne.w bridge_install_bad
 cmpi.w #$2fc2,$67a16
 bne.w bridge_install_bad
 cmpi.w #$33c0,$67a26
 bne.w bridge_install_bad
 cmpi.w #$0003,$67a28
 bne.w bridge_install_bad
 cmpi.w #$2fc4,$67a2a
 bne.w bridge_install_bad
 cmpi.w #$4279,$67a30
 bne.w bridge_install_bad
 cmpi.w #$0003,$67a32
 bne.w bridge_install_bad
 cmpi.w #$2fc4,$67a34
 bne.w bridge_install_bad
 cmpi.w #$33c0,$68306
 bne.w bridge_install_bad
 cmpi.w #$0003,$68308
 bne.w bridge_install_bad
 cmpi.w #$2fc2,$6830a
 bne.w bridge_install_bad
 cmpi.w #$33c0,$68352
 bne.w bridge_install_bad
 cmpi.w #$0003,$68354
 bne.w bridge_install_bad
 cmpi.w #$2fc2,$68356
 bne.w bridge_install_bad
 cmpi.w #$33fc,$68376
 bne.w bridge_install_bad
 cmpi.w #$015e,$68378
 bne.w bridge_install_bad
 cmpi.w #$0003,$6837a
 bne.w bridge_install_bad
 cmpi.w #$2fc2,$6837c
 bne.w bridge_install_bad
 cmpi.w #$33c0,$683b8
 bne.w bridge_install_bad
 cmpi.w #$0003,$683ba
 bne.w bridge_install_bad
 cmpi.w #$2fc4,$683bc
 bne.w bridge_install_bad
 cmpi.w #$4279,$694c8
 bne.w bridge_install_bad
 cmpi.w #$0003,$694ca
 bne.w bridge_install_bad
 cmpi.w #$2fc4,$694cc
 bne.w bridge_install_bad
 cmpi.w #$33c0,$6956a
 bne.w bridge_install_bad
 cmpi.w #$0003,$6956c
 bne.w bridge_install_bad
 cmpi.w #$2fc2,$6956e
 bne.w bridge_install_bad
 cmpi.w #$3080,$691c4
 bne.w bridge_install_bad
 cmpi.w #$202f,$691c6
 bne.w bridge_install_bad
 cmpi.w #$0010,$691c8
 bne.w bridge_install_bad
 cmpi.w #$3081,$692ae
 bne.w bridge_install_bad
 cmpi.w #$222f,$692b0
 bne.w bridge_install_bad
 cmpi.w #$0018,$692b2
 bne.w bridge_install_bad
 cmpi.w #$3081,$6886e
 bne.w bridge_install_bad
 cmpi.w #$6000,$68870
 bne.w bridge_install_bad
 cmpi.w #$00ec,$68872
 bne.w bridge_install_bad
 cmpi.w #$3080,$688e2
 bne.w bridge_install_bad
 cmpi.w #$202f,$688e4
 bne.w bridge_install_bad
 cmpi.w #$0000,$688e6
 bne.w bridge_install_bad
 cmpi.w #$3080,$68918
 bne.w bridge_install_bad
 cmpi.w #$3039,$6891a
 bne.w bridge_install_bad
 cmpi.w #$0001,$6891c
 bne.w bridge_install_bad
 cmpi.w #$c1e0,$6891e
 bne.w bridge_install_bad
 cmpi.w #$3080,$68ab8
 bne.w bridge_install_bad
 cmpi.w #$3039,$68aba
 bne.w bridge_install_bad
 cmpi.w #$0001,$68abc
 bne.w bridge_install_bad
 cmpi.w #$c1e0,$68abe
 bne.w bridge_install_bad
 cmpi.w #$4250,$68b26
 bne.w bridge_install_bad
 cmpi.w #$302f,$68b28
 bne.w bridge_install_bad
 cmpi.w #$0000,$68b2a
 bne.w bridge_install_bad
 cmpi.w #$3091,$663f4
 bne.w bridge_install_bad
 cmpi.w #$52ae,$663f6
 bne.w bridge_install_bad
 cmpi.w #$fffc,$663f8
 bne.w bridge_install_bad
 cmpi.w #$3091,$68c12
 bne.w bridge_install_bad
 cmpi.w #$322f,$68c14
 bne.w bridge_install_bad
 cmpi.w #$0000,$68c16
 bne.w bridge_install_bad
 lea bridge_6720e(pc),a1
 move.w #$4ef9,$6720e
 move.l a1,$67210
 lea bridge_68546(pc),a1
 move.w #$4ef9,$68546
 move.l a1,$68548
 lea bridge_67b52(pc),a1
 move.w #$4ef9,$67b52
 move.l a1,$67b54
 lea bridge_67a12(pc),a1
 move.w #$4ef9,$67a12
 move.l a1,$67a14
 lea bridge_67a26(pc),a1
 move.w #$4ef9,$67a26
 move.l a1,$67a28
 lea bridge_67a30(pc),a1
 move.w #$4ef9,$67a30
 move.l a1,$67a32
 lea bridge_68306(pc),a1
 move.w #$4ef9,$68306
 move.l a1,$68308
 lea bridge_68352(pc),a1
 move.w #$4ef9,$68352
 move.l a1,$68354
 lea bridge_68376(pc),a1
 move.w #$4ef9,$68376
 move.l a1,$68378
 move.w #$4e71,$6837c
 lea bridge_683b8(pc),a1
 move.w #$4ef9,$683b8
 move.l a1,$683ba
 lea bridge_694c8(pc),a1
 move.w #$4ef9,$694c8
 move.l a1,$694ca
 lea bridge_6956a(pc),a1
 move.w #$4ef9,$6956a
 move.l a1,$6956c
 lea bridge_691c4(pc),a1
 move.w #$4ef9,$691c4
 move.l a1,$691c6
 lea bridge_692ae(pc),a1
 move.w #$4ef9,$692ae
 move.l a1,$692b0
 lea bridge_6886e(pc),a1
 move.w #$4ef9,$6886e
 move.l a1,$68870
 lea bridge_688e2(pc),a1
 move.w #$4ef9,$688e2
 move.l a1,$688e4
 lea bridge_68918(pc),a1
 move.w #$4ef9,$68918
 move.l a1,$6891a
 move.w #$4e71,$6891e
 lea bridge_68ab8(pc),a1
 move.w #$4ef9,$68ab8
 move.l a1,$68aba
 move.w #$4e71,$68abe
 lea bridge_68b26(pc),a1
 move.w #$4ef9,$68b26
 move.l a1,$68b28
 lea bridge_663f4(pc),a1
 move.w #$4ef9,$663f4
 move.l a1,$663f6
 lea bridge_68c12(pc),a1
 move.w #$4ef9,$68c12
 move.l a1,$68c14
 lea bridge_installed(pc),a0
 move.l #1,(a0)
 bra.b bridge_install_done
bridge_install_bad:
 lea error(pc),a0
 move.l #6,(a0)
bridge_install_done:
 movem.l (sp)+,d0-d2/a0-a1
 rts
bridge_6720e:
 dc.w $33d0,$0003,$2fc4
 IFD FF1_C4_HOOK_P5
C4P5Gate_bridge_6720e equ *
 bra.w .p5_original
 ; The displaced native instruction still runs at its original point.
 ; Defer only the shadow callback to the last adjacent load/store hook.
 jmp $67214
.p5_original:
 ENDC
C4SaveMask018 equ *
 movem.l a0/a1/d0/d4/d7,-(sp)
 move.w sr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_load
.done:
 move.w (sp)+,ccr
C4SaveMask019 equ *
 movem.l (sp)+,a0/a1/d0/d4/d7
 jmp $67214
bridge_68546:
 dc.w $30b9,$0003,$2fc4
 IFD FF1_C4_HOOK_P5
C4P5Gate_bridge_68546 equ *
 bra.w .p5_original
 ; The displaced native instruction still runs at its original point.
 ; Defer only the shadow callback to the last adjacent load/store hook.
 jmp $6854c
.p5_original:
 ENDC
C4SaveMask020 equ *
 movem.l a0/d0/d4/d7,-(sp)
 move.w sr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_store
.done:
 move.w (sp)+,ccr
C4SaveMask021 equ *
 movem.l (sp)+,a0/d0/d4/d7
 jmp $6854c
bridge_67b52:
 dc.w $33c1,$0003,$2fc4
 ; P5 diagnostic may narrow the paired masks to D0-D4/A0-A1.
 ; bridge_context/bridge_rotate clobber only those registers; both position
 ; rotation adapters preserve the remaining caller state, including A0.
 IFD FF1_C4_HOOK_P5
C4P5RotateSave equ *
 ENDC
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_rotate
.done:
 move.w (sp)+,ccr
 IFD FF1_C4_HOOK_P5
C4P5RotateRestore equ *
 ENDC
 movem.l (sp)+,d0-d7/a0-a6
 jmp $67b58
bridge_67a12:
 dc.w $33c0,$0003,$2fc2
C4SaveMask022 equ *
 movem.l a0/d0/d4/d7,-(sp)
 move.w sr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_sync_x
.done:
 move.w (sp)+,ccr
C4SaveMask023 equ *
 movem.l (sp)+,a0/d0/d4/d7
 jmp $67a18
bridge_67a26:
 dc.w $33c0,$0003,$2fc4
C4SaveMask024 equ *
 movem.l a0/d0/d4/d7,-(sp)
 move.w sr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_sync_z
.done:
 move.w (sp)+,ccr
C4SaveMask025 equ *
 movem.l (sp)+,a0/d0/d4/d7
 jmp $67a2c
bridge_67a30:
 dc.w $4279,$0003,$2fc4
C4SaveMask026 equ *
 movem.l a0/d0/d4/d7,-(sp)
 move.w sr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_reset_z
.done:
 move.w (sp)+,ccr
C4SaveMask027 equ *
 movem.l (sp)+,a0/d0/d4/d7
 jmp $67a36
bridge_68306:
 dc.w $33c0,$0003,$2fc2
C4SaveMask028 equ *
 movem.l a0/d0/d4/d7,-(sp)
 move.w sr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_reset_x
.done:
 move.w (sp)+,ccr
C4SaveMask029 equ *
 movem.l (sp)+,a0/d0/d4/d7
 jmp $6830c
bridge_68352:
 dc.w $33c0,$0003,$2fc2
C4SaveMask030 equ *
 movem.l a0/d0/d4/d7,-(sp)
 move.w sr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_reset_x
.done:
 move.w (sp)+,ccr
C4SaveMask031 equ *
 movem.l (sp)+,a0/d0/d4/d7
 jmp $68358
bridge_68376:
 dc.w $33fc,$015e,$0003,$2fc2
C4SaveMask032 equ *
 movem.l a0/d0/d4/d7,-(sp)
 move.w sr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_reset_x
.done:
 move.w (sp)+,ccr
C4SaveMask033 equ *
 movem.l (sp)+,a0/d0/d4/d7
 jmp $6837e
bridge_683b8:
 dc.w $33c0,$0003,$2fc4
C4SaveMask034 equ *
 movem.l a0/d0/d4/d7,-(sp)
 move.w sr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_reset_z
.done:
 move.w (sp)+,ccr
C4SaveMask035 equ *
 movem.l (sp)+,a0/d0/d4/d7
 jmp $683be
bridge_694c8:
 dc.w $4279,$0003,$2fc4
C4SaveMask036 equ *
 movem.l a0/d0/d4/d7,-(sp)
 move.w sr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_reset_z
.done:
 move.w (sp)+,ccr
C4SaveMask037 equ *
 movem.l (sp)+,a0/d0/d4/d7
 jmp $694ce
bridge_6956a:
 dc.w $33c0,$0003,$2fc2
C4SaveMask038 equ *
 movem.l a0/d0/d4/d7,-(sp)
 move.w sr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_reset_x
.done:
 move.w (sp)+,ccr
C4SaveMask039 equ *
 movem.l (sp)+,a0/d0/d4/d7
 jmp $69570
bridge_691c4:
 dc.w $3080,$202f,$0010
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w bridge_contact_first
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $691ca
bridge_692ae:
 dc.w $3081,$222f,$0018
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w bridge_contact_second
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $692b4
bridge_6886e:
 dc.w $3081
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w bridge_array_x
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6895e
bridge_688e2:
 dc.w $3080,$202f,$0000
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w bridge_array_z
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $688e8
bridge_68918:
 dc.w $3080,$3039,$0001,$c1e0
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w bridge_array_x
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68920
bridge_68ab8:
 dc.w $3080,$3039,$0001,$c1e0
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w bridge_array_x
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68ac0
bridge_68b26:
 dc.w $4250,$302f,$0000
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w bridge_array_z
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68b2c
bridge_663f4:
 dc.w $3091,$52ae,$fffc
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w bridge_snapshot
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $663fa
bridge_68c12:
 dc.w $3091,$322f,$0000
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w bridge_restore
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68c18
bridge_context:
 moveq #0,d0
 move.w $32fbc,d0
 cmpi.l #7,d0
 bhi.b .bad

 IFD FF1_C4_CONTEXT_P5
C4P5PositionGate equ *
 ; Exact eight-car offsets, without a runtime dispatch cost. A0 is scratch.
 ; MOVEA/ADDA preserve X; the word lookup matches MULU's N/Z/V/C.
 move.l d0,a0
 adda.w d0,a0
 move.w .p5_offsets(pc,a0.w),d0
 ELSE
 mulu.w #12,d0
 ENDC
 lea position_shadow(pc),a0
 adda.l d0,a0
 moveq #0,d0
 rts
.bad:
 lea error(pc),a0
 move.l #7,(a0)
 moveq #-1,d0
 rts
 IFD FF1_C4_CONTEXT_P5
.p5_offsets: dc.w 0,12,24,36,48,60,72,84
 ENDC
bridge_load:
 lea fine_cross_pending(pc),a1
 clr.w (a1)
 lea fine_car_crosses(pc),a1
 clr.w (a1)
 move.w $32fc2,(a0)
 move.w $32fc4,6(a0)
 rts
bridge_store:
 move.w $32fc2,(a0)
 move.w $32fc4,6(a0)
 rts
bridge_sync_x:
 move.w $32fc2,(a0)
 rts
bridge_sync_z:
 move.w $32fc4,6(a0)
 rts
bridge_reset_x:
 move.w $32fc2,d0
 bra.w FF1PositionReset
bridge_reset_z:
 move.w $32fc4,d0
 addq.l #6,a0
 bra.w FF1PositionReset
bridge_rotate:
 move.w -16(a6),d4
 andi.l #1023,d4
 add.l d4,d4
 lea $2180c,a1
 move.w (a1,d4.l),d1
 lea $21a0c,a1
 move.w (a1,d4.l),d0
 move.w $32fc2,d2
 move.w $32fc4,d3
 bsr.w FF1PositionRotate25
 tst.l d1
 bne.b .bad

 move.w (a0),$32fc2
 move.w 6(a0),$32fc4
 rts
.bad:
 lea error(pc),a1
 move.l #8,(a1)
 rts
bridge_contact_first:
 move.w -8(a6),d2
 bra.b bridge_contact
bridge_contact_second:
 move.w -6(a6),d2
bridge_contact:
 move.w (a0),d4
 move.l a0,d1
 subi.l #$6a62a,d1
 cmpi.l #14,d1
 bhi.b .bad

 btst #0,d1
 bne.b .bad

 andi.l #$ffff,d2
 cmpi.l #7,d2
 bhi.b .bad

 mulu.w #6,d1
 mulu.w #12,d2
 lea position_shadow+6(pc),a0
 lea position_shadow+6(pc),a1
 adda.l d1,a0
 adda.l d2,a1
 move.w d4,d0
 bsr.w FF1PositionAssign
 rts
.bad:
 lea error(pc),a1
 move.l #9,(a1)
 rts
; Pointer-based cold writers do not depend on main-loop car index.
bridge_array_x:
 moveq #0,d2
 move.l #$6a61a,d1
 bra.b bridge_array_reset
bridge_array_z:
 moveq #6,d2
 move.l #$6a62a,d1
bridge_array_reset:
 move.w (a0),d0
 move.l a0,d3
 sub.l d1,d3
 cmpi.l #14,d3
 bhi.w bridge_pointer_bad

 btst #0,d3
 bne.w bridge_pointer_bad

 mulu.w #6,d3
 lea position_shadow(pc),a0
 adda.l d3,a0
 adda.l d2,a0
 bsr.w FF1PositionReset
 rts
bridge_snapshot:
 move.w (a0),d0
 move.l a0,d3
 subi.l #$227ca,d3
 cmpi.l #14,d3
 bhi.w bridge_pointer_bad

 btst #0,d3
 bne.w bridge_pointer_bad

 move.l d3,d2
 mulu.w #3,d3
 mulu.w #6,d2
 lea saved_position(pc),a0
 adda.l d3,a0
 lea position_shadow+6(pc),a1
 adda.l d2,a1
 bsr.w FF1PositionAssign
 rts
bridge_restore:
 move.w (a0),d0
 move.l a0,d3
 subi.l #$6a62a,d3
 cmpi.l #14,d3
 bhi.w bridge_pointer_bad

 btst #0,d3
 bne.w bridge_pointer_bad

 move.l d3,d2
 mulu.w #6,d3
 mulu.w #3,d2
 lea position_shadow+6(pc),a0
 adda.l d3,a0
 lea saved_position(pc),a1
 adda.l d2,a1
 bsr.w FF1PositionAssign
 rts
bridge_pointer_bad:
 lea error(pc),a1
 move.l #10,(a1)
 rts
bridge_array_resets: dc.l 0
bridge_snapshots: dc.l 0
bridge_restores: dc.l 0
saved_position: ds.b 48
bridge_contacts: dc.l 0
bridge_installed: dc.l 0
bridge_loads: dc.l 0
bridge_stores: dc.l 0
bridge_rotations: dc.l 0
bridge_resets: dc.l 0
position_shadow: ds.b 96
; Fractional position conversion for the complete 200 ms path.
install_fine_position:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #8,d0
 blo.w .done
 cmpi.l #$30390003,$67a04
 bne.w .bad
 cmpi.w #$2fc2,$67a08
 bne.w .bad
 cmpi.l #$30390003,$67a36
 bne.w .bad
 cmpi.w #$2fca,$67a3a
 bne.w .bad
 cmpi.l #$30390003,$68292
 bne.w .bad
 cmpi.w #$2fbc,$68296
 bne.w .bad
 lea fine_advance(pc),a0
 move.w #$4ef9,$67a04
 move.l a0,$67a06
 lea fine_boundary(pc),a0
 move.w #$4ef9,$67a36
 move.l a0,$67a38
 lea fine_bounds(pc),a0
 move.w #$4ef9,$68292
 move.l a0,$68294
 lea fine_installed(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #11,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts

fine_advance:
C4SaveMask040 equ *
 movem.l a0/a2/a3/a5/d0/d1/d2/d4/d7,-(sp)
 move.w sr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.w fine_fault

 move.w $32fc2,(a0)
 move.w $32fc4,6(a0)
 move.l a0,a3
 lea fine_trial(pc),a0
 move.l (a3),(a0)
 move.l 4(a3),4(a0)
 move.l 8(a3),8(a0)
 move.l a0,a5
 FF1PlayerContext velocity_shadow,velocity_context
 move.l a0,a2
 move.l a5,a0
 move.l (a2),d0
 move.w 8(a2),d1
 bsr.w FF1Position20Velocity
 tst.l d1
 bne.w fine_fault

 addq.l #6,a0
 move.l 4(a2),d0
 move.w 10(a2),d1
 bsr.w FF1Position20Velocity
 tst.l d1
 bne.w fine_fault

 moveq #0,d0
 bsr.w FF1PositionClampLower
 lea fine_trial(pc),a0
 move.l (a0),(a3)
 move.l 4(a0),4(a3)
 move.l 8(a0),8(a3)
 move.w (a0),$32fc2
 move.w 6(a0),$32fc4
 move.w (sp)+,ccr
C4SaveMask041 equ *
 movem.l (sp)+,a0/a2/a3/a5/d0/d1/d2/d4/d7
 jmp $67a36
fine_record_overflow:
 lea error(pc),a0
 move.l #12,(a0)
 bra.w fine_stop
fine_fault:
 lea error(pc),a0
 move.l #13,(a0)
fine_stop:
 bra.w velocity_stop

fine_boundary:
C4SaveMask042 equ *
 movem.l a0/a1/d0/d1/d4/d7,-(sp)
 move.w sr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.w fine_fault

 move.w $32fc2,(a0)
 move.w $32fc4,6(a0)
 moveq #0,d4
 move.w $32fca,d4
 cmp.w $2268c,d4
 bhs.w fine_fault

 add.l d4,d4
 lea $1dc24,a1
 move.w (a1,d4.l),d4
 move.w d4,-16(a6)
 andi.l #1023,d4
 add.l d4,d4
 IFD FF1_C4_BOUNDARY_P5
 move.w C4BoundaryControl(pc),-(sp)
 tst.w (sp)+
 bne.b .p5_native_coefficients
 lea C4BoundaryControl(pc),a1
 dc.w $d3fc
 dc.l C4BoundaryCoefficients-C4BoundaryControl
 move.w (a1,d4.l),d0
 ext.l d0
 adda.w #512,a1
 move.w (a1,d4.l),d1
 ext.l d1
 bra.b .p5_coefficients_done
.p5_native_coefficients:
 ENDC
 lea $2180c,a1
 move.w (a1,d4.l),d0
 muls.w #1000,d0
 asr.l #8,d0
 asr.l #7,d0
 lea $21a0c,a1
 move.w (a1,d4.l),d1
 muls.w #1000,d1
 asr.l #8,d1
 asr.l #7,d1
 IFD FF1_C4_BOUNDARY_P5
.p5_coefficients_done:
 ENDC
 bsr.w FF1PositionCrossed25
 tst.l d1
 bne.w fine_fault

 lea fine_cross_pending(pc),a1
 move.w d0,(a1)
 tst.l d0
 beq.b .inside
 lea fine_car_crosses(pc),a1
 addq.w #1,(a1)
 cmpi.w #64,(a1)
 bhi.w fine_fault

 move.w (sp)+,ccr
C4SaveMask043 equ *
 movem.l (sp)+,a0/a1/d0/d1/d4/d7
 jmp $67aac
.inside:
 move.w (sp)+,ccr
C4SaveMask044 equ *
 movem.l (sp)+,a0/a1/d0/d1/d4/d7
 jmp $68292

fine_bounds:
 move.w $32fbc,d0
C4SaveMask045 equ *
 movem.l a0/a1/d0/d1/d4/d7,-(sp)
 move.w sr,-(sp)
 lea fine_cross_pending(pc),a1
 tst.w (a1)
 beq.b .bounds
 clr.w (a1)
 move.w (sp)+,ccr
C4SaveMask046 equ *
 movem.l (sp)+,a0/a1/d0/d1/d4/d7
 jmp $67a36
.bounds:
 moveq #0,d0
 move.w $32fbc,d0
 cmpi.w #7,d0
 bhi.w fine_fault

 add.l d0,d0
 lea $32f30,a1
 tst.w (a1,d0.l)
 ble.b .done
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.w fine_fault

 move.w $32fc2,(a0)
 moveq #0,d4
 move.w $32fca,d4
 cmp.w $2268c,d4
 bhs.w fine_fault

 add.l d4,d4
 lea $1d29c,a1
 move.w (a1,d4.l),d0
 addi.w #100,d0
 bsr.w FF1PositionClampUpper
 lea $1c914,a1
 move.w (a1,d4.l),d0
 neg.w d0
 subi.w #100,d0
 bsr.w FF1PositionClampLower
 move.w (a0),$32fc2
.done:
 move.w (sp)+,ccr
C4SaveMask047 equ *
 movem.l (sp)+,a0/a1/d0/d1/d4/d7
 jmp $68298
fine_installed: dc.l 0
fine_steps: dc.l 0
fine_cross_pending: dc.w 0
fine_car_crosses: dc.w 0
fine_trial: ds.b 12
 IFD FF1_C4_BOUNDARY_P5
 include "FerrariFormulaOne_Coarse200Boundary.s"
 ENDC

install_heading:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #8,d0
 bne.w .done
 cmpi.w #$23d0,$67280
 bne.w .bad
 cmpi.w #$0003,$67282
 bne.w .bad
 cmpi.w #$2fb8,$67284
 bne.w .bad
 cmpi.w #$20b9,$6860e
 bne.w .bad
 cmpi.w #$0003,$68610
 bne.w .bad
 cmpi.w #$2fb8,$68612
 bne.w .bad
 cmpi.w #$d1b9,$678de
 bne.w .bad
 cmpi.w #$0003,$678e0
 bne.w .bad
 cmpi.w #$2fb4,$678e2
 bne.w .bad
 cmpi.w #$d1b9,$67900
 bne.w .bad
 cmpi.w #$0003,$67902
 bne.w .bad
 cmpi.w #$2fb8,$67904
 bne.w .bad
 cmpi.w #$d1b9,$67948
 bne.w .bad
 cmpi.w #$0003,$6794a
 bne.w .bad
 cmpi.w #$2fb4,$6794c
 bne.w .bad
 cmpi.w #$d1b9,$67976
 bne.w .bad
 cmpi.w #$0003,$67978
 bne.w .bad
 cmpi.w #$2fb8,$6797a
 bne.w .bad
 cmpi.w #$91b9,$67320
 bne.w .bad
 cmpi.w #$0003,$67322
 bne.w .bad
 cmpi.w #$2fb8,$67324
 bne.w .bad
 cmpi.w #$42b9,$67326
 bne.w .bad
 cmpi.w #$0003,$67328
 bne.w .bad
 cmpi.w #$2fb4,$6732a
 bne.w .bad
 cmpi.w #$93b9,$683ac
 bne.w .bad
 cmpi.w #$0003,$683ae
 bne.w .bad
 cmpi.w #$2fb8,$683b0
 bne.w .bad
 cmpi.w #$42b9,$683b2
 bne.w .bad
 cmpi.w #$0003,$683b4
 bne.w .bad
 cmpi.w #$2fb4,$683b6
 bne.w .bad
 cmpi.w #$23c0,$69590
 bne.w .bad
 cmpi.w #$0003,$69592
 bne.w .bad
 cmpi.w #$2fb4,$69594
 bne.w .bad
 cmpi.w #$23c0,$695e8
 bne.w .bad
 cmpi.w #$0003,$695ea
 bne.w .bad
 cmpi.w #$2fb8,$695ec
 bne.w .bad
 cmpi.w #$4290,$68a5e
 bne.w .bad
 cmpi.w #$202f,$68a60
 bne.w .bad
 cmpi.w #$0000,$68a62
 bne.w .bad
 cmpi.w #$4290,$68c24
 bne.w .bad
 cmpi.w #$2040,$68c26
 bne.w .bad
 cmpi.w #$d1fc,$68c28
 bne.w .bad
 cmpi.w #$0006,$68c2a
 bne.w .bad
 cmpi.w #$a60a,$68c2c
 bne.w .bad
 cmpi.w #$202e,$68d0e
 bne.w .bad
 cmpi.w #$fff6,$68d10
 bne.w .bad
 cmpi.w #$d091,$68d12
 bne.w .bad
 cmpi.w #$2080,$68d14
 bne.w .bad
 lea heading_67280(pc),a0
 move.w #$4ef9,$67280
 move.l a0,$67282
 lea heading_6860e(pc),a0
 move.w #$4ef9,$6860e
 move.l a0,$68610
 lea heading_678de(pc),a0
 move.w #$4ef9,$678de
 move.l a0,$678e0
 lea heading_67900(pc),a0
 move.w #$4ef9,$67900
 move.l a0,$67902
 lea heading_67948(pc),a0
 move.w #$4ef9,$67948
 move.l a0,$6794a
 lea heading_67976(pc),a0
 move.w #$4ef9,$67976
 move.l a0,$67978
 lea heading_67320(pc),a0
 move.w #$4ef9,$67320
 move.l a0,$67322
 move.w #$4e71,$67326
 move.w #$4e71,$67328
 move.w #$4e71,$6732a
 lea heading_683ac(pc),a0
 move.w #$4ef9,$683ac
 move.l a0,$683ae
 move.w #$4e71,$683b2
 move.w #$4e71,$683b4
 move.w #$4e71,$683b6
 lea heading_69590(pc),a0
 move.w #$4ef9,$69590
 move.l a0,$69592
 lea heading_695e8(pc),a0
 move.w #$4ef9,$695e8
 move.l a0,$695ea
 lea heading_68a5e(pc),a0
 move.w #$4ef9,$68a5e
 move.l a0,$68a60
 lea heading_68c24(pc),a0
 move.w #$4ef9,$68c24
 move.l a0,$68c26
 move.w #$4e71,$68c2a
 move.w #$4e71,$68c2c
 lea heading_68d0e(pc),a0
 move.w #$4ef9,$68d0e
 move.l a0,$68d10
 move.w #$4e71,$68d14
 lea heading_installed(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #15,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
heading_67280:
 dc.w $23d0,$0003,$2fb8
C4SaveMask048 equ *
 movem.l a0/a1/d0/d1/d2/d4/d7,-(sp)
 move.w sr,-(sp)
 move.l d0,d4
 bsr.w heading_context
 bsr.w heading_sync
 move.w (sp)+,ccr
C4SaveMask049 equ *
 movem.l (sp)+,a0/a1/d0/d1/d2/d4/d7
 jmp $67286
heading_6860e:
 dc.w $20b9,$0003,$2fb8
C4SaveMask050 equ *
 movem.l a0/a1/d0/d1/d2/d4/d7,-(sp)
 move.w sr,-(sp)
 move.l d0,d4
 bsr.w heading_context
 bsr.w heading_sync
 move.w (sp)+,ccr
C4SaveMask051 equ *
 movem.l (sp)+,a0/a1/d0/d1/d2/d4/d7
 jmp $68614
heading_678de:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d4
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_step_a
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $678e4
heading_67900:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d4
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_step_b
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $67906
heading_67948:
C4SaveMask052 equ *
 movem.l a0/a2/a3/d0/d1/d2/d4/d5/d7,-(sp)
 move.w sr,-(sp)
 move.l d0,d4
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_step_a
 move.w (sp)+,ccr
C4SaveMask053 equ *
 movem.l (sp)+,a0/a2/a3/d0/d1/d2/d4/d5/d7
 jmp $6794e
heading_67976:
C4SaveMask054 equ *
 movem.l a0/a2/a3/d0/d1/d2/d4/d5/d7,-(sp)
 move.w sr,-(sp)
 move.l d0,d4
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_step_b
 move.w (sp)+,ccr
C4SaveMask055 equ *
 movem.l (sp)+,a0/a2/a3/d0/d1/d2/d4/d5/d7
 jmp $6797c
heading_67320:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d4
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_zero
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6732c
heading_683ac:
C4SaveMask056 equ *
 movem.l a0/d0/d1/d4/d7,-(sp)
 move.w sr,-(sp)
 move.l d0,d4
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_zero
 move.w (sp)+,ccr
C4SaveMask057 equ *
 movem.l (sp)+,a0/d0/d1/d4/d7
 jmp $683b8
heading_69590:
 dc.w $23c0,$0003,$2fb4
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d4
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_reset_a
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69596
heading_695e8:
 dc.w $23c0,$0003,$2fb8
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d4
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_reset_b
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $695ee
heading_68a5e:
 dc.w $4290,$202f,$0000
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d4
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_reset_a
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68a64
heading_68c24:
 dc.w $4290,$2040,$d1fc,$0006,$a60a
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d4
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_reset_a
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68c2e
heading_68d0e:
 dc.w $202e,$fff6,$d091,$2080
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d4
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_assign_b
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68d16
heading_context:
 moveq #0,d0
 move.w $32fbc,d0
 cmpi.w #7,d0
 bhi.w fine_fault

 mulu.w #12,d0
 lea heading_shadow(pc),a0
 adda.l d0,a0
 rts
heading_sync:
 move.l $32fb4,(a0)
 move.l $32fb8,6(a0)
 rts
heading_step_a:
 moveq #0,d5
 bra.b heading_step
heading_step_b:
 moveq #1,d5
 addq.l #6,a0
heading_step:
 move.l a0,a3
 lea $32fb4,a2
 tst.w d5
 beq.b .axis_ready
 addq.l #4,a2
.axis_ready:
 move.l (a2),(a0)
 move.l d4,d0
 bsr.w FF1Heading20
 tst.l d1
 bne.w fine_fault

 move.l (a0),(a2)
 rts
heading_zero:
 bsr.w heading_sync
 bsr.w FF1HeadingZeroRelative
 move.l (a0),$32fb4
 move.l 6(a0),$32fb8
 rts
heading_reset_a:
 ; Cold array resets write zero; recovery writes -4<<16. Read the authoritative
 ; per-car relative array rather than stale shared scratch on cold paths.
 moveq #0,d0
 move.w $32fbc,d0
 lsl.l #2,d0
 lea $2278a,a1
 move.l (a1,d0.l),d0
 bsr.w FF1HeadingReset
 rts
heading_reset_b:
 addq.l #6,a0
 move.l $32fb8,d0
 bsr.w FF1HeadingReset
 rts
heading_assign_b:
 move.l a0,a1
 addq.l #6,a0
 moveq #0,d0
 move.w $32fbc,d0
 lsl.l #2,d0
 lea $227aa,a2
 move.l (a2,d0.l),d0
 bsr.w FF1HeadingAssign
 rts
heading_installed: dc.l 0
heading_steps: dc.l 0
heading_zeroes: dc.l 0
heading_resets: dc.l 0
heading_assignments: dc.l 0
heading_shadow: ds.b 96
install_steering:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #7,d0
 blo.w .done
 cmpi.w #$d240,$6773c
 bne.w .bad
 cmpi.w #$e241,$6773e
 bne.w .bad
 cmpi.w #$3081,$67740
 bne.w .bad
 cmpi.w #$7000,$68788
 bne.w .bad
 cmpi.w #$3080,$6878a
 bne.w .bad
 cmpi.w #$4a79,$6878c
 bne.w .bad
 cmpi.w #$0001,$6878e
 bne.w .bad
 cmpi.w #$c222,$68790
 bne.w .bad
 lea steering_6773c(pc),a0
 move.w #$4ef9,$6773c
 move.l a0,$6773e
 lea steering_68788(pc),a0
 move.w #$4ef9,$68788
 move.l a0,$6878a
 move.w #$4e71,$6878e
 move.w #$4e71,$68790
 lea steering_shadow(pc),a0
 lea $32f7a,a1
 move.l ticks(pc),d3
 subq.l #1,d3
 moveq #7,d7
.init:
 move.w (a1)+,d0
 bsr.w FF1SteeringReset
 adda.w #18,a0
 dbra d7,.init
 lea steering_installed(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #27,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
steering_6773c:
 move.w sr,-(sp)
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 beq.b .fine
 move.w (sp)+,ccr
 dc.w $d240,$e241,$3081
 jmp $67742
.fine:
 move.w (sp)+,ccr
C4SaveMask058 equ *
 movem.l a0/a5/d0/d1/d2/d3/d4/d5/d6/d7,-(sp)
 move.w sr,-(sp)
 move.l d0,d4
 move.l a0,a5
 bsr.w steering_sample
 move.w (sp)+,ccr
C4SaveMask059 equ *
 movem.l (sp)+,a0/a5/d0/d1/d2/d3/d4/d5/d6/d7
 jmp $67742
steering_68788:
 dc.w $7000,$3080,$4a79,$0001,$c222
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w steering_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68792
steering_context:
 moveq #0,d0
 move.w $32fbc,d0
 cmpi.w #7,d0
 bhi.w velocity_fault

 mulu.w #18,d0
 lea steering_shadow(pc),a0
 adda.l d0,a0
 rts
steering_sample:
 FF1PlayerContext steering_shadow,steering_context
 move.l ticks(pc),d3
 move.w d4,d0
 bsr.w FF1SteeringSample20
 tst.l d1
 bne.w velocity_fault

 move.w d0,12(sp)
 move.w d0,(a5)
 move.w sr,d5
 andi.w #15,d5
 move.w d4,d6
 add.w d2,d6
 andi.w #1,d6
 lsl.w #4,d6
 or.w d6,d5
 andi.w #$ffe0,4(sp)
 or.w d5,4(sp)
 rts
steering_reset:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 FF1PlayerContext steering_shadow,steering_context
 moveq #0,d0
 move.l ticks(pc),d3
 subq.l #1,d3
 bsr.w FF1SteeringReset
.done:
 rts
steering_installed: dc.l 0
steering_samples: dc.l 0
steering_resets: dc.l 0
steering_shadow: ds.b 144
install_wear:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #7,d0
 blo.w .done
 cmpi.w #$4eb9,$6de74
 bne.w .bad
 cmpi.w #$0002,$6de76
 bne.w .bad
 cmpi.w #$9500,$6de78
 bne.w .bad
 cmpi.w #$4eb9,$6defa
 bne.w .bad
 cmpi.w #$0002,$6defc
 bne.w .bad
 cmpi.w #$9500,$6defe
 bne.w .bad
 cmpi.w #$2236,$6de96
 bne.w .bad
 cmpi.w #$08d8,$6de98
 bne.w .bad
 cmpi.w #$9390,$6de9a
 bne.w .bad
 cmpi.w #$2236,$6ded4
 bne.w .bad
 cmpi.w #$08d8,$6ded6
 bne.w .bad
 cmpi.w #$9390,$6ded8
 bne.w .bad
 cmpi.w #$2236,$6df2a
 bne.w .bad
 cmpi.w #$08d8,$6df2c
 bne.w .bad
 cmpi.w #$e381,$6df2e
 bne.w .bad
 cmpi.w #$9390,$6df30
 bne.w .bad
 cmpi.w #$9190,$6e018
 bne.w .bad
 cmpi.w #$2041,$6e01a
 bne.w .bad
 cmpi.w #$d1fc,$6e01c
 bne.w .bad
 cmpi.w #$0002,$6e01e
 bne.w .bad
 cmpi.w #$2356,$6e020
 bne.w .bad
 cmpi.w #$2080,$64b4c
 bne.w .bad
 cmpi.w #$52ae,$64b4e
 bne.w .bad
 cmpi.w #$fffc,$64b50
 bne.w .bad
 cmpi.w #$223c,$687f4
 bne.w .bad
 cmpi.w #$00ff,$687f6
 bne.w .bad
 cmpi.w #$0000,$687f8
 bne.w .bad
 cmpi.w #$20bc,$6c67c
 bne.w .bad
 cmpi.w #$00ff,$6c67e
 bne.w .bad
 cmpi.w #$0000,$6c680
 bne.w .bad
 lea wear_6de74(pc),a0
 move.w #$4ef9,$6de74
 move.l a0,$6de76
 lea wear_6defa(pc),a0
 move.w #$4ef9,$6defa
 move.l a0,$6defc
 lea wear_6de96(pc),a0
 move.w #$4ef9,$6de96
 move.l a0,$6de98
 lea wear_6ded4(pc),a0
 move.w #$4ef9,$6ded4
 move.l a0,$6ded6
 lea wear_6df2a(pc),a0
 move.w #$4ef9,$6df2a
 move.l a0,$6df2c
 move.w #$4e71,$6df30
 lea wear_6e018(pc),a0
 move.w #$4ef9,$6e018
 move.l a0,$6e01a
 move.w #$4e71,$6e01e
 move.w #$4e71,$6e020
 lea wear_64b4c(pc),a0
 move.w #$4ef9,$64b4c
 move.l a0,$64b4e
 lea wear_687f4(pc),a0
 move.w #$4ef9,$687f4
 move.l a0,$687f6
 lea wear_6c67c(pc),a0
 move.w #$4ef9,$6c67c
 move.l a0,$6c67e
 lea wear_installed(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #28,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
wear_6de74:
 dc.w $4eb9,$0002,$9500
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d4
 move.l #$6de74,d6
 moveq #6,d7
 bsr.w wear_sample
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6de7a
wear_6defa:
 dc.w $4eb9,$0002,$9500
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d4
 move.l #$6defa,d6
 moveq #6,d7
 bsr.w wear_sample
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6df00
wear_6de96:
 dc.w $2236,$08d8
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d1,d4
 move.l #$6de96,d6
 moveq #10,d7
 bsr.w wear_sample
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $9390
 jmp $6de9c
wear_6ded4:
 dc.w $2236,$08d8
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d1,d4
 move.l #$6ded4,d6
 moveq #10,d7
 bsr.w wear_sample
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $9390
 jmp $6deda
wear_6df2a:
 dc.w $2236,$08d8,$e381
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d1,d4
 move.l #$6df2a,d6
 moveq #10,d7
 bsr.w wear_sample
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $9390
 jmp $6df32
wear_6e018:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d4
 move.l #$6e018,d6
 moveq #6,d7
 bsr.w wear_sample
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $9190,$2041,$d1fc,$0002,$2356
 jmp $6e022
wear_64b4c:
 dc.w $2080
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w wear_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $52ae,$fffc
 jmp $64b52
wear_687f4:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w wear_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $223c,$00ff,$0000
 jmp $687fa
wear_6c67c:
 dc.w $20bc,$00ff,$0000
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w wear_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6c682
wear_context:
 move.l a0,d2
 subi.l #$66c52,d2
 cmpi.l #16,d2
 blo.b .player
 move.l a0,d2
 subi.l #$22356,d2
 cmpi.l #32,d2
 bhs.w velocity_fault

 addi.l #16,d2
.player:
 move.l d2,d3
 andi.l #3,d3
 bne.w velocity_fault

 lsr.l #1,d2
 lea wear_remainders(pc),a1
 adda.l d2,a1
 rts
wear_reset:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 bsr.w wear_context
 clr.w (a1)
.done:
 rts
wear_sample:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 bsr.w wear_context
 move.l d4,d0
 bsr.w FF1Wear20Delta
 tst.l d1
 bne.w velocity_fault

 move.l d0,(sp,d7.l)
.done:
 rts
wear_installed: dc.l 0
wear_samples: dc.l 0
wear_resets: dc.l 0
wear_remainders: ds.w 12
install_fuel:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #7,d0
 blo.w .done
 cmpi.w #$9190,$6d164
 bne.w .bad
 cmpi.w #$2d40,$6d166
 bne.w .bad
 cmpi.w #$fffc,$6d168
 bne.w .bad
 cmpi.w #$23c0,$64ae6
 bne.w .bad
 cmpi.w #$0002,$64ae8
 bne.w .bad
 cmpi.w #$2376,$64aea
 bne.w .bad
 cmpi.w #$c1fc,$6881e
 bne.w .bad
 cmpi.w #$2710,$68820
 bne.w .bad
 cmpi.w #$2080,$68822
 bne.w .bad
 cmpi.w #$c1fc,$6c6a2
 bne.w .bad
 cmpi.w #$2710,$6c6a4
 bne.w .bad
 cmpi.w #$2080,$6c6a6
 bne.w .bad
 cmpi.w #$d1fc,$66942
 bne.w .bad
 cmpi.w #$0002,$66944
 bne.w .bad
 cmpi.w #$2376,$66946
 bne.w .bad
 cmpi.w #$4290,$66948
 bne.w .bad
 cmpi.w #$d1fc,$6d242
 bne.w .bad
 cmpi.w #$0002,$6d244
 bne.w .bad
 cmpi.w #$2376,$6d246
 bne.w .bad
 cmpi.w #$4290,$6d248
 bne.w .bad
 lea fuel_6d164(pc),a0
 move.w #$4ef9,$6d164
 move.l a0,$6d166
 lea fuel_64ae6(pc),a0
 move.w #$4ef9,$64ae6
 move.l a0,$64ae8
 lea fuel_6881e(pc),a0
 move.w #$4ef9,$6881e
 move.l a0,$68820
 lea fuel_6c6a2(pc),a0
 move.w #$4ef9,$6c6a2
 move.l a0,$6c6a4
 lea fuel_66942(pc),a0
 move.w #$4ef9,$66942
 move.l a0,$66944
 move.w #$4e71,$66948
 lea fuel_6d242(pc),a0
 move.w #$4ef9,$6d242
 move.l a0,$6d244
 move.w #$4e71,$6d248
 lea fuel_installed(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #32,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
fuel_6d164:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d4
 move.l #$6d164,d6
 moveq #6,d7
 bsr.w fuel_sample
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $9190,$2d40,$fffc
 jmp $6d16a
fuel_64ae6:
 dc.w $23c0,$0002,$2376
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 lea $22376,a0
 bsr.w fuel_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $64aec
fuel_6881e:
 dc.w $c1fc,$2710,$2080
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w fuel_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68824
fuel_6c6a2:
 dc.w $c1fc,$2710,$2080
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w fuel_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6c6a8
fuel_66942:
 dc.w $d1fc,$0002,$2376,$4290
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w fuel_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6694a
fuel_6d242:
 dc.w $d1fc,$0002,$2376,$4290
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w fuel_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6d24a
fuel_context:
 move.l a0,d2
 subi.l #$22376,d2
 cmpi.l #32,d2
 bhs.w velocity_fault

 move.l d2,d3
 andi.l #3,d3
 bne.w velocity_fault

 lsr.l #1,d2
 lea fuel_remainders(pc),a1
 adda.l d2,a1
 rts
fuel_reset:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 bsr.w fuel_context
 clr.w (a1)
.done:
 rts
fuel_sample:
 move.w modeval(pc),-(sp)
 cmpi.w #8,(sp)+
 bne.b .done
 bsr.w fuel_context
 move.l d4,d0
 bsr.w FF1Wear20Delta
 tst.l d1
 bne.w velocity_fault

 move.l d0,(sp,d7.l)
.done:
 rts
fuel_installed: dc.l 0
fuel_samples: dc.l 0
fuel_resets: dc.l 0
fuel_remainders: ds.w 8

C4WeightedSpeedRate:
 lea speed_work(pc),a0
 move.w C4PhaseWeight(pc),d1
 bsr.w FF1SpeedRatePulses200
 tst.l d1
 bne.w velocity_fault
 move.w (a0),d0
 ext.l d0
 move.w d0,$32fbe
 rts
