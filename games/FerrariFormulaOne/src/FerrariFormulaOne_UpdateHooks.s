; Host code size is supplied by relocated-loader builds; legacy default exact.
 ifnd FF1_HOST_CODE_SIZE
FF1_HOST_CODE_SIZE equ 5440
 endc
; VERIFY capacity may be reduced by an isolated capture build to fit Chip RAM.
; Allocation and overflow guard always share this value; default ABI is unchanged.
 IFND FF1_SPEED_RECORD_CAPACITY
FF1_SPEED_RECORD_CAPACITY equ 4096
 ENDC
; Ferrari Formula One, SPS 0481: candidate 68020 update hooks.
; S2 VERIFY split. Not included by FerrariFormulaOne_WHD.s; default-off.
; FF1_PLAYER_HOOKS requires FF1_PLAN_B and consolidates player state/hooks.
; FF1_PLAN_B selects player-only conversion with native opponent updates.
; The ordinary slave does not activate this candidate scheduling policy.
;
; Include with Games on the assembler include path, after the host's native
; patch/entry plumbing and data symbols: start, modeval, installed, error,
; ticks, cache_api, cache_old, cache_called, candidate. The host installs the
; hooks at its accepted race-loop boundary and calls schedule_begin/end.
; Emit FF1UpdateWorkspace once after code and other host data.
;
; Define VERIFY to retain the accepted record format, snapshots, counters and
; assertions. Otherwise only functional contexts and 80 bytes of velocity
; scratch are used. Do not remove the scratch: offsets 2, 20..79 carry angle,
; projection, body response, fractional velocity and feedback between hooks.
; Simulation serials, remainders, saved contact positions and scheduler debt
; remain live in both builds. Install-time signature checks remain mandatory.
; CCR saves here require 68020; do not install these hooks on a 68000.
;
; Local startup controls, captures and build harness remain under tmp/dev.
; No game data, ROMs or captured state is included in this source.

 IFD FF1_PLAYER_HOOKS
 IFND FF1_PLAN_B
 fail "FF1_PLAYER_HOOKS requires FF1_PLAN_B"
 ENDC
 IFND VERIFY
FF1_LEAN_PLAYER equ 1
 ENDC
 ENDC

; B4 is the mode-8 player path only. Its native opponent guards precede these
; callbacks. VERIFY retains the broad trace ABI; lean saves each callback's
; clobbered registers. D0/D1 remain first when a callback returns through the
; saved frame. Component helpers keep their original arithmetic contracts.
FF1PlayerContext macro
 IFD FF1_PLAYER_HOOKS
 lea (\1.l,pc),a0
 moveq #0,d0
 ELSE
 bsr.w \2
 ENDC
 endm
FF1PlayerSave macro
 IFD FF1_LEAN_PLAYER
 movem.l \1,-(sp)
 ELSE
 movem.l d0-d7/a0-a6,-(sp)
 ENDC
 endm
FF1PlayerRestore macro
 IFD FF1_LEAN_PLAYER
 movem.l (sp)+,\1
 ELSE
 movem.l (sp)+,d0-d7/a0-a6
 ENDC
 endm

FF1UpdateWorkspace macro
 IFND VERIFY
velocity_scratch equ velocity_records
 ENDC
 IFD VERIFY
velocity_records: ds.b 64000
 ELSE
velocity_records: ds.b 80
 ENDC
 IFD VERIFY
velocity_target_speeds: ds.l 800
 ELSE
velocity_target_speeds: ds.b 0
 ENDC
 IFD VERIFY
speed_records: ds.b FF1_SPEED_RECORD_CAPACITY*32
 ELSE
speed_records: ds.b 0
 ENDC
 IFD VERIFY
speed_feedback_records: ds.b 6400
 ELSE
speed_feedback_records: ds.b 0
 ENDC
 IFD VERIFY
fine_records: ds.b 25600
 ELSE
fine_records: ds.b 0
 ENDC
 IFD VERIFY
heading_records: ds.b 38400
 ELSE
heading_records: ds.b 0
 ENDC
 IFD VERIFY
position_velocity_inputs: ds.b 9600
 ELSE
position_velocity_inputs: ds.b 0
 ENDC
 IFD VERIFY
steering_records: ds.b 16000
 ELSE
steering_records: ds.b 0
 ENDC
 IFD VERIFY
wear_records: ds.b 131072
 ELSE
wear_records: ds.b 0
 ENDC
 IFD VERIFY
events_records: ds.b 128000
 ELSE
events_records: ds.b 0
 ENDC
 IFD VERIFY
clocks_records: ds.b 6400
 ELSE
clocks_records: ds.b 0
 ENDC
 IFD VERIFY
counters_records: ds.b 6400
 ELSE
counters_records: ds.b 0
 ENDC
 IFD VERIFY
fuel_records: ds.b 131072
 ELSE
fuel_records: ds.b 0
 ENDC
 IFD VERIFY
boost_records: ds.b 4800
 ELSE
boost_records: ds.b 0
 ENDC
 IFD VERIFY
recovery_contact_records: ds.b 12800
 ELSE
recovery_contact_records: ds.b 0
 ENDC
 IFD VERIFY
recovery_records: ds.b 25600
 ELSE
recovery_records: ds.b 0
 ENDC
 IFD VERIFY
schedule_records: ds.b 3200
 ELSE
schedule_records: ds.b 0
 ENDC
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
 IFND FF1_PLAYER_HOOKS
 lea (velocity_671e6.l,pc),a0
 move.w #$4ef9,$671e6
 move.l a0,$671e8
 ENDC
 IFND FF1_PLAYER_HOOKS
 lea (velocity_685a6.l,pc),a0
 move.w #$4ef9,$685a6
 move.l a0,$685a8
 ENDC
 lea (velocity_67bcc.l,pc),a0
 move.w #$4ef9,$67bcc
 move.l a0,$67bce
 move.w #$4e71,$67bd2
 lea (velocity_6dc96.l,pc),a0
 move.w #$4ef9,$6dc96
 move.l a0,$6dc98
 lea (velocity_6dd44.l,pc),a0
 move.w #$4ef9,$6dd44
 move.l a0,$6dd46
 lea (velocity_6e084.l,pc),a0
 move.w #$4ef9,$6e084
 move.l a0,$6e086
 lea (velocity_6e2ae.l,pc),a0
 move.w #$4ef9,$6e2ae
 move.l a0,$6e2b0
 move.w #$4e71,$6e2b4
 lea (velocity_68990.l,pc),a0
 move.w #$4ef9,$68990
 move.l a0,$68992
 lea (velocity_689a0.l,pc),a0
 move.w #$4ef9,$689a0
 move.l a0,$689a2
 lea (velocity_68b98.l,pc),a0
 move.w #$4ef9,$68b98
 move.l a0,$68b9a
 lea (velocity_68baa.l,pc),a0
 move.w #$4ef9,$68baa
 move.l a0,$68bac
 move.w #$4e71,$68bb0
 lea (velocity_6e95e.l,pc),a0
 move.w #$4ef9,$6e95e
 move.l a0,$6e960
 move.w #$4e71,$6e964
 move.w #$4e71,$6e966
 lea (velocity_6e968.l,pc),a0
 move.w #$4ef9,$6e968
 move.l a0,$6e96a
 lea (velocity_6917a.l,pc),a0
 move.w #$4ef9,$6917a
 move.l a0,$6917c
 lea (velocity_68386.l,pc),a0
 move.w #$4ef9,$68386
 move.l a0,$68388
 lea (velocity_6e2a4.l,pc),a0
 move.w #$4ef9,$6e2a4
 move.l a0,$6e2a6
 lea (velocity_6e2ec.l,pc),a0
 move.w #$4ef9,$6e2ec
 move.l a0,$6e2ee
 lea (velocity_69b36.l,pc),a0
 move.w #$4ef9,$69b36
 move.l a0,$69b38
 lea (velocity_69b50.l,pc),a0
 move.w #$4ef9,$69b50
 move.l a0,$69b52
 lea (velocity_6ee00.l,pc),a0
 move.w #$4ef9,$6ee00
 move.l a0,$6ee02
 lea (velocity_6ee16.l,pc),a0
 move.w #$4ef9,$6ee16
 move.l a0,$6ee18
 move.w #$4e71,$6ee1c
 lea (velocity_6993a.l,pc),a0
 move.w #$4ef9,$6993a
 move.l a0,$6993c
 lea (velocity_69a0a.l,pc),a0
 move.w #$4ef9,$69a0a
 move.l a0,$69a0c
 lea (velocity_6998e.l,pc),a0
 move.w #$4ef9,$6998e
 move.l a0,$69990
 lea (velocity_69a5e.l,pc),a0
 move.w #$4ef9,$69a5e
 move.l a0,$69a60
 IFND FF1_PLAYER_HOOKS
 lea (velocity_68576.l,pc),a0
 move.w #$4ef9,$68576
 move.l a0,$68578
 ENDC
 lea (velocity_6897e.l,pc),a0
 move.w #$4ef9,$6897e
 move.l a0,$68980
 lea (velocity_68b84.l,pc),a0
 move.w #$4ef9,$68b84
 move.l a0,$68b86
 lea (velocity_672f0.l,pc),a0
 move.w #$4ef9,$672f0
 move.l a0,$672f2
 lea (velocity_673fc.l,pc),a0
 move.w #$4ef9,$673fc
 move.l a0,$673fe
 lea (velocity_67426.l,pc),a0
 move.w #$4ef9,$67426
 move.l a0,$67428
 lea (velocity_67438.l,pc),a0
 move.w #$4ef9,$67438
 move.l a0,$6743a
 lea (velocity_6744a.l,pc),a0
 move.w #$4ef9,$6744a
 move.l a0,$6744c
 lea (velocity_67476.l,pc),a0
 move.w #$4ef9,$67476
 move.l a0,$67478
 lea (velocity_675c0.l,pc),a0
 move.w #$4ef9,$675c0
 move.l a0,$675c2
 lea (velocity_6766c.l,pc),a0
 move.w #$4ef9,$6766c
 move.l a0,$6766e
 lea (velocity_6768e.l,pc),a0
 move.w #$4ef9,$6768e
 move.l a0,$67690
 lea (velocity_676e0.l,pc),a0
 move.w #$4ef9,$676e0
 move.l a0,$676e2
 lea (velocity_69970.l,pc),a0
 move.w #$4ef9,$69970
 move.l a0,$69972
 lea (velocity_69a42.l,pc),a0
 move.w #$4ef9,$69a42
 move.l a0,$69a44
 IFND FF1_PLAYER_HOOKS
 lea (velocity_6721c.l,pc),a0
 move.w #$4ef9,$6721c
 move.l a0,$6721e
 ENDC
 IFND FF1_LEAN_PLAYER
 lea (velocity_679fe.l,pc),a0
 move.w #$4ef9,$679fe
 move.l a0,$67a00
 ENDC
 lea (velocity_6838c.l,pc),a0
 move.w #$4ef9,$6838c
 move.l a0,$6838e
 lea (velocity_694ce.l,pc),a0
 move.w #$4ef9,$694ce
 move.l a0,$694d0
 move.w #$4e71,$694d4
 lea (velocity_69b30.l,pc),a0
 move.w #$4ef9,$69b30
 move.l a0,$69b32
 lea (velocity_69b4a.l,pc),a0
 move.w #$4ef9,$69b4a
 move.l a0,$69b4c
 lea $2275a,a0
 lea (speed_shadow.l,pc),a1
 IFD FF1_PLAYER_HOOKS
 moveq #0,d0
 ELSE
 moveq #7,d0
 ENDC
.init_speed:
 move.w (a0)+,(a1)+
 clr.w (a1)+
 clr.w (a1)+
 dbra d0,.init_speed
 lea (velocity_installed.l,pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea (error.l,pc),a0
 move.l #16,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
velocity_671e6:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33d0,$0003,$2f96
 jmp $671ec
.b3_player:
 ENDC
 dc.w $33d0,$0003,$2f96
 FF1PlayerSave d0-d2/a0-a1
 move.w ccr,-(sp)
 IFND FF1_LEAN_PLAYER
 move.l d0,d7
 ENDC
 bsr.w velocity_load
 move.w (sp)+,ccr
 FF1PlayerRestore d0-d2/a0-a1
 jmp $671ec
velocity_685a6:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $30b9,$0003,$2f96
 jmp $685ac
.b3_player:
 ENDC
 dc.w $30b9,$0003,$2f96
 FF1PlayerSave d0/a0
 move.w ccr,-(sp)
 IFND FF1_LEAN_PLAYER
 move.l d0,d7
 ENDC
 bsr.w velocity_store
 move.w (sp)+,ccr
 FF1PlayerRestore d0/a0
 jmp $685ac
velocity_67bcc:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33ee,$fff2,$0003,$2f94
 jmp $67bd4
.b3_player:
 ENDC
 dc.w $33ee,$fff2,$0003,$2f94
 FF1PlayerSave d0-d2/a0-a2
 move.w ccr,-(sp)
 IFND FF1_LEAN_PLAYER
 move.l d0,d7
 ENDC
 bsr.w velocity_rotate
 move.w (sp)+,ccr
 FF1PlayerRestore d0-d2/a0-a2
 jmp $67bd4
velocity_6dc96:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $3039,$0003,$2f94
 jmp $6dc9c
.b3_player:
 ENDC
 dc.w $3039,$0003,$2f94
 FF1PlayerSave d0-d2/a0-a2/a4
 move.w ccr,-(sp)
 IFND FF1_LEAN_PLAYER
 move.l d0,d7
 ENDC
 bsr.w velocity_project
 move.w (sp)+,ccr
 FF1PlayerRestore d0-d2/a0-a2/a4
 jmp $6dc9c
velocity_6dd44:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $3239,$0003,$2fbc
 jmp $6dd4a
.b3_player:
 ENDC
 dc.w $3239,$0003,$2fbc
 FF1PlayerSave d0-d1/d7/a4
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_raw
 move.w (sp)+,ccr
 FF1PlayerRestore d0-d1/d7/a4
 jmp $6dd4a
velocity_6e084:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $3039,$0003,$2fbc
 jmp $6e08a
.b3_player:
 ENDC
 dc.w $3039,$0003,$2fbc
 FF1PlayerSave d0-d2/a4
 move.w ccr,-(sp)
 IFND FF1_LEAN_PLAYER
 move.l d0,d7
 ENDC
 bsr.w velocity_limit
 move.w (sp)+,ccr
 FF1PlayerRestore d0-d2/a4
 jmp $6e08a
velocity_6e2ae:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $302e,$000e
 dc.w $4cdf,$000c
 jmp $6e2b6
.b3_player:
 ENDC
 dc.w $302e,$000e,$4cdf,$000c
 FF1PlayerSave d0-d2/a0-a2/a4
 move.w ccr,-(sp)
 IFND FF1_LEAN_PLAYER
 move.l d0,d7
 ENDC
 bsr.w velocity_returned
 move.w (sp)+,ccr
 FF1PlayerRestore d0-d2/a0-a2/a4
 jmp $6e2b6
velocity_68990:
 IFD FF1_PLAN_B
 cmpa.l #$6f13c,a0
 beq.b .b3_player
 dc.w $3080
 dc.w $202f,$0000
 jmp $68996
.b3_player:
 ENDC
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_cold_x
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $3080,$202f,$0000
 jmp $68996
velocity_689a0:
 IFD FF1_PLAN_B
 cmpa.l #$6f14c,a0
 beq.b .b3_player
 dc.w $4250
 dc.w $206f,$0000
 jmp $689a6
.b3_player:
 ENDC
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_cold_z
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $4250,$206f,$0000
 jmp $689a6
velocity_68b98:
 IFD FF1_PLAN_B
 cmpa.l #$6f13c,a0
 beq.b .b3_player
 dc.w $3081
 dc.w $322f,$0000
 jmp $68b9e
.b3_player:
 ENDC
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_cold_x
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $3081,$322f,$0000
 jmp $68b9e
velocity_68baa:
 IFD FF1_PLAN_B
 cmpa.l #$6f14c,a0
 beq.b .b3_player
 dc.w $30bc,$00c8
 dc.w $4a6f,$0000
 jmp $68bb2
.b3_player:
 ENDC
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_cold_z200
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $30bc,$00c8,$4a6f,$0000
 jmp $68bb2
velocity_6e95e:
 IFD FF1_PLAN_B
 cmpa.l #$6f13c,a0
 beq.b .b3_player
 dc.w $3081
 dc.w $2040
 dc.w $d1fc,$0006,$f14c
 jmp $6e968
.b3_player:
 ENDC
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_cold_x
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $3081,$2040,$d1fc,$0006,$f14c
 jmp $6e968
velocity_6e968:
 IFD FF1_PLAN_B
 cmpa.l #$6f14c,a0
 beq.b .b3_player
 dc.w $3081
 dc.w $202e,$fffc
 jmp $6e96e
.b3_player:
 ENDC
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_cold_z
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $3081,$202e,$fffc
 jmp $6e96e
velocity_6917a:
 IFD FF1_PLAN_B
 tst.w -6(a6)
 beq.b .b3_player
 dc.w $3084,$3d44,$fff6
 jmp $69180
.b3_player:
 ENDC
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_swap_z
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $3084,$3d44,$fff6
 jmp $69180
velocity_68386:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2f94
 jmp $6838c
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2f94
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_reset_work
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6838c
velocity_6e2a4:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2f96
 jmp $6e2aa
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2f96
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_reset_work
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6e2aa
velocity_6e2ec:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2f96
 jmp $6e2f2
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2f96
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_reset_work
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6e2f2
velocity_69b36:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2f96
 jmp $69b3c
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2f96
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_clamp_z
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69b3c
velocity_69b50:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2f96
 jmp $69b56
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2f96
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_clamp_z
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69b56
velocity_6ee00:
 IFD FF1_PLAN_B
 cmpa.l #$6f13c,a0
 beq.b .b3_player
 dc.w $3081
 dc.w $322e,$000e
 jmp $6ee06
.b3_player:
 ENDC
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_impulse_x
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $3081,$322e,$000e
 jmp $6ee06
velocity_6ee16:
 IFD FF1_PLAN_B
 cmpa.l #$6f13c,a0
 beq.b .b3_player
 dc.w $3081
 dc.w $0c6e,$00c8,$0012
 jmp $6ee1e
.b3_player:
 ENDC
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_impulse_x
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $3081,$0c6e,$00c8,$0012
 jmp $6ee1e
velocity_6993a:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2f94
 jmp $69940
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2f94
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_offroad_right
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69940
velocity_69a0a:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2f94
 jmp $69a10
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2f94
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_offroad_left
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69a10
velocity_6998e:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c1,$0003,$2f96
 jmp $69994
.b3_player:
 ENDC
 dc.w $33c1,$0003,$2f96
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_offroad_z
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69994
velocity_69a5e:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c1,$0003,$2f96
 jmp $69a64
.b3_player:
 ENDC
 dc.w $33c1,$0003,$2f96
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_offroad_z
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69a64
velocity_68576:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $30b9,$0003,$2fbe
 jmp $6857c
.b3_player:
 ENDC
 dc.w $30b9,$0003,$2fbe
 FF1PlayerSave d0/a0-a1
 move.w ccr,-(sp)
 IFND FF1_LEAN_PLAYER
 move.l d0,d7
 ENDC
 bsr.w velocity_speed_store
 move.w (sp)+,ccr
 FF1PlayerRestore d0/a0-a1
 jmp $6857c
velocity_6897e:
 IFD FF1_PLAN_B
 cmpa.l #$2275a,a0
 beq.b .b3_player
 dc.w $3080
 dc.w $202f,$0000
 jmp $68984
.b3_player:
 ENDC
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_cold
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $3080,$202f,$0000
 jmp $68984
velocity_68b84:
 IFD FF1_PLAN_B
 cmpa.l #$2275a,a0
 beq.b .b3_player
 dc.w $3080
 dc.w $302f,$0000
 jmp $68b8a
.b3_player:
 ENDC
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_cold
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $3080,$302f,$0000
 jmp $68b8a
velocity_672f0:
 IFD FF1_LEAN_PLAYER
 tst.w $32fbc
 bne.b .native
 move.w d0,$32fbe
 movem.l d1/a0,-(sp)
 move.w ccr,-(sp)
 lea speed_work(pc),a0
 bsr.w FF1SpeedRate20
 move.w (a0),d0
 ext.l d0
 move.w d0,$32fbe
 move.w (sp)+,ccr
 movem.l (sp)+,d1/a0
 jmp $672f6
.native:
 move.w d0,$32fbe
 jmp $672f6
 ELSE
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2fbe
 jmp $672f6
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_672f0
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $672f6
 ENDC
velocity_673fc:
 IFD FF1_LEAN_PLAYER
 tst.w $32fbc
 bne.b .native
 move.w d0,$32fbe
 movem.l d1/a0,-(sp)
 move.w ccr,-(sp)
 lea speed_work(pc),a0
 bsr.w FF1SpeedRate20
 move.w (a0),d0
 ext.l d0
 move.w d0,$32fbe
 move.w (sp)+,ccr
 movem.l (sp)+,d1/a0
 jmp $67402
.native:
 move.w d0,$32fbe
 jmp $67402
 ELSE
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2fbe
 jmp $67402
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_673fc
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $67402
 ENDC
velocity_67426:
 IFD FF1_LEAN_PLAYER
 tst.w $32fbc
 bne.b .native
 move.w d0,$32fbe
 movem.l d1/a0,-(sp)
 move.w ccr,-(sp)
 lea speed_work(pc),a0
 bsr.w FF1SpeedRate20
 move.w (a0),d0
 ext.l d0
 move.w d0,$32fbe
 move.w (sp)+,ccr
 movem.l (sp)+,d1/a0
 jmp $6742c
.native:
 move.w d0,$32fbe
 jmp $6742c
 ELSE
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2fbe
 jmp $6742c
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_67426
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6742c
 ENDC
velocity_67438:
 IFD FF1_LEAN_PLAYER
 tst.w $32fbc
 bne.b .native
 move.w d0,$32fbe
 movem.l d1/a0,-(sp)
 move.w ccr,-(sp)
 lea speed_work(pc),a0
 bsr.w FF1SpeedRate20
 move.w (a0),d0
 ext.l d0
 move.w d0,$32fbe
 move.w (sp)+,ccr
 movem.l (sp)+,d1/a0
 jmp $6743e
.native:
 move.w d0,$32fbe
 jmp $6743e
 ELSE
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2fbe
 jmp $6743e
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_67438
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6743e
 ENDC
velocity_6744a:
 IFD FF1_LEAN_PLAYER
 tst.w $32fbc
 bne.b .native
 move.w d0,$32fbe
 movem.l d1/a0,-(sp)
 move.w ccr,-(sp)
 lea speed_work(pc),a0
 bsr.w FF1SpeedRate20
 move.w (a0),d0
 ext.l d0
 move.w d0,$32fbe
 move.w (sp)+,ccr
 movem.l (sp)+,d1/a0
 jmp $67450
.native:
 move.w d0,$32fbe
 jmp $67450
 ELSE
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2fbe
 jmp $67450
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_6744a
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $67450
 ENDC
velocity_67476:
 IFD FF1_LEAN_PLAYER
 tst.w $32fbc
 bne.b .native
 move.w d0,$32fbe
 movem.l d1/a0,-(sp)
 move.w ccr,-(sp)
 lea speed_work(pc),a0
 bsr.w FF1SpeedRate20
 move.w (a0),d0
 ext.l d0
 move.w d0,$32fbe
 move.w (sp)+,ccr
 movem.l (sp)+,d1/a0
 jmp $6747c
.native:
 move.w d0,$32fbe
 jmp $6747c
 ELSE
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2fbe
 jmp $6747c
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_67476
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6747c
 ENDC
velocity_675c0:
 IFD FF1_LEAN_PLAYER
 tst.w $32fbc
 bne.b .native
 move.w d0,$32fbe
 movem.l d1/a0,-(sp)
 move.w ccr,-(sp)
 lea speed_work(pc),a0
 bsr.w FF1SpeedRate20
 move.w (a0),d0
 ext.l d0
 move.w d0,$32fbe
 move.w (sp)+,ccr
 movem.l (sp)+,d1/a0
 jmp $675c6
.native:
 move.w d0,$32fbe
 jmp $675c6
 ELSE
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2fbe
 jmp $675c6
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_675c0
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $675c6
 ENDC
velocity_6766c:
 IFD FF1_LEAN_PLAYER
 tst.w $32fbc
 bne.b .native
 move.w d0,$32fbe
 movem.l d1/a0,-(sp)
 move.w ccr,-(sp)
 lea speed_work(pc),a0
 bsr.w FF1SpeedRate20
 move.w (a0),d0
 ext.l d0
 move.w d0,$32fbe
 move.w (sp)+,ccr
 movem.l (sp)+,d1/a0
 jmp $67672
.native:
 move.w d0,$32fbe
 jmp $67672
 ELSE
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2fbe
 jmp $67672
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_6766c
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $67672
 ENDC
velocity_6768e:
 IFD FF1_LEAN_PLAYER
 tst.w $32fbc
 bne.b .native
 move.w d0,$32fbe
 movem.l d1/a0,-(sp)
 move.w ccr,-(sp)
 lea speed_work(pc),a0
 bsr.w FF1SpeedRate20
 move.w (a0),d0
 ext.l d0
 move.w d0,$32fbe
 move.w (sp)+,ccr
 movem.l (sp)+,d1/a0
 jmp $67694
.native:
 move.w d0,$32fbe
 jmp $67694
 ELSE
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2fbe
 jmp $67694
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_6768e
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $67694
 ENDC
velocity_676e0:
 IFD FF1_LEAN_PLAYER
 tst.w $32fbc
 bne.b .native
 move.w d0,$32fbe
 movem.l d1/a0,-(sp)
 move.w ccr,-(sp)
 lea speed_work(pc),a0
 bsr.w FF1SpeedRate20
 move.w (a0),d0
 ext.l d0
 move.w d0,$32fbe
 move.w (sp)+,ccr
 movem.l (sp)+,d1/a0
 jmp $676e6
.native:
 move.w d0,$32fbe
 jmp $676e6
 ELSE
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2fbe
 jmp $676e6
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_676e0
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $676e6
 ENDC
velocity_69970:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c1,$0003,$2fbe
 jmp $69976
.b3_player:
 ENDC
 dc.w $33c1,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_69970
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69976
velocity_69a42:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c1,$0003,$2fbe
 jmp $69a48
.b3_player:
 ENDC
 dc.w $33c1,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_rate_69a42
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69a48
velocity_6721c:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33d0,$0003,$2fc0
 jmp $67222
.b3_player:
 ENDC
 dc.w $33d0,$0003,$2fc0
 FF1PlayerSave d0/a0-a1
 move.w ccr,-(sp)
 IFND FF1_LEAN_PLAYER
 move.l d0,d7
 ENDC
 bsr.w velocity_speed_load
 move.w (sp)+,ccr
 FF1PlayerRestore d0/a0-a1
 jmp $67222
velocity_679fe:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2fbe
 jmp $67a04
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_feedback
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $67a04
velocity_6838c:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2fbe
 jmp $68392
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68392
velocity_694ce:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33fc,$0064,$0003,$2fbe
 jmp $694d6
.b3_player:
 ENDC
 dc.w $33fc,$0064,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $694d6
velocity_69b30:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2fbe
 jmp $69b36
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69b36
velocity_69b4a:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2fbe
 jmp $69b50
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2fbe
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d7
 bsr.w velocity_speed_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69b50
velocity_context:
 moveq #0,d0
 move.w $32fbc,d0
 cmpi.w #7,d0
 IFD VERIFY
 bhi.w velocity_fault
 ENDC
 mulu.w #12,d0
 lea (velocity_shadow.l,pc),a0
 adda.l d0,a0
 rts
velocity_sync:
 FF1PlayerContext velocity_shadow,velocity_context
 move.w $32f94,d0
 move.w $32f96,d1
 bsr.w FF1VelocityReset
 rts
velocity_load:
 IFD VERIFY
 lea (velocity_loads.l,pc),a1
 addq.l #1,(a1)
 ENDC
 cmpi.w #8,modeval(pc)
 bne.w velocity_sync
 FF1PlayerContext velocity_shadow,velocity_context
 move.w $32fbc,d2
 lea (velocity_initialized.l,pc),a1
 bset d2,(a1)
 bne.w velocity_check
 bsr.w velocity_sync
 clr.l 8(a0)
 rts
velocity_store:
 IFD VERIFY
 lea (velocity_stores.l,pc),a1
 addq.l #1,(a1)
 ENDC
 cmpi.w #8,modeval(pc)
 bne.w velocity_sync
 FF1PlayerContext velocity_shadow,velocity_context
 bra.w velocity_check
velocity_rotate:
 IFD VERIFY
 lea (velocity_rotations.l,pc),a1
 addq.l #1,(a1)
 ENDC
 cmpi.w #8,modeval(pc)
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
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 move.w (a0),$32f94
 move.w 4(a0),$32f96
 rts
velocity_check:
 IFD VERIFY
 move.w (a0),d0
 cmp.w $32f94,d0
 IFD VERIFY
 bne.w velocity_fault_x
 ENDC
 move.w 4(a0),d0
 cmp.w $32f96,d0
 IFD VERIFY
 bne.w velocity_fault_z
 ENDC
 rts
 ELSE
 rts
 ENDC
 IFD VERIFY
velocity_record:
 ELSE
velocity_workspace:
 ENDC
 IFD VERIFY
 move.l velocity_records_count(pc),d0
 cmpi.l #800,d0
 IFD VERIFY
 bhs.w velocity_fault
 ENDC
 mulu.w #80,d0
 lea (velocity_records.l,pc),a4
 adda.l d0,a4
 rts
 ELSE
 lea (velocity_scratch.l,pc),a4
 rts
 ENDC
velocity_project:
 IFD VERIFY
 IFD VERIFY
 bsr.w velocity_record
 ELSE
 bsr.w velocity_workspace
 ENDC
 move.w $32fbc,(a4)
 move.w 10(a6),2(a4)
 move.w 14(a6),4(a4)
 move.w -14(a6),8(a4)
 move.w -16(a6),10(a4)
 move.w $32f94,12(a4)
 move.w $32f96,14(a4)
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
 cmpi.w #8,modeval(pc)
 bne.b .integer_speed
 move.l speed_work(pc),d0
.integer_speed:
 move.l velocity_records_count(pc),d3
 lsl.l #2,d3
 lea (velocity_target_speeds,pc),a0
 move.l d0,(a0,d3.l)
 lea 24(a4),a0
 bsr.w FF1VelocityProject020
 tst.l d1
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 FF1PlayerContext velocity_shadow,velocity_context
 move.l (a0),40(a4)
 move.l 4(a0),44(a4)
 move.l 8(a0),48(a4)
 lea 40(a4),a0
 lea 24(a4),a1
 lea 52(a4),a2
 bsr.w FF1VelocityDerivative20
 tst.l d1
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 ; Old physical velocity is Q16 + carry/5: normalized delta subtracts carry.
 move.w 48(a4),d0
 ext.l d0
 sub.l d0,52(a4)
 IFD VERIFY
 bvs.w velocity_fault
 ENDC
 move.w 50(a4),d0
 ext.l d0
 sub.l d0,56(a4)
 IFD VERIFY
 bvs.w velocity_fault
 ENDC
 bsr.w velocity_coefficients
 lea 52(a4),a0
 bsr.w FF1VelocityRotate020
 tst.l d1
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 IFD VERIFY
 lea (velocity_projects.l,pc),a0
 addq.l #1,(a0)
 ENDC
 rts
 ELSE
 IFD VERIFY
 bsr.w velocity_record
 ELSE
 bsr.w velocity_workspace
 ENDC
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
 cmpi.w #8,modeval(pc)
 bne.b .integer_speed
 move.l speed_work(pc),d0
.integer_speed:
 lea 24(a4),a0
 bsr.w FF1VelocityProject020
 tst.l d1
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 FF1PlayerContext velocity_shadow,velocity_context
 move.l (a0),40(a4)
 move.l 4(a0),44(a4)
 move.l 8(a0),48(a4)
 lea 40(a4),a0
 lea 24(a4),a1
 lea 52(a4),a2
 bsr.w FF1VelocityDerivative20
 tst.l d1
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 ; Old physical velocity is Q16 + carry/5: normalized delta subtracts carry.
 move.w 48(a4),d0
 ext.l d0
 sub.l d0,52(a4)
 IFD VERIFY
 bvs.w velocity_fault
 ENDC
 move.w 50(a4),d0
 ext.l d0
 sub.l d0,56(a4)
 IFD VERIFY
 bvs.w velocity_fault
 ENDC
 bsr.w velocity_coefficients
 lea 52(a4),a0
 bsr.w FF1VelocityRotate020
 tst.l d1
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 IFD VERIFY
 lea (velocity_projects.l,pc),a0
 addq.l #1,(a0)
 ENDC
 rts
 ENDC
velocity_raw:
 IFD VERIFY
 bsr.w velocity_record
 ELSE
 bsr.w velocity_workspace
 ENDC
 cmpi.w #8,modeval(pc)
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
 IFD VERIFY
 bhi.w velocity_fault
 ENDC
 move.l d0,d7
 move.l d0,6(sp)
.native:
 move.w -12(a6),32(a4)
 move.w -10(a6),34(a4)
 move.w d7,36(a4)
 IFD VERIFY
 lea (velocity_raws.l,pc),a0
 addq.l #1,(a0)
 ENDC
 rts
velocity_limit:
 cmpi.w #8,modeval(pc)
 bne.b .done
 IFD VERIFY
 bsr.w velocity_record
 ELSE
 bsr.w velocity_workspace
 ENDC
 moveq #0,d2
 move.w 36(a4),d2
 beq.b .zero
 move.w -8(a6),38(a4)
 move.w 32(a4),d0
 move.w 38(a4),d1
 bsr.w FF1VelocityLimit020
 tst.l d1
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 move.w d0,-12(a6)
 move.w 34(a4),d0
 move.w 38(a4),d1
 bsr.w FF1VelocityLimit020
 tst.l d1
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 move.w d0,-10(a6)
 rts
.zero:
 clr.w 38(a4)
 clr.w -12(a6)
 clr.w -10(a6)
.done:
 rts
velocity_returned:
 IFD VERIFY
 IFD VERIFY
 bsr.w velocity_record
 ELSE
 bsr.w velocity_workspace
 ENDC
 move.w d7,6(a4)
 move.w $32f94,16(a4)
 move.w $32f96,18(a4)
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
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 move.l 40(a4),68(a4)
 move.l 44(a4),72(a4)
 move.l 48(a4),76(a4)
 lea 68(a4),a0
 lea 76(a4),a1
 lea 60(a4),a2
 bsr.w FF1VelocityApply20
 tst.l d1
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 cmpi.w #8,modeval(pc)
 bne.w .native
 FF1PlayerContext velocity_shadow,velocity_context
 move.l 68(a4),(a0)
 move.l 72(a4),4(a0)
 move.l 76(a4),8(a0)
 lea (speed_work.l,pc),a1
 bsr.w FF1SpeedFromVelocity020
 tst.l d1
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 move.l velocity_records_count(pc),d0
 lsl.l #3,d0
 lea (speed_feedback_records,pc),a2
 adda.l d0,a2
 move.l (a1),(a2)
 move.w 4(a1),4(a2)
 clr.w 6(a2)
 tst.l (a1)
 bne.b .moving
 clr.l (a0)
 clr.l 4(a0)
 clr.l 8(a0)
 clr.l 68(a4)
 clr.l 72(a4)
 clr.l 76(a4)
 move.w #1,6(a2)
.moving:
 move.w (a0),$32f94
 move.w 4(a0),$32f96
 move.w (a0),16(a4)
 move.w 4(a0),18(a4)
 moveq #0,d0
 move.w (a1),d0
 move.w d0,6(a4)
 move.l d0,6(sp)
.native:
 IFD VERIFY
 lea (velocity_records_count.l,pc),a0
 addq.l #1,(a0)
 ENDC
 rts
 ELSE
 IFD VERIFY
 bsr.w velocity_record
 ELSE
 bsr.w velocity_workspace
 ENDC
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
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 move.l 40(a4),68(a4)
 move.l 44(a4),72(a4)
 move.l 48(a4),76(a4)
 lea 68(a4),a0
 lea 76(a4),a1
 lea 60(a4),a2
 bsr.w FF1VelocityApply20
 tst.l d1
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 cmpi.w #8,modeval(pc)
 bne.w .native
 FF1PlayerContext velocity_shadow,velocity_context
 move.l 68(a4),(a0)
 move.l 72(a4),4(a0)
 move.l 76(a4),8(a0)
 lea (speed_work.l,pc),a1
 bsr.w FF1SpeedFromVelocity020
 tst.l d1
 IFD VERIFY
 bne.w velocity_fault
 ENDC
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
 IFD VERIFY
 lea (velocity_records_count.l,pc),a0
 addq.l #1,(a0)
 ENDC
 rts
 ENDC
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
 lea (error.l,pc),a0
 move.l d0,(a0)
velocity_stop:
 IFD FF1_PRODUCTION
 bra.w FF1ProductionFault
 ELSE
 bra.b velocity_stop
 ENDC
velocity_initialized: dc.w 0
velocity_installed: dc.l 0
velocity_loads: dc.l 0
velocity_stores: dc.l 0
velocity_rotations: dc.l 0
velocity_projects: dc.l 0
velocity_raws: dc.l 0
velocity_records_count: dc.l 0
 IFD FF1_PLAYER_HOOKS
; Persistent player state, exactly 64 bytes. Cursor and condition carries are
; unsigned 0..4, so bytes retain their complete domains. The steering helper
; leaves byte 11 (fuel carry) alone. Scratch and saved contact state are separate.
player_state:
velocity_shadow: ds.b 12
position_shadow: ds.b 12
heading_shadow: ds.b 12
speed_shadow: ds.b 6
steering_shadow: ds.b 11
fuel_remainders: ds.b 1
 ds.b 6
wear_remainders: ds.b 4
player_state_end:
 ifne player_state_end-player_state-64
 fail "B4 player state must be 64 bytes"
 ENDC
 ELSE
velocity_shadow: ds.b 96
 ENDC
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
 IFD VERIFY
 lea (velocity_cold_writes.l,pc),a0
 addq.l #1,(a0)
 ENDC
 rts
velocity_array_context:
 cmpi.l #14,d0
 IFD VERIFY
 bhi.w velocity_fault
 ENDC
 btst #0,d0
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 mulu.w #6,d0
 lea (velocity_shadow.l,pc),a0
 adda.l d0,a0
 rts
velocity_swap_z:
 IFD FF1_PLAN_B
 ; Native has already swapped speed and the first velocity word. The second
 ; velocity write follows this callback. Only the player owns fractional state.
 tst.w d3
 beq.b .b3_first
 cmpa.l #$6f14c,a0
 bne.b .b3_done
 move.w d4,d0
 bra.b .b3_reset
.b3_first:
 move.w $6f14c,d0
.b3_reset:
 lea velocity_shadow+4(pc),a1
 move.w d0,(a1)
 clr.w 2(a1)
 clr.w 6(a1)
 lea speed_shadow(pc),a1
 move.w $2275a,(a1)
 clr.l 2(a1)
.b3_done:
 rts
 ELSE
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
 IFD VERIFY
 lea (velocity_swaps.l,pc),a0
 addq.l #1,(a0)
 ENDC
 rts
 ENDC
velocity_cold_writes: dc.l 0
velocity_swaps: dc.l 0
velocity_reset_work:
 bsr.w velocity_sync
 clr.l 8(a0)
 IFD VERIFY
 lea (velocity_work_resets.l,pc),a0
 addq.l #1,(a0)
 ENDC
 rts
velocity_clamp_z:
 FF1PlayerContext velocity_shadow,velocity_context
 move.w $32f96,4(a0)
 clr.w 6(a0)
 clr.w 10(a0)
 IFD VERIFY
 lea (velocity_clamps.l,pc),a0
 addq.l #1,(a0)
 ENDC
 rts
velocity_impulse_x:
 ; D1 holds the newly computed native word; preserve fractional tail/carry.
 move.w d1,d4
 move.l a0,d0
 subi.l #$6f13c,d0
 FF1PlayerContext velocity_shadow,velocity_array_context
 move.w d4,(a0)
 IFD VERIFY
 lea (velocity_impulses.l,pc),a0
 addq.l #1,(a0)
 ENDC
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
 cmpi.w #8,modeval(pc)
 beq.b .fine
 lea $32f94,a1
 move.w d5,d0
 lsr.w #1,d0
 move.w (a1,d0.w),(a0,d5.w)
 bra.b .count
.fine:
 cmpi.l #-32768,d4
 IFD VERIFY
 blt.w velocity_fault
 ENDC
 cmpi.l #32767,d4
 IFD VERIFY
 bgt.w velocity_fault
 ENDC
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
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 move.w (a0),$32f94
 move.w 4(a0),$32f96
.count:
 IFD VERIFY
 lea (velocity_offroads.l,pc),a0
 addq.l #1,(a0)
 ENDC
 rts
velocity_offroads: dc.l 0
velocity_speed_rate_672f0:
 cmpi.w #8,modeval(pc)
 bne.b .done
 move.l d7,d0
 move.l #$672f0,d6
 bsr.w velocity_speed_rate
 move.l d0,6(sp)
.done:
 rts
velocity_speed_rate_673fc:
 cmpi.w #8,modeval(pc)
 bne.b .done
 move.l d7,d0
 move.l #$673fc,d6
 bsr.w velocity_speed_rate
 move.l d0,6(sp)
.done:
 rts
velocity_speed_rate_67426:
 cmpi.w #8,modeval(pc)
 bne.b .done
 move.l d7,d0
 move.l #$67426,d6
 bsr.w velocity_speed_rate
 move.l d0,6(sp)
.done:
 rts
velocity_speed_rate_67438:
 cmpi.w #8,modeval(pc)
 bne.b .done
 move.l d7,d0
 move.l #$67438,d6
 bsr.w velocity_speed_rate
 move.l d0,6(sp)
.done:
 rts
velocity_speed_rate_6744a:
 cmpi.w #8,modeval(pc)
 bne.b .done
 move.l d7,d0
 move.l #$6744a,d6
 bsr.w velocity_speed_rate
 move.l d0,6(sp)
.done:
 rts
velocity_speed_rate_67476:
 cmpi.w #8,modeval(pc)
 bne.b .done
 move.l d7,d0
 move.l #$67476,d6
 bsr.w velocity_speed_rate
 move.l d0,6(sp)
.done:
 rts
velocity_speed_rate_675c0:
 cmpi.w #8,modeval(pc)
 bne.b .done
 move.l d7,d0
 move.l #$675c0,d6
 bsr.w velocity_speed_rate
 move.l d0,6(sp)
.done:
 rts
velocity_speed_rate_6766c:
 cmpi.w #8,modeval(pc)
 bne.b .done
 move.l d7,d0
 move.l #$6766c,d6
 bsr.w velocity_speed_rate
 move.l d0,6(sp)
.done:
 rts
velocity_speed_rate_6768e:
 cmpi.w #8,modeval(pc)
 bne.b .done
 move.l d7,d0
 move.l #$6768e,d6
 bsr.w velocity_speed_rate
 move.l d0,6(sp)
.done:
 rts
velocity_speed_rate_676e0:
 cmpi.w #8,modeval(pc)
 bne.b .done
 move.l d7,d0
 move.l #$676e0,d6
 bsr.w velocity_speed_rate
 move.l d0,6(sp)
.done:
 rts
velocity_speed_rate_69970:
 cmpi.w #8,modeval(pc)
 bne.b .done
 move.l d1,d0
 move.l #$69970,d6
 bsr.w velocity_speed_rate
 move.l d0,10(sp)
.done:
 rts
velocity_speed_rate_69a42:
 cmpi.w #8,modeval(pc)
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
 IFD VERIFY
 bhi.w velocity_fault
 ENDC
 btst #0,d0
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 mulu.w #3,d0
 lea (speed_shadow.l,pc),a0
 adda.l d0,a0
 rts
velocity_speed_reset:
 lea (speed_work.l,pc),a0
 move.w $32fbe,d0
 bra.b velocity_speed_reset_store
velocity_speed_load:
 cmpi.w #8,modeval(pc)
 bne.b .native
 FF1PlayerContext speed_shadow,velocity_speed_context
 move.w (a0),d0
 cmp.w $32fc0,d0
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 lea (speed_work.l,pc),a1
 move.l (a0),(a1)
 move.w 4(a0),4(a1)
 IFD VERIFY
 lea (speed_loads.l,pc),a0
 addq.l #1,(a0)
 ENDC
 rts
.native:
 lea (speed_work.l,pc),a0
 move.w $32fc0,d0
velocity_speed_reset_store:
 swap d0
 clr.w d0
 move.l d0,(a0)
 clr.w 4(a0)
 rts
velocity_speed_feedback:
 cmpi.w #8,modeval(pc)
 bne.w velocity_speed_reset
 move.w speed_work(pc),d0
 cmp.w $32fbe,d0
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 rts
velocity_speed_store:
 cmpi.w #8,modeval(pc)
 bne.b .done
 FF1PlayerContext speed_shadow,velocity_speed_context
 lea (speed_work.l,pc),a1
 move.w (a1),d0
 cmp.w $32fbe,d0
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 move.l (a1),(a0)
 move.w 4(a1),4(a0)
 IFD VERIFY
 lea (speed_stores.l,pc),a0
 addq.l #1,(a0)
 ENDC
.done:
 rts
velocity_speed_cold:
 cmpi.w #8,modeval(pc)
 bne.b .done
 move.l a0,d0
 subi.l #$2275a,d0
 FF1PlayerContext speed_shadow,velocity_speed_array
 move.w d7,d0
 swap d0
 clr.w d0
 move.l d0,(a0)
 clr.w 4(a0)
 IFD VERIFY
 lea (speed_cold_writes.l,pc),a0
 addq.l #1,(a0)
 ENDC
.done:
 rts
velocity_speed_swap:
 cmpi.w #8,modeval(pc)
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
 IFD VERIFY
 lea (speed_swaps.l,pc),a0
 addq.l #1,(a0)
 ENDC
 movem.l (sp)+,d0-d3/a0-a2
.done:
 rts
velocity_speed_rate:
 IFD VERIFY
 move.l speed_records_count(pc),d3
 cmpi.l #FF1_SPEED_RECORD_CAPACITY,d3
 IFD VERIFY
 bhs.w velocity_fault
 ENDC
 lsl.l #5,d3
 lea (speed_records,pc),a3
 adda.l d3,a3
 move.l d6,(a3)
 move.w $32fbc,4(a3)
 clr.w 6(a3)
 lea (speed_work.l,pc),a0
 move.l (a0),8(a3)
 move.w 4(a0),12(a3)
 move.l d0,16(a3)
 bsr.w FF1SpeedRate20
 tst.l d1
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 move.w 4(a0),14(a3)
 move.l (a0),20(a3)
 move.l ticks(pc),24(a3)
 clr.l 28(a3)
 IFD VERIFY
 lea (speed_records_count.l,pc),a1
 addq.l #1,(a1)
 ENDC
 move.w (a0),d0
 ext.l d0
 move.w d0,$32fbe
 rts
 ELSE
 lea (speed_work.l,pc),a0
 bsr.w FF1SpeedRate20
 tst.l d1
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 move.w (a0),d0
 ext.l d0
 move.w d0,$32fbe
 rts
 ENDC
speed_work: ds.b 6
 IFND FF1_PLAYER_HOOKS
speed_shadow: ds.b 48
 ENDC
speed_records_count: dc.l 0
speed_loads: dc.l 0
speed_stores: dc.l 0
speed_cold_writes: dc.l 0
speed_swaps: dc.l 0
 include "FerrariFormulaOne_Step.s"
 include "FerrariFormulaOne_Velocity.s"
 include "FerrariFormulaOne_Speed.s"
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
 IFND FF1_PLAYER_HOOKS
 lea (bridge_6720e.l,pc),a1
 move.w #$4ef9,$6720e
 move.l a1,$67210
 ENDC
 IFND FF1_PLAYER_HOOKS
 lea (bridge_68546.l,pc),a1
 move.w #$4ef9,$68546
 move.l a1,$68548
 ENDC
 lea (bridge_67b52.l,pc),a1
 move.w #$4ef9,$67b52
 move.l a1,$67b54
 lea (bridge_67a12.l,pc),a1
 move.w #$4ef9,$67a12
 move.l a1,$67a14
 lea (bridge_67a26.l,pc),a1
 move.w #$4ef9,$67a26
 move.l a1,$67a28
 lea (bridge_67a30.l,pc),a1
 move.w #$4ef9,$67a30
 move.l a1,$67a32
 lea (bridge_68306.l,pc),a1
 move.w #$4ef9,$68306
 move.l a1,$68308
 lea (bridge_68352.l,pc),a1
 move.w #$4ef9,$68352
 move.l a1,$68354
 lea (bridge_68376.l,pc),a1
 move.w #$4ef9,$68376
 move.l a1,$68378
 move.w #$4e71,$6837c
 lea (bridge_683b8.l,pc),a1
 move.w #$4ef9,$683b8
 move.l a1,$683ba
 lea (bridge_694c8.l,pc),a1
 move.w #$4ef9,$694c8
 move.l a1,$694ca
 lea (bridge_6956a.l,pc),a1
 move.w #$4ef9,$6956a
 move.l a1,$6956c
 lea (bridge_691c4.l,pc),a1
 move.w #$4ef9,$691c4
 move.l a1,$691c6
 lea (bridge_692ae.l,pc),a1
 move.w #$4ef9,$692ae
 move.l a1,$692b0
 lea (bridge_6886e.l,pc),a1
 move.w #$4ef9,$6886e
 move.l a1,$68870
 lea (bridge_688e2.l,pc),a1
 move.w #$4ef9,$688e2
 move.l a1,$688e4
 lea (bridge_68918.l,pc),a1
 move.w #$4ef9,$68918
 move.l a1,$6891a
 move.w #$4e71,$6891e
 lea (bridge_68ab8.l,pc),a1
 move.w #$4ef9,$68ab8
 move.l a1,$68aba
 move.w #$4e71,$68abe
 lea (bridge_68b26.l,pc),a1
 move.w #$4ef9,$68b26
 move.l a1,$68b28
 lea (bridge_663f4.l,pc),a1
 move.w #$4ef9,$663f4
 move.l a1,$663f6
 lea (bridge_68c12.l,pc),a1
 move.w #$4ef9,$68c12
 move.l a1,$68c14
 lea (bridge_installed.l,pc),a0
 move.l #1,(a0)
 bra.b bridge_install_done
bridge_install_bad:
 lea (error.l,pc),a0
 move.l #6,(a0)
bridge_install_done:
 movem.l (sp)+,d0-d2/a0-a1
 rts
bridge_6720e:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33d0,$0003,$2fc4
 jmp $67214
.b3_player:
 ENDC
 dc.w $33d0,$0003,$2fc4
 FF1PlayerSave d0/a0-a1
 move.w ccr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_load
.done:
 move.w (sp)+,ccr
 FF1PlayerRestore d0/a0-a1
 jmp $67214
bridge_68546:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $30b9,$0003,$2fc4
 jmp $6854c
.b3_player:
 ENDC
 dc.w $30b9,$0003,$2fc4
 FF1PlayerSave d0/a0
 move.w ccr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_store
.done:
 move.w (sp)+,ccr
 FF1PlayerRestore d0/a0
 jmp $6854c
bridge_67b52:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c1,$0003,$2fc4
 jmp $67b58
.b3_player:
 ENDC
 dc.w $33c1,$0003,$2fc4
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_rotate
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $67b58
bridge_67a12:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2fc2
 jmp $67a18
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2fc2
 FF1PlayerSave d0/a0
 move.w ccr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_sync_x
.done:
 move.w (sp)+,ccr
 FF1PlayerRestore d0/a0
 jmp $67a18
bridge_67a26:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2fc4
 jmp $67a2c
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2fc4
 FF1PlayerSave d0/a0
 move.w ccr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_sync_z
.done:
 move.w (sp)+,ccr
 FF1PlayerRestore d0/a0
 jmp $67a2c
bridge_67a30:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $4279,$0003,$2fc4
 jmp $67a36
.b3_player:
 ENDC
 dc.w $4279,$0003,$2fc4
 FF1PlayerSave d0/a0
 move.w ccr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_reset_z
.done:
 move.w (sp)+,ccr
 FF1PlayerRestore d0/a0
 jmp $67a36
bridge_68306:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2fc2
 jmp $6830c
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2fc2
 FF1PlayerSave d0/a0
 move.w ccr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_reset_x
.done:
 move.w (sp)+,ccr
 FF1PlayerRestore d0/a0
 jmp $6830c
bridge_68352:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2fc2
 jmp $68358
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2fc2
 FF1PlayerSave d0/a0
 move.w ccr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_reset_x
.done:
 move.w (sp)+,ccr
 FF1PlayerRestore d0/a0
 jmp $68358
bridge_68376:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33fc,$015e,$0003,$2fc2
 jmp $6837e
.b3_player:
 ENDC
 dc.w $33fc,$015e,$0003,$2fc2
 FF1PlayerSave d0/a0
 move.w ccr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_reset_x
.done:
 move.w (sp)+,ccr
 FF1PlayerRestore d0/a0
 jmp $6837e
bridge_683b8:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2fc4
 jmp $683be
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2fc4
 FF1PlayerSave d0/a0
 move.w ccr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_reset_z
.done:
 move.w (sp)+,ccr
 FF1PlayerRestore d0/a0
 jmp $683be
bridge_694c8:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $4279,$0003,$2fc4
 jmp $694ce
.b3_player:
 ENDC
 dc.w $4279,$0003,$2fc4
 FF1PlayerSave d0/a0
 move.w ccr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_reset_z
.done:
 move.w (sp)+,ccr
 FF1PlayerRestore d0/a0
 jmp $694ce
bridge_6956a:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $33c0,$0003,$2fc2
 jmp $69570
.b3_player:
 ENDC
 dc.w $33c0,$0003,$2fc2
 FF1PlayerSave d0/a0
 move.w ccr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 bmi.b .done
 bsr.w bridge_reset_x
.done:
 move.w (sp)+,ccr
 FF1PlayerRestore d0/a0
 jmp $69570
bridge_691c4:
 IFD FF1_PLAN_B
 cmpa.l #$6a62a,a0
 beq.b .b3_player
 dc.w $3080,$202f,$0010
 jmp $691ca
.b3_player:
 ENDC
 dc.w $3080,$202f,$0010
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 bsr.w bridge_contact_first
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $691ca
bridge_692ae:
 IFD FF1_PLAN_B
 cmpa.l #$6a62a,a0
 beq.b .b3_player
 dc.w $3081,$222f,$0018
 jmp $692b4
.b3_player:
 ENDC
 dc.w $3081,$222f,$0018
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 bsr.w bridge_contact_second
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $692b4
bridge_6886e:
 IFD FF1_PLAN_B
 cmpa.l #$6a61a,a0
 beq.b .b3_player
 dc.w $3081
 jmp $6895e
.b3_player:
 ENDC
 dc.w $3081
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 bsr.w bridge_array_x
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6895e
bridge_688e2:
 IFD FF1_PLAN_B
 cmpa.l #$6a62a,a0
 beq.b .b3_player
 dc.w $3080
 dc.w $202f,$0000
 jmp $688e8
.b3_player:
 ENDC
 dc.w $3080,$202f,$0000
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 bsr.w bridge_array_z
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $688e8
bridge_68918:
 IFD FF1_PLAN_B
 cmpa.l #$6a61a,a0
 beq.b .b3_player
 dc.w $3080
 dc.w $3039,$0001,$c1e0
 jmp $68920
.b3_player:
 ENDC
 dc.w $3080,$3039,$0001,$c1e0
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 bsr.w bridge_array_x
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68920
bridge_68ab8:
 IFD FF1_PLAN_B
 cmpa.l #$6a61a,a0
 beq.b .b3_player
 dc.w $3080
 dc.w $3039,$0001,$c1e0
 jmp $68ac0
.b3_player:
 ENDC
 dc.w $3080,$3039,$0001,$c1e0
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 bsr.w bridge_array_x
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68ac0
bridge_68b26:
 IFD FF1_PLAN_B
 cmpa.l #$6a62a,a0
 beq.b .b3_player
 dc.w $4250
 dc.w $302f,$0000
 jmp $68b2c
.b3_player:
 ENDC
 dc.w $4250,$302f,$0000
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 bsr.w bridge_array_z
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68b2c
bridge_663f4:
 dc.w $3091,$52ae,$fffc
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 bsr.w bridge_snapshot
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $663fa
bridge_68c12:
 dc.w $3091,$322f,$0000
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 bsr.w bridge_restore
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68c18
bridge_context:
 moveq #0,d0
 move.w $32fbc,d0
 cmpi.l #7,d0
 IFD VERIFY
 bhi.b .bad
 ENDC
 mulu.w #12,d0
 lea (position_shadow.l,pc),a0
 adda.l d0,a0
 moveq #0,d0
 rts
.bad:
 lea (error.l,pc),a0
 move.l #7,(a0)
 moveq #-1,d0
 rts
bridge_load:
 lea (fine_cross_pending.l,pc),a1
 clr.w (a1)
 lea (fine_car_crosses.l,pc),a1
 clr.w (a1)
 IFD VERIFY
 lea (bridge_loads.l,pc),a1
 addq.l #1,(a1)
 ENDC
 move.w $32fc2,(a0)
 move.w $32fc4,6(a0)
 rts
bridge_store:
 IFD VERIFY
 lea (bridge_stores.l,pc),a1
 addq.l #1,(a1)
 ENDC
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
 IFD VERIFY
 lea (bridge_resets.l,pc),a1
 addq.l #1,(a1)
 ENDC
 move.w $32fc2,d0
 bra.w FF1PositionReset
bridge_reset_z:
 IFD VERIFY
 lea (bridge_resets.l,pc),a1
 addq.l #1,(a1)
 ENDC
 move.w $32fc4,d0
 addq.l #6,a0
 bra.w FF1PositionReset
bridge_rotate:
 IFD VERIFY
 lea (bridge_rotations.l,pc),a1
 addq.l #1,(a1)
 ENDC
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
 IFD VERIFY
 bne.b .bad
 ENDC
 move.w (a0),$32fc2
 move.w 6(a0),$32fc4
 rts
.bad:
 lea (error.l,pc),a1
 move.l #8,(a1)
 rts
bridge_contact_first:
 move.w -8(a6),d2
 bra.b bridge_contact
bridge_contact_second:
 move.w -6(a6),d2
bridge_contact:
 IFD FF1_PLAN_B
 ; Native contact placement is an integer offset from a native opponent.
 ; Never copy a dormant opponent shadow into the player fraction.
 cmpa.l #$6a62a,a0
 bne.b .b3_done
 move.w (a0),d0
 lea position_shadow+6(pc),a0
 bsr.w FF1PositionReset
.b3_done:
 rts
 ELSE
 move.w (a0),d4
 move.l a0,d1
 subi.l #$6a62a,d1
 cmpi.l #14,d1
 IFD VERIFY
 bhi.b .bad
 ENDC
 btst #0,d1
 IFD VERIFY
 bne.b .bad
 ENDC
 andi.l #$ffff,d2
 cmpi.l #7,d2
 IFD VERIFY
 bhi.b .bad
 ENDC
 mulu.w #6,d1
 mulu.w #12,d2
 lea (position_shadow+6.l,pc),a0
 lea (position_shadow+6.l,pc),a1
 adda.l d1,a0
 adda.l d2,a1
 move.w d4,d0
 bsr.w FF1PositionAssign
 IFD VERIFY
 lea (bridge_contacts.l,pc),a1
 addq.l #1,(a1)
 ENDC
 rts
.bad:
 lea (error.l,pc),a1
 move.l #9,(a1)
 rts
 ENDC
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
 IFD VERIFY
 bhi.w bridge_pointer_bad
 ENDC
 btst #0,d3
 IFD VERIFY
 bne.w bridge_pointer_bad
 ENDC
 mulu.w #6,d3
 lea (position_shadow.l,pc),a0
 adda.l d3,a0
 adda.l d2,a0
 bsr.w FF1PositionReset
 IFD VERIFY
 lea (bridge_array_resets.l,pc),a1
 addq.l #1,(a1)
 ENDC
 rts
bridge_snapshot:
 IFD FF1_PLAN_B
 cmpa.l #$227ca,a0
 beq.b .b3_player
 rts
.b3_player:
 ENDC
 move.w (a0),d0
 move.l a0,d3
 subi.l #$227ca,d3
 cmpi.l #14,d3
 IFD VERIFY
 bhi.w bridge_pointer_bad
 ENDC
 btst #0,d3
 IFD VERIFY
 bne.w bridge_pointer_bad
 ENDC
 move.l d3,d2
 mulu.w #3,d3
 mulu.w #6,d2
 lea (saved_position.l,pc),a0
 adda.l d3,a0
 lea (position_shadow+6.l,pc),a1
 adda.l d2,a1
 bsr.w FF1PositionAssign
 IFD VERIFY
 lea (bridge_snapshots.l,pc),a1
 addq.l #1,(a1)
 ENDC
 rts
bridge_restore:
 IFD FF1_PLAN_B
 cmpa.l #$6a62a,a0
 beq.b .b3_player
 rts
.b3_player:
 ENDC
 move.w (a0),d0
 move.l a0,d3
 subi.l #$6a62a,d3
 cmpi.l #14,d3
 IFD VERIFY
 bhi.w bridge_pointer_bad
 ENDC
 btst #0,d3
 IFD VERIFY
 bne.w bridge_pointer_bad
 ENDC
 move.l d3,d2
 mulu.w #6,d3
 mulu.w #3,d2
 lea (position_shadow+6.l,pc),a0
 adda.l d3,a0
 lea (saved_position.l,pc),a1
 adda.l d2,a1
 bsr.w FF1PositionAssign
 IFD VERIFY
 lea (bridge_restores.l,pc),a1
 addq.l #1,(a1)
 ENDC
 rts
bridge_pointer_bad:
 lea (error.l,pc),a1
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
 IFND FF1_PLAYER_HOOKS
position_shadow: ds.b 96
 ENDC
 include "FerrariFormulaOne_Position.s"
; VERIFY-only position conversion. Other physics still executes native ticks.
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
 lea (fine_advance.l,pc),a0
 move.w #$4ef9,$67a04
 move.l a0,$67a06
 lea (fine_boundary.l,pc),a0
 move.w #$4ef9,$67a36
 move.l a0,$67a38
 lea (fine_bounds.l,pc),a0
 move.w #$4ef9,$68292
 move.l a0,$68294
 lea (fine_installed.l,pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea (error.l,pc),a0
 move.l #11,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts

fine_advance:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $3039,$0003,$2fc2
 jmp $67a0a
.b3_player:
 ENDC
 IFD VERIFY
 FF1PlayerSave d0-d2/a0/a2-a3/a5
 move.w ccr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 IFD VERIFY
 bmi.w fine_fault
 ENDC
 move.w $32fc2,(a0)
 move.w $32fc4,6(a0)
 move.l a0,a3
 lea (fine_trial.l,pc),a0
 move.l (a3),(a0)
 move.l 4(a3),4(a0)
 move.l 8(a3),8(a0)
 ; Record input before changing the independent axis states.
 move.l fine_steps(pc),d0
 cmpi.l #800,d0
 IFD VERIFY
 bhs.w fine_record_overflow
 ENDC
 lsl.l #5,d0
 lea (fine_records.l,pc),a4
 adda.l d0,a4
 move.w $32fbc,(a4)
 clr.w 2(a4)
 move.w $32f94,4(a4)
 move.w $32f96,6(a4)
 move.l (a0),8(a4)
 move.l 4(a0),12(a4)
 move.l 8(a0),16(a4)
 move.l a0,a5
 FF1PlayerContext velocity_shadow,velocity_context
 move.l a0,a2
 move.l a5,a0
 move.l fine_steps(pc),d0
 mulu.w #12,d0
 lea (position_velocity_inputs.l,pc),a1
 adda.l d0,a1
 move.l (a2),(a1)
 move.l 4(a2),4(a1)
 move.l 8(a2),8(a1)
 move.l (a2),d0
 move.w 8(a2),d1
 bsr.w FF1Position20Velocity
 tst.l d1
 IFD VERIFY
 bne.w fine_fault
 ENDC
 addq.l #6,a0
 move.l 4(a2),d0
 move.w 10(a2),d1
 bsr.w FF1Position20Velocity
 tst.l d1
 IFD VERIFY
 bne.w fine_fault
 ENDC
 moveq #0,d0
 bsr.w FF1PositionClampLower
 move.w d1,2(a4)
 lea (fine_trial.l,pc),a0
 move.l (a0),(a3)
 move.l 4(a0),4(a3)
 move.l 8(a0),8(a3)
 move.l (a0),20(a4)
 move.l 4(a0),24(a4)
 move.l 8(a0),28(a4)
 move.w (a0),$32fc2
 move.w 6(a0),$32fc4
 IFD VERIFY
 lea (fine_steps.l,pc),a0
 addq.l #1,(a0)
 ENDC
 move.w (sp)+,ccr
 FF1PlayerRestore d0-d2/a0/a2-a3/a5
 jmp $67a36
 ELSE
 FF1PlayerSave d0-d2/a0/a2-a3/a5
 move.w ccr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 IFD VERIFY
 bmi.w fine_fault
 ENDC
 move.w $32fc2,(a0)
 move.w $32fc4,6(a0)
 move.l a0,a3
 lea (fine_trial.l,pc),a0
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
 IFD VERIFY
 bne.w fine_fault
 ENDC
 addq.l #6,a0
 move.l 4(a2),d0
 move.w 10(a2),d1
 bsr.w FF1Position20Velocity
 tst.l d1
 IFD VERIFY
 bne.w fine_fault
 ENDC
 moveq #0,d0
 bsr.w FF1PositionClampLower
 lea (fine_trial.l,pc),a0
 move.l (a0),(a3)
 move.l 4(a0),4(a3)
 move.l 8(a0),8(a3)
 move.w (a0),$32fc2
 move.w 6(a0),$32fc4
 IFD VERIFY
 lea (fine_steps.l,pc),a0
 addq.l #1,(a0)
 ENDC
 move.w (sp)+,ccr
 FF1PlayerRestore d0-d2/a0/a2-a3/a5
 jmp $67a36
 ENDC
fine_record_overflow:
 lea (error.l,pc),a0
 move.l #12,(a0)
 bra.w fine_stop
fine_fault:
 lea (error.l,pc),a0
 move.l #13,(a0)
fine_stop:
 bra.w velocity_stop

fine_boundary:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $3039,$0003,$2fca
 jmp $67a3c
.b3_player:
 ENDC
 FF1PlayerSave d0-d1/d4/a0-a1
 move.w ccr,-(sp)
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 IFD VERIFY
 bmi.w fine_fault
 ENDC
 move.w $32fc2,(a0)
 move.w $32fc4,6(a0)
 moveq #0,d4
 move.w $32fca,d4
 cmp.w $2268c,d4
 IFD VERIFY
 bhs.w fine_fault
 ENDC
 add.l d4,d4
 lea $1dc24,a1
 move.w (a1,d4.l),d4
 move.w d4,-16(a6)
 andi.l #1023,d4
 add.l d4,d4
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
 bsr.w FF1PositionCrossed25
 tst.l d1
 IFD VERIFY
 bne.w fine_fault
 ENDC
 lea (fine_cross_pending.l,pc),a1
 move.w d0,(a1)
 tst.l d0
 beq.b .inside
 lea (fine_car_crosses.l,pc),a1
 addq.w #1,(a1)
 cmpi.w #64,(a1)
 IFD VERIFY
 bhi.w fine_fault
 ENDC
 move.w (sp)+,ccr
 FF1PlayerRestore d0-d1/d4/a0-a1
 jmp $67aac
.inside:
 move.w (sp)+,ccr
 FF1PlayerRestore d0-d1/d4/a0-a1
 jmp $68292

fine_bounds:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $3039,$0003,$2fbc
 jmp $68298
.b3_player:
 ENDC
 move.w $32fbc,d0
 FF1PlayerSave d0-d1/d4/a0-a1
 move.w ccr,-(sp)
 lea (fine_cross_pending.l,pc),a1
 tst.w (a1)
 beq.b .bounds
 clr.w (a1)
 move.w (sp)+,ccr
 FF1PlayerRestore d0-d1/d4/a0-a1
 jmp $67a36
.bounds:
 moveq #0,d0
 move.w $32fbc,d0
 cmpi.w #7,d0
 IFD VERIFY
 bhi.w fine_fault
 ENDC
 add.l d0,d0
 lea $32f30,a1
 tst.w (a1,d0.l)
 ble.b .done
 FF1PlayerContext position_shadow,bridge_context
 tst.l d0
 IFD VERIFY
 bmi.w fine_fault
 ENDC
 move.w $32fc2,(a0)
 moveq #0,d4
 move.w $32fca,d4
 cmp.w $2268c,d4
 IFD VERIFY
 bhs.w fine_fault
 ENDC
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
 FF1PlayerRestore d0-d1/d4/a0-a1
 jmp $68298
fine_installed: dc.l 0
fine_steps: dc.l 0
fine_cross_pending: dc.w 0
fine_car_crosses: dc.w 0
fine_trial: ds.b 12

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
 lea (heading_67280.l,pc),a0
 move.w #$4ef9,$67280
 move.l a0,$67282
 lea (heading_6860e.l,pc),a0
 move.w #$4ef9,$6860e
 move.l a0,$68610
 lea (heading_678de.l,pc),a0
 move.w #$4ef9,$678de
 move.l a0,$678e0
 lea (heading_67900.l,pc),a0
 move.w #$4ef9,$67900
 move.l a0,$67902
 lea (heading_67948.l,pc),a0
 move.w #$4ef9,$67948
 move.l a0,$6794a
 lea (heading_67976.l,pc),a0
 move.w #$4ef9,$67976
 move.l a0,$67978
 lea (heading_67320.l,pc),a0
 move.w #$4ef9,$67320
 move.l a0,$67322
 move.w #$4e71,$67326
 move.w #$4e71,$67328
 move.w #$4e71,$6732a
 lea (heading_683ac.l,pc),a0
 move.w #$4ef9,$683ac
 move.l a0,$683ae
 move.w #$4e71,$683b2
 move.w #$4e71,$683b4
 move.w #$4e71,$683b6
 lea (heading_69590.l,pc),a0
 move.w #$4ef9,$69590
 move.l a0,$69592
 lea (heading_695e8.l,pc),a0
 move.w #$4ef9,$695e8
 move.l a0,$695ea
 lea (heading_68a5e.l,pc),a0
 move.w #$4ef9,$68a5e
 move.l a0,$68a60
 lea (heading_68c24.l,pc),a0
 move.w #$4ef9,$68c24
 move.l a0,$68c26
 move.w #$4e71,$68c2a
 move.w #$4e71,$68c2c
 lea (heading_68d0e.l,pc),a0
 move.w #$4ef9,$68d0e
 move.l a0,$68d10
 move.w #$4e71,$68d14
 lea (heading_installed.l,pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea (error.l,pc),a0
 move.l #15,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
heading_67280:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $23d0,$0003,$2fb8
 jmp $67286
.b3_player:
 ENDC
 IFD FF1_LEAN_PLAYER
 dc.w $23d0,$0003,$2fb8
 movem.l d0-d1/a0-a1,-(sp)
 move.w ccr,-(sp)
 lea velocity_initialized(pc),a0
 bset #0,(a0)
 bne.b .loaded
 lea velocity_shadow(pc),a0
 move.w $32f94,d0
 move.w $32f96,d1
 bsr.w FF1VelocityReset
 clr.l 8(a0)
.loaded:
 lea fine_cross_pending(pc),a0
 clr.w (a0)
 lea fine_car_crosses(pc),a0
 clr.w (a0)
 lea position_shadow(pc),a0
 move.w $32fc2,(a0)
 move.w $32fc4,6(a0)
 lea speed_shadow(pc),a0
 lea speed_work(pc),a1
 move.l (a0),(a1)
 move.w 4(a0),4(a1)
 lea heading_shadow(pc),a0
 move.l $32fb4,(a0)
 move.l $32fb8,6(a0)
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d1/a0-a1
 jmp $67286
 ELSE
 dc.w $23d0,$0003,$2fb8
 FF1PlayerSave d0-d2/a0-a1
 move.w ccr,-(sp)
 IFND FF1_LEAN_PLAYER
 move.l d0,d4
 ENDC
 IFD FF1_PLAYER_HOOKS
 ; Shared save frame for the adjacent native state loads/stores.
 bsr.w velocity_load
 lea position_shadow(pc),a0
 bsr.w bridge_load
 bsr.w velocity_speed_load
 lea (heading_shadow.l,pc),a0
 moveq #0,d0
 ELSE
 bsr.w heading_context
 ENDC
 bsr.w heading_sync
 move.w (sp)+,ccr
 FF1PlayerRestore d0-d2/a0-a1
 jmp $67286
 ENDC
heading_6860e:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $20b9,$0003,$2fb8
 jmp $68614
.b3_player:
 ENDC
 IFD FF1_LEAN_PLAYER
 dc.w $20b9,$0003,$2fb8
 movem.l d0-d1/a0-a1,-(sp)
 move.w ccr,-(sp)
 lea position_shadow(pc),a0
 move.w $32fc2,(a0)
 move.w $32fc4,6(a0)
 lea speed_work(pc),a0
 lea speed_shadow(pc),a1
 move.l (a0),(a1)
 move.w 4(a0),4(a1)
 lea heading_shadow(pc),a0
 move.l $32fb4,(a0)
 move.l $32fb8,6(a0)
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d1/a0-a1
 jmp $68614
 ELSE
 dc.w $20b9,$0003,$2fb8
 FF1PlayerSave d0-d2/a0-a1
 move.w ccr,-(sp)
 IFND FF1_LEAN_PLAYER
 move.l d0,d4
 ENDC
 IFD FF1_PLAYER_HOOKS
 ; Shared save frame for the adjacent native state loads/stores.
 bsr.w velocity_store
 lea position_shadow(pc),a0
 bsr.w bridge_store
 bsr.w velocity_speed_store
 lea (heading_shadow.l,pc),a0
 moveq #0,d0
 ELSE
 bsr.w heading_context
 ENDC
 bsr.w heading_sync
 move.w (sp)+,ccr
 FF1PlayerRestore d0-d2/a0-a1
 jmp $68614
 ENDC
heading_678de:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $d1b9,$0003,$2fb4
 jmp $678e4
.b3_player:
 ENDC
 IFD FF1_LEAN_PLAYER
 movem.l d0-d2/a0,-(sp)
 move.w ccr,-(sp)
 lea heading_shadow+0(pc),a0
 move.l $32fb4,(a0)
 addq.l #4,a0
 bsr.w FF1Step20Delta
 tst.l d1
 bne.b .unchanged
 add.l d0,-4(a0)
.unchanged:
 move.l -4(a0),$32fb4
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d2/a0
 jmp $678e4
 ELSE
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d4
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_step_a
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $678e4
 ENDC
heading_67900:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $d1b9,$0003,$2fb8
 jmp $67906
.b3_player:
 ENDC
 IFD FF1_LEAN_PLAYER
 movem.l d0-d2/a0,-(sp)
 move.w ccr,-(sp)
 lea heading_shadow+6(pc),a0
 move.l $32fb8,(a0)
 addq.l #4,a0
 bsr.w FF1Step20Delta
 tst.l d1
 bne.b .unchanged
 add.l d0,-4(a0)
.unchanged:
 move.l -4(a0),$32fb8
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d2/a0
 jmp $67906
 ELSE
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d4
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_step_b
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $67906
 ENDC
heading_67948:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $d1b9,$0003,$2fb4
 jmp $6794e
.b3_player:
 ENDC
 IFD FF1_LEAN_PLAYER
 movem.l d0-d2/a0,-(sp)
 move.w ccr,-(sp)
 lea heading_shadow+0(pc),a0
 move.l $32fb4,(a0)
 addq.l #4,a0
 bsr.w FF1Step20Delta
 tst.l d1
 bne.b .unchanged
 add.l d0,-4(a0)
.unchanged:
 move.l -4(a0),$32fb4
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d2/a0
 jmp $6794e
 ELSE
 FF1PlayerSave d0-d2/d4-d5/a0/a2-a3
 move.w ccr,-(sp)
 move.l d0,d4
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_step_a
 move.w (sp)+,ccr
 FF1PlayerRestore d0-d2/d4-d5/a0/a2-a3
 jmp $6794e
 ENDC
heading_67976:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $d1b9,$0003,$2fb8
 jmp $6797c
.b3_player:
 ENDC
 IFD FF1_LEAN_PLAYER
 movem.l d0-d2/a0,-(sp)
 move.w ccr,-(sp)
 lea heading_shadow+6(pc),a0
 move.l $32fb8,(a0)
 addq.l #4,a0
 bsr.w FF1Step20Delta
 tst.l d1
 bne.b .unchanged
 add.l d0,-4(a0)
.unchanged:
 move.l -4(a0),$32fb8
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d2/a0
 jmp $6797c
 ELSE
 FF1PlayerSave d0-d2/d4-d5/a0/a2-a3
 move.w ccr,-(sp)
 move.l d0,d4
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_step_b
 move.w (sp)+,ccr
 FF1PlayerRestore d0-d2/d4-d5/a0/a2-a3
 jmp $6797c
 ENDC
heading_67320:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $91b9,$0003,$2fb8
 dc.w $42b9,$0003,$2fb4
 jmp $6732c
.b3_player:
 ENDC
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d4
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_zero
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6732c
heading_683ac:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $93b9,$0003,$2fb8
 dc.w $42b9,$0003,$2fb4
 jmp $683b8
.b3_player:
 ENDC
 FF1PlayerSave d0-d1/a0
 move.w ccr,-(sp)
 IFND FF1_LEAN_PLAYER
 move.l d0,d4
 ENDC
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_zero
 move.w (sp)+,ccr
 FF1PlayerRestore d0-d1/a0
 jmp $683b8
heading_69590:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $23c0,$0003,$2fb4
 jmp $69596
.b3_player:
 ENDC
 dc.w $23c0,$0003,$2fb4
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d4
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_reset_a
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $69596
heading_695e8:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $23c0,$0003,$2fb8
 jmp $695ee
.b3_player:
 ENDC
 dc.w $23c0,$0003,$2fb8
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d4
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_reset_b
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $695ee
heading_68a5e:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $4290
 dc.w $202f,$0000
 jmp $68a64
.b3_player:
 ENDC
 dc.w $4290,$202f,$0000
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d4
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_reset_a
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68a64
heading_68c24:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $4290
 dc.w $2040
 dc.w $d1fc,$0006,$a60a
 jmp $68c2e
.b3_player:
 ENDC
 dc.w $4290,$2040,$d1fc,$0006,$a60a
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d4
 FF1PlayerContext heading_shadow,heading_context
 bsr.w heading_reset_a
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68c2e
heading_68d0e:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $202e,$fff6
 dc.w $d091
 dc.w $2080
 jmp $68d16
.b3_player:
 ENDC
 dc.w $202e,$fff6,$d091,$2080
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
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
 IFD VERIFY
 bhi.w fine_fault
 ENDC
 mulu.w #12,d0
 lea (heading_shadow.l,pc),a0
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
 IFD VERIFY
 move.l a0,a3
 move.l heading_steps(pc),d0
 cmpi.l #1600,d0
 IFD VERIFY
 bhs.w fine_fault
 ENDC
 mulu.w #24,d0
 lea (heading_records.l,pc),a4
 adda.l d0,a4
 move.w $32fbc,(a4)
 move.w d5,2(a4)
 move.l d4,4(a4)
 lea $32fb4,a2
 tst.w d5
 beq.b .axis_ready
 addq.l #4,a2
.axis_ready:
 move.l (a2),(a0)
 move.l (a0),8(a4)
 move.w 4(a0),12(a4)
 clr.w 14(a4)
 move.l d4,d0
 bsr.w FF1Heading20
 tst.l d1
 IFD VERIFY
 bne.w fine_fault
 ENDC
 move.l (a0),(a2)
 move.l (a0),16(a4)
 move.w 4(a0),20(a4)
 move.w d1,22(a4)
 IFD VERIFY
 lea (heading_steps.l,pc),a1
 addq.l #1,(a1)
 ENDC
 rts
 ELSE
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
 IFD VERIFY
 bne.w fine_fault
 ENDC
 move.l (a0),(a2)
 IFD VERIFY
 lea (heading_steps.l,pc),a1
 addq.l #1,(a1)
 ENDC
 rts
 ENDC
heading_zero:
 bsr.w heading_sync
 bsr.w FF1HeadingZeroRelative
 move.l (a0),$32fb4
 move.l 6(a0),$32fb8
 IFD VERIFY
 lea (heading_zeroes.l,pc),a1
 addq.l #1,(a1)
 ENDC
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
 IFD VERIFY
 lea (heading_resets.l,pc),a1
 addq.l #1,(a1)
 ENDC
 rts
heading_reset_b:
 addq.l #6,a0
 move.l $32fb8,d0
 bsr.w FF1HeadingReset
 IFD VERIFY
 lea (heading_resets.l,pc),a1
 addq.l #1,(a1)
 ENDC
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
 IFD VERIFY
 lea (heading_assignments.l,pc),a1
 addq.l #1,(a1)
 ENDC
 rts
heading_installed: dc.l 0
heading_steps: dc.l 0
heading_zeroes: dc.l 0
heading_resets: dc.l 0
heading_assignments: dc.l 0
 IFND FF1_PLAYER_HOOKS
heading_shadow: ds.b 96
 ENDC
 include "FerrariFormulaOne_Heading.s"
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
 lea (steering_6773c.l,pc),a0
 move.w #$4ef9,$6773c
 move.l a0,$6773e
 lea (steering_68788.l,pc),a0
 move.w #$4ef9,$68788
 move.l a0,$6878a
 move.w #$4e71,$6878e
 move.w #$4e71,$68790
 lea steering_shadow(pc),a0
 lea $32f7a,a1
 move.l ticks(pc),d3
 subq.l #1,d3
 IFD FF1_PLAYER_HOOKS
 moveq #0,d7
 ELSE
 moveq #7,d7
 ENDC
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
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $d240
 dc.w $e241
 dc.w $3081
 jmp $67742
.b3_player:
 ENDC
 move.w ccr,-(sp)
 cmpi.w #8,modeval(pc)
 beq.b .fine
 move.w (sp)+,ccr
 dc.w $d240,$e241,$3081
 jmp $67742
.fine:
 move.w (sp)+,ccr
 FF1PlayerSave d0-d6/a0/a5
 move.w ccr,-(sp)
 move.l d0,d4
 move.l a0,a5
 bsr.w steering_sample
 move.w (sp)+,ccr
 FF1PlayerRestore d0-d6/a0/a5
 jmp $67742
steering_68788:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $7000
 dc.w $3080
 dc.w $4a79,$0001,$c222
 jmp $68792
.b3_player:
 ENDC
 dc.w $7000,$3080,$4a79,$0001,$c222
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 bsr.w steering_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68792
steering_context:
 moveq #0,d0
 move.w $32fbc,d0
 cmpi.w #7,d0
 IFD VERIFY
 bhi.w velocity_fault
 ENDC
 mulu.w #18,d0
 lea steering_shadow(pc),a0
 adda.l d0,a0
 rts
steering_sample:
 IFD VERIFY
 FF1PlayerContext steering_shadow,steering_context
 move.l steering_samples(pc),d0
 cmpi.l #800,d0
 IFD VERIFY
 bhs.w velocity_fault
 ENDC
 mulu.w #20,d0
 lea (steering_records.l,pc),a4
 adda.l d0,a4
 move.l ticks(pc),d3
 move.l d3,(a4)
 move.w $32fbc,4(a4)
 move.w d4,6(a4)
 move.l 12(a0),12(a4)
 sub.l 12(a0),d3
 move.l d3,16(a4)
 move.l ticks(pc),d3
 move.w d4,d0
 bsr.w FF1SteeringSample20
 tst.l d1
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 move.w d2,8(a4)
 move.w d0,10(a4)
 move.w d0,12(sp)
 move.w d0,(a5)
 move.w ccr,d5
 andi.w #15,d5
 move.w d4,d6
 add.w d2,d6
 andi.w #1,d6
 lsl.w #4,d6
 or.w d6,d5
 andi.w #$ffe0,4(sp)
 or.w d5,4(sp)
 IFD VERIFY
 lea steering_samples(pc),a0
 addq.l #1,(a0)
 ENDC
 rts
 ELSE
 FF1PlayerContext steering_shadow,steering_context
 move.l ticks(pc),d3
 move.w d4,d0
 bsr.w FF1SteeringSample20
 tst.l d1
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 move.w d0,12(sp)
 move.w d0,(a5)
 move.w ccr,d5
 andi.w #15,d5
 move.w d4,d6
 add.w d2,d6
 andi.w #1,d6
 lsl.w #4,d6
 or.w d6,d5
 andi.w #$ffe0,4(sp)
 or.w d5,4(sp)
 IFD VERIFY
 lea steering_samples(pc),a0
 addq.l #1,(a0)
 ENDC
 rts
 ENDC
steering_reset:
 cmpi.w #8,modeval(pc)
 bne.b .done
 FF1PlayerContext steering_shadow,steering_context
 moveq #0,d0
 move.l ticks(pc),d3
 subq.l #1,d3
 bsr.w FF1SteeringReset
 IFD VERIFY
 lea steering_resets(pc),a0
 addq.l #1,(a0)
 ENDC
.done:
 rts
steering_installed: dc.l 0
steering_samples: dc.l 0
steering_resets: dc.l 0
 IFND FF1_PLAYER_HOOKS
steering_shadow: ds.b 144
 ENDC
 include "FerrariFormulaOne_Steering.s"
install_wear:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #7,d0
 blo.w .done
 cmpi.w #$4c01,$6de74
 bne.w .bad
 cmpi.w #$0800,$6de76
 bne.w .bad
 cmpi.w #$4e71,$6de78
 bne.w .bad
 cmpi.w #$4c01,$6defa
 bne.w .bad
 cmpi.w #$0800,$6defc
 bne.w .bad
 cmpi.w #$4e71,$6defe
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
 lea (wear_6de74.l,pc),a0
 move.w #$4ef9,$6de74
 move.l a0,$6de76
 lea (wear_6defa.l,pc),a0
 move.w #$4ef9,$6defa
 move.l a0,$6defc
 lea (wear_6de96.l,pc),a0
 move.w #$4ef9,$6de96
 move.l a0,$6de98
 lea (wear_6ded4.l,pc),a0
 move.w #$4ef9,$6ded4
 move.l a0,$6ded6
 lea (wear_6df2a.l,pc),a0
 move.w #$4ef9,$6df2a
 move.l a0,$6df2c
 move.w #$4e71,$6df30
 lea (wear_6e018.l,pc),a0
 move.w #$4ef9,$6e018
 move.l a0,$6e01a
 move.w #$4e71,$6e01e
 move.w #$4e71,$6e020
 lea (wear_64b4c.l,pc),a0
 move.w #$4ef9,$64b4c
 move.l a0,$64b4e
 lea (wear_687f4.l,pc),a0
 move.w #$4ef9,$687f4
 move.l a0,$687f6
 lea (wear_6c67c.l,pc),a0
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
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $4eb9,$0002,$9500
 jmp $6de7a
.b3_player:
 ENDC
 IFD FF1_LEAN_PLAYER
 dc.w $4c01,$0800,$4e71
 movem.l d0-d2/a1,-(sp)
 move.w ccr,-(sp)
 move.l a0,d2
 subi.l #$66c52,d2
 lsr.l #2,d2
 lea wear_remainders(pc),a1
 adda.l d2,a1
 bsr.w FF1Wear20Delta
 move.l d0,2(sp)
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d2/a1

 jmp $6de7a
 ELSE
 dc.w $4c01,$0800,$4e71
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d4
 move.l #$6de74,d6
 moveq #6,d7
 bsr.w wear_sample
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6de7a
 ENDC
wear_6defa:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $4eb9,$0002,$9500
 jmp $6df00
.b3_player:
 ENDC
 IFD FF1_LEAN_PLAYER
 dc.w $4c01,$0800,$4e71
 movem.l d0-d2/a1,-(sp)
 move.w ccr,-(sp)
 move.l a0,d2
 subi.l #$66c52,d2
 lsr.l #2,d2
 lea wear_remainders(pc),a1
 adda.l d2,a1
 bsr.w FF1Wear20Delta
 move.l d0,2(sp)
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d2/a1

 jmp $6df00
 ELSE
 dc.w $4c01,$0800,$4e71
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d4
 move.l #$6defa,d6
 moveq #6,d7
 bsr.w wear_sample
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6df00
 ENDC
wear_6de96:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $2236,$08d8
 dc.w $9390
 jmp $6de9c
.b3_player:
 ENDC
 IFD FF1_LEAN_PLAYER
 dc.w $2236,$08d8
 movem.l d0-d2/a1,-(sp)
 move.w ccr,-(sp)
 move.l a0,d2
 subi.l #$66c52,d2
 lsr.l #2,d2
 lea wear_remainders(pc),a1
 adda.l d2,a1
 move.l d1,d0
 bsr.w FF1Wear20Delta
 move.l d0,6(sp)
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d2/a1
 dc.w $9390
 jmp $6de9c
 ELSE
 dc.w $2236,$08d8
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d1,d4
 move.l #$6de96,d6
 moveq #10,d7
 bsr.w wear_sample
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $9390
 jmp $6de9c
 ENDC
wear_6ded4:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $2236,$08d8
 dc.w $9390
 jmp $6deda
.b3_player:
 ENDC
 IFD FF1_LEAN_PLAYER
 dc.w $2236,$08d8
 movem.l d0-d2/a1,-(sp)
 move.w ccr,-(sp)
 move.l a0,d2
 subi.l #$66c52,d2
 lsr.l #2,d2
 lea wear_remainders(pc),a1
 adda.l d2,a1
 move.l d1,d0
 bsr.w FF1Wear20Delta
 move.l d0,6(sp)
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d2/a1
 dc.w $9390
 jmp $6deda
 ELSE
 dc.w $2236,$08d8
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d1,d4
 move.l #$6ded4,d6
 moveq #10,d7
 bsr.w wear_sample
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $9390
 jmp $6deda
 ENDC
wear_6df2a:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $2236,$08d8
 dc.w $e381
 dc.w $9390
 jmp $6df32
.b3_player:
 ENDC
 IFD FF1_LEAN_PLAYER
 dc.w $2236,$08d8,$e381
 movem.l d0-d2/a1,-(sp)
 move.w ccr,-(sp)
 move.l a0,d2
 subi.l #$66c52,d2
 lsr.l #2,d2
 lea wear_remainders(pc),a1
 adda.l d2,a1
 move.l d1,d0
 bsr.w FF1Wear20Delta
 move.l d0,6(sp)
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d2/a1
 dc.w $9390
 jmp $6df32
 ELSE
 dc.w $2236,$08d8,$e381
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d1,d4
 move.l #$6df2a,d6
 moveq #10,d7
 bsr.w wear_sample
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $9390
 jmp $6df32
 ENDC
wear_6e018:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $9190
 dc.w $2041
 dc.w $d1fc,$0002,$2356
 jmp $6e022
.b3_player:
 ENDC
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
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
 move.w ccr,-(sp)
 bsr.w wear_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $52ae,$fffc
 jmp $64b52
wear_687f4:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 bsr.w wear_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $223c,$00ff,$0000
 jmp $687fa
wear_6c67c:
 dc.w $20bc,$00ff,$0000
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
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
 IFD VERIFY
 bhs.w velocity_fault
 ENDC
 addi.l #16,d2
.player:
 move.l d2,d3
 andi.l #3,d3
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 lsr.l #1,d2
 lea wear_remainders(pc),a1
 adda.l d2,a1
 rts
wear_reset:
 IFD FF1_PLAN_B
 ; Only the four player tyre slots own 20 ms wear remainders. Opponent
 ; repair/refill writes remain native and must not touch dormant fractions.
 cmpa.l #$66c52,a0
 blo.b .b3_native
 cmpa.l #$66c62,a0
 blo.b .b3_player
.b3_native:
 rts
.b3_player:
 ENDC
 cmpi.w #8,modeval(pc)
 bne.b .done
 IFD FF1_PLAYER_HOOKS
 move.l a0,d2
 subi.l #$66c52,d2
 lsr.l #2,d2
 lea wear_remainders(pc),a1
 adda.l d2,a1
 ELSE
 bsr.w wear_context
 ENDC
 IFD FF1_PLAYER_HOOKS
 clr.b (a1)
 ELSE
 clr.w (a1)
 ENDC
 IFD VERIFY
 lea wear_resets(pc),a1
 addq.l #1,(a1)
 ENDC
.done:
 rts
wear_sample:
 IFD VERIFY
 cmpi.w #8,modeval(pc)
 bne.w .done
 IFD FF1_PLAYER_HOOKS
 move.l a0,d2
 subi.l #$66c52,d2
 lsr.l #2,d2
 lea wear_remainders(pc),a1
 adda.l d2,a1
 ELSE
 bsr.w wear_context
 ENDC
 move.l wear_samples(pc),d2
 cmpi.l #4096,d2
 IFD VERIFY
 bhs.w velocity_fault
 ENDC
 lsl.l #5,d2
 lea (wear_records.l,pc),a4
 adda.l d2,a4
 move.l d6,(a4)
 move.l a0,4(a4)
 move.l (a0),8(a4)
 move.l d4,12(a4)
 IFD FF1_PLAYER_HOOKS
 clr.w 20(a4)
 move.b (a1),21(a4)
 ELSE
 move.w (a1),20(a4)
 ENDC
 move.l ticks(pc),24(a4)
 move.l d4,d0
 bsr.w FF1Wear20Delta
 tst.l d1
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 move.l d0,16(a4)
 IFD FF1_PLAYER_HOOKS
 clr.w 22(a4)
 move.b (a1),23(a4)
 ELSE
 move.w (a1),22(a4)
 ENDC
 move.l d0,(sp,d7.l)
 IFD VERIFY
 lea wear_samples(pc),a1
 addq.l #1,(a1)
 ENDC
.done:
 rts
 ELSE
 cmpi.w #8,modeval(pc)
 bne.b .done
 IFD FF1_PLAYER_HOOKS
 move.l a0,d2
 subi.l #$66c52,d2
 lsr.l #2,d2
 lea wear_remainders(pc),a1
 adda.l d2,a1
 ELSE
 bsr.w wear_context
 ENDC
 move.l d4,d0
 bsr.w FF1Wear20Delta
 tst.l d1
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 move.l d0,(sp,d7.l)
.done:
 rts
 ENDC
wear_installed: dc.l 0
wear_samples: dc.l 0
wear_resets: dc.l 0
 IFND FF1_PLAYER_HOOKS
wear_remainders: ds.w 12
 ENDC
 include "FerrariFormulaOne_Wear.s"
install_events:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #7,d0
 blo.w .done
 cmpi.w #$6100,$6d5f2
 bne.w .bad
 cmpi.w #$144a,$6d5f4
 bne.w .bad
 cmpi.w #$6000,$6d5f6
 bne.w .bad
 cmpi.w #$008c,$6d5f8
 bne.w .bad
 cmpi.w #$6100,$6d67e
 bne.w .bad
 cmpi.w #$17f0,$6d680
 bne.w .bad
 cmpi.w #$588f,$6d682
 bne.w .bad
 cmpi.w #$4e56,$24eec
 bne.w .bad
 cmpi.w #$fffe,$24eee
 bne.w .bad
 cmpi.w #$2079,$24ef0
 bne.w .bad
 cmpi.w #$0002,$24ef2
 bne.w .bad
 cmpi.w #$4fd4,$24ef4
 bne.w .bad
 lea (events_6d5f2.l,pc),a0
 move.w #$4ef9,$6d5f2
 move.l a0,$6d5f4
 move.w #$4e71,$6d5f8
 lea (events_6d67e.l,pc),a0
 move.w #$4ef9,$6d67e
 move.l a0,$6d680
 lea (events_24eec.l,pc),a0
 move.w #$4ef9,$24eec
 move.l a0,$24eee
 move.w #$4e71,$24ef2
 move.w #$4e71,$24ef4
 lea events_installed(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #29,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
events_quantum:
 IFND FF1_PRODUCTION
 cmpi.l #126,ticks(pc)
 blo.b .done
 ENDC
 cmpi.w #8,modeval(pc)
 bne.b .done
 lea events_phase(pc),a0
 clr.w 2(a0)
 addq.w #1,(a0)
 cmpi.w #5,(a0)
 blo.b .done
 clr.w (a0)
 move.w #1,2(a0)
 IFD VERIFY
 lea events_pulses(pc),a0
 addq.l #1,(a0)
 ENDC
.done:
 rts
events_6d5f2:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 jsr $6ea3e
 jmp $6d684
.b3_player:
 ENDC
 IFD FF1_LEAN_PLAYER
 move.w ccr,-(sp)
 tst.w events_pulse(pc)
 beq.b .skip
 move.w (sp)+,ccr
 jsr $6ea3e
 jmp $6d684
.skip:
 move.w (sp)+,ccr
 jmp $6d684
 ELSE
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 moveq #0,d6
 bsr.w events_before
 tst.w d0
 beq.b .skip
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jsr $6ea3e
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
.skip:
 IFD VERIFY
 bsr.w events_after
 ENDC
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6d684
 ENDC
events_6d67e:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 jsr $6ee70
 dc.w $588f
 jmp $6d684
.b3_player:
 ENDC
 IFD FF1_LEAN_PLAYER
 move.w ccr,-(sp)
 tst.w events_pulse(pc)
 beq.b .skip
 move.w (sp)+,ccr
 jsr $6ee70
 dc.w $588f
 jmp $6d684
.skip:
 move.w (sp)+,ccr
 dc.w $588f
 jmp $6d684
 ELSE
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 moveq #1,d6
 bsr.w events_before
 tst.w d0
 beq.b .skip
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jsr $6ee70
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
.skip:
 IFD VERIFY
 bsr.w events_after
 ENDC
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 addq.l #4,sp
 jmp $6d684
 ENDC
events_24eec:
 IFD VERIFY
 move.w ccr,-(sp)
 move.l a0,-(sp)
 IFD VERIFY
 lea events_rng_calls(pc),a0
 addq.l #1,(a0)
 ENDC
 move.l (sp)+,a0
 move.w (sp)+,ccr
 dc.w $4e56,$fffe,$2079,$0002,$4fd4
 jmp $24ef6
 ELSE
 dc.w $4e56,$fffe,$2079,$0002,$4fd4
 jmp $24ef6
 ENDC
events_record:
 IFD VERIFY
 move.l events_samples(pc),d0
 cmpi.l #800,d0
 IFD VERIFY
 bhs.w velocity_fault
 ENDC
 mulu.w #160,d0
 lea (events_records.l,pc),a4
 adda.l d0,a4
 rts
 ELSE
 rts
 ENDC
events_before:
 IFD VERIFY
 bsr.w events_record
 move.l ticks(pc),(a4)
 move.w $32fbc,4(a4)
 move.w d6,6(a4)
 moveq #1,d0
 cmpi.w #8,modeval(pc)
 bne.b .decided
 move.w events_pulse(pc),d0
.decided:
 move.w d0,8(a4)
 move.w $6ef52,10(a4)
 move.l events_rng_calls(pc),16(a4)
 lea 32(a4),a1
 bsr.w events_snapshot
 move.w 8(a4),d0
 rts
 ELSE
 moveq #1,d0
 cmpi.w #8,modeval(pc)
 bne.b .done
 move.w events_pulse(pc),d0
.done:
 rts
 ENDC
events_after:
 IFD VERIFY
 bsr.w events_record
 move.w $6ef52,12(a4)
 move.l events_rng_calls(pc),20(a4)
 lea 96(a4),a1
 bsr.w events_snapshot
 IFD VERIFY
 lea events_samples(pc),a0
 addq.l #1,(a0)
 ENDC
 rts
 ELSE
 rts
 ENDC
events_snapshot:
 IFD VERIFY
 lea $66c3e,a0
 moveq #13,d0
.copy:
 move.l (a0)+,(a1)+
 dbra d0,.copy
 moveq #0,d0
 move.w $32fbc,d0
 add.w d0,d0
 move.w $2268e(d0.l),(a1)+
 move.w $2269e(d0.l),(a1)+
 add.w d0,d0
 move.l $6f10a(d0.l),(a1)+
 rts
 ELSE
 rts
 ENDC
events_installed: dc.l 0
events_samples: dc.l 0
events_rng_calls: dc.l 0
events_pulses: dc.l 0
events_phase: dc.w 0
events_pulse: dc.w 0
install_clocks:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #7,d0
 blo.w .done
 cmpi.w #$4eb9,$65dca
 bne.w .bad
 cmpi.w #$0002,$65dcc
 bne.w .bad
 cmpi.w #$2c3a,$65dce
 bne.w .bad
 cmpi.w #$4eb9,$65dd8
 bne.w .bad
 cmpi.w #$0002,$65dda
 bne.w .bad
 cmpi.w #$2c3a,$65ddc
 bne.w .bad
 lea (clocks_65dca.l,pc),a0
 move.w #$4ef9,$65dca
 move.l a0,$65dcc
 lea (clocks_65dd8.l,pc),a0
 move.w #$4ef9,$65dd8
 move.l a0,$65dda
 lea clocks_installed(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #30,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
clocks_65dca:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 moveq #0,d6
 bsr.w clocks_before
 tst.w d0
 beq.b .skip
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 IFD FF1_PRESENTATION_SPLIT
 bsr.w FF1ClockTick
 ELSE
 jsr $22c3a
 ENDC
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
.skip:
 IFD VERIFY
 bsr.w clocks_after
 ENDC
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $65dd0
clocks_65dd8:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 moveq #1,d6
 bsr.w clocks_before
 tst.w d0
 beq.b .skip
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 IFD FF1_PRESENTATION_SPLIT
 bsr.w FF1ClockTick
 ELSE
 jsr $22c3a
 ENDC
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
.skip:
 IFD VERIFY
 bsr.w clocks_after
 ENDC
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $65dde
clocks_record:
 IFD VERIFY
 move.l clocks_samples(pc),d0
 cmpi.l #200,d0
 IFD VERIFY
 bhs.w velocity_fault
 ENDC
 lsl.l #5,d0
 lea (clocks_records.l,pc),a4
 adda.l d0,a4
 rts
 ELSE
 rts
 ENDC
clocks_pointer:
 IFD VERIFY
 lea $226c0,a0
 tst.w 4(a4)
 beq.b .done
 adda.w #10,a0
.done:
 rts
 ELSE
 rts
 ENDC
clocks_before:
 IFD VERIFY
 bsr.w clocks_record
 move.l ticks(pc),(a4)
 move.w d6,4(a4)
 moveq #1,d0
 cmpi.w #8,modeval(pc)
 bne.b .decided
 move.w events_pulse(pc),d0
.decided:
 move.w d0,6(a4)
 bsr.w clocks_pointer
 move.l (a0)+,8(a4)
 move.l (a0)+,12(a4)
 move.w (a0),16(a4)
 move.w 6(a4),d0
 rts
 ELSE
 moveq #1,d0
 cmpi.w #8,modeval(pc)
 bne.b .done
 move.w events_pulse(pc),d0
.done:
 rts
 ENDC
clocks_after:
 IFD VERIFY
 bsr.w clocks_record
 bsr.w clocks_pointer
 move.l (a0)+,18(a4)
 move.l (a0)+,22(a4)
 move.w (a0),26(a4)
 IFD VERIFY
 lea clocks_samples(pc),a0
 addq.l #1,(a0)
 ENDC
 rts
 ELSE
 rts
 ENDC
clocks_installed: dc.l 0
clocks_samples: dc.l 0
install_counters:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #7,d0
 blo.w .done
 cmpi.w #$5200,$6712e
 bne.w .bad
 cmpi.w #$0200,$67130
 bne.w .bad
 cmpi.w #$0003,$67132
 bne.w .bad
 cmpi.w #$5340,$67172
 bne.w .bad
 cmpi.w #$33c0,$67174
 bne.w .bad
 cmpi.w #$0006,$67176
 bne.w .bad
 cmpi.w #$6f94,$67178
 bne.w .bad
 cmpi.w #$0cb9,$6734e
 bne.w .bad
 cmpi.w #$0010,$67350
 bne.w .bad
 cmpi.w #$ffff,$67352
 bne.w .bad
 cmpi.w #$0006,$67354
 bne.w .bad
 cmpi.w #$6c42,$67356
 bne.w .bad
 cmpi.w #$3039,$673a4
 bne.w .bad
 cmpi.w #$0006,$673a6
 bne.w .bad
 cmpi.w #$6f92,$673a8
 bne.w .bad
 lea (counters_6712e.l,pc),a0
 move.w #$4ef9,$6712e
 move.l a0,$67130
 lea (counters_67172.l,pc),a0
 move.w #$4ef9,$67172
 move.l a0,$67174
 move.w #$4e71,$67178
 lea (counters_6734e.l,pc),a0
 move.w #$4ef9,$6734e
 move.l a0,$67350
 move.w #$4e71,$67354
 move.w #$4e71,$67356
 lea (counters_673a4.l,pc),a0
 move.w #$4ef9,$673a4
 move.l a0,$673a6
 lea counters_installed(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #31,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
counters_6712e:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 moveq #0,d6
 bsr.w counters_before
 tst.w d0
 beq.b .skip
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $5200,$0200,$0003
 bra.b .record
.skip:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 andi.b #3,d0
.record:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 moveq #0,d6
 move.b d0,$1be42
 IFD VERIFY
 bsr.w counters_after
 ENDC
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $67134
counters_67172:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 moveq #1,d6
 bsr.w counters_before
 tst.w d0
 beq.b .skip
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $5340,$33c0,$0006,$6f94
 bra.b .record
.skip:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 move.w d0,$66f94
.record:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 moveq #1,d6
 IFD VERIFY
 bsr.w counters_after
 ENDC
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6717a
counters_6734e:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 moveq #2,d6
 bsr.w counters_before
 tst.w d0
 beq.b .skip
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $0cb9,$0010,$ffff,$0006,$6c42
 jmp $67358
.skip:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $673a4
counters_673a4:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 moveq #2,d6
 IFD VERIFY
 bsr.w counters_after
 ENDC
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $3039,$0006,$6f92
 jmp $673aa
counters_record:
 IFD VERIFY
 move.l counters_samples(pc),d0
 cmpi.l #400,d0
 IFD VERIFY
 bhs.w velocity_fault
 ENDC
 lsl.l #4,d0
 lea (counters_records.l,pc),a4
 adda.l d0,a4
 rts
 ELSE
 rts
 ENDC
counters_value:
 IFD VERIFY
 moveq #0,d0
 tst.w d6
 bne.b .word
 move.b $1be42,d0
 rts
.word:
 move.w $66f94,d0
 cmpi.w #1,d6
 beq.b .done
 move.w $32f2e,d0
.done:
 rts
 ELSE
 rts
 ENDC
counters_before:
 IFD VERIFY
 bsr.w counters_record
 move.l ticks(pc),(a4)
 move.w d6,4(a4)
 bsr.w counters_value
 move.w d0,8(a4)
 moveq #1,d0
 cmpi.w #8,modeval(pc)
 bne.b .decided
 move.w events_pulse(pc),d0
.decided:
 move.w d0,6(a4)
 rts
 ELSE
 moveq #1,d0
 cmpi.w #8,modeval(pc)
 bne.b .done
 move.w events_pulse(pc),d0
.done:
 rts
 ENDC
counters_after:
 IFD VERIFY
 bsr.w counters_record
 bsr.w counters_value
 move.w d0,10(a4)
 IFD VERIFY
 lea counters_samples(pc),a0
 addq.l #1,(a0)
 ENDC
 rts
 ELSE
 rts
 ENDC
counters_installed: dc.l 0
counters_samples: dc.l 0
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
 lea (fuel_6d164.l,pc),a0
 move.w #$4ef9,$6d164
 move.l a0,$6d166
 lea (fuel_64ae6.l,pc),a0
 move.w #$4ef9,$64ae6
 move.l a0,$64ae8
 lea (fuel_6881e.l,pc),a0
 move.w #$4ef9,$6881e
 move.l a0,$68820
 lea (fuel_6c6a2.l,pc),a0
 move.w #$4ef9,$6c6a2
 move.l a0,$6c6a4
 lea (fuel_66942.l,pc),a0
 move.w #$4ef9,$66942
 move.l a0,$66944
 move.w #$4e71,$66948
 lea (fuel_6d242.l,pc),a0
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
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $9190
 dc.w $2d40,$fffc
 jmp $6d16a
.b3_player:
 ENDC
 IFD FF1_LEAN_PLAYER
 movem.l d1/a1,-(sp)
 lea fuel_remainders(pc),a1
 bsr.w FF1Wear20Delta
 movem.l (sp)+,d1/a1
 dc.w $9190,$2d40,$fffc
 jmp $6d16a
 ELSE
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l d0,d4
 move.l #$6d164,d6
 moveq #6,d7
 bsr.w fuel_sample
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 dc.w $9190,$2d40,$fffc
 jmp $6d16a
 ENDC
fuel_64ae6:
 dc.w $23c0,$0002,$2376
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 lea $22376,a0
 bsr.w fuel_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $64aec
fuel_6881e:
 dc.w $c1fc,$2710,$2080
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 bsr.w fuel_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68824
fuel_6c6a2:
 dc.w $c1fc,$2710,$2080
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 bsr.w fuel_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6c6a8
fuel_66942:
 dc.w $d1fc,$0002,$2376,$4290
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 bsr.w fuel_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6694a
fuel_6d242:
 dc.w $d1fc,$0002,$2376,$4290
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 bsr.w fuel_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $6d24a
fuel_context:
 move.l a0,d2
 subi.l #$22376,d2
 cmpi.l #32,d2
 IFD VERIFY
 bhs.w velocity_fault
 ENDC
 move.l d2,d3
 andi.l #3,d3
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 lsr.l #1,d2
 lea fuel_remainders(pc),a1
 adda.l d2,a1
 rts
fuel_reset:
 IFD FF1_PLAN_B
 cmpa.l #$22376,a0
 beq.b .b3_player
 rts
.b3_player:
 ENDC
 cmpi.w #8,modeval(pc)
 bne.b .done
 IFD FF1_PLAYER_HOOKS
 lea fuel_remainders(pc),a1
 ELSE
 bsr.w fuel_context
 ENDC
 IFD FF1_PLAYER_HOOKS
 clr.b (a1)
 ELSE
 clr.w (a1)
 ENDC
 IFD VERIFY
 lea fuel_resets(pc),a1
 addq.l #1,(a1)
 ENDC
.done:
 rts
fuel_sample:
 IFD VERIFY
 cmpi.w #8,modeval(pc)
 bne.w .done
 IFD FF1_PLAYER_HOOKS
 lea fuel_remainders(pc),a1
 ELSE
 bsr.w fuel_context
 ENDC
 move.l fuel_samples(pc),d2
 cmpi.l #4096,d2
 IFD VERIFY
 bhs.w velocity_fault
 ENDC
 lsl.l #5,d2
 lea (fuel_records.l,pc),a4
 adda.l d2,a4
 move.l d6,(a4)
 move.l a0,4(a4)
 move.l (a0),8(a4)
 move.l d4,12(a4)
 IFD FF1_PLAYER_HOOKS
 clr.w 20(a4)
 move.b (a1),21(a4)
 ELSE
 move.w (a1),20(a4)
 ENDC
 move.l ticks(pc),24(a4)
 move.l d4,d0
 bsr.w FF1Wear20Delta
 tst.l d1
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 move.l d0,16(a4)
 IFD FF1_PLAYER_HOOKS
 clr.w 22(a4)
 move.b (a1),23(a4)
 ELSE
 move.w (a1),22(a4)
 ENDC
 move.l d0,(sp,d7.l)
 IFD VERIFY
 lea fuel_samples(pc),a1
 addq.l #1,(a1)
 ENDC
.done:
 rts
 ELSE
 cmpi.w #8,modeval(pc)
 bne.b .done
 IFD FF1_PLAYER_HOOKS
 lea fuel_remainders(pc),a1
 ELSE
 bsr.w fuel_context
 ENDC
 move.l d4,d0
 bsr.w FF1Wear20Delta
 tst.l d1
 IFD VERIFY
 bne.w velocity_fault
 ENDC
 move.l d0,(sp,d7.l)
.done:
 rts
 ENDC
fuel_installed: dc.l 0
fuel_samples: dc.l 0
fuel_resets: dc.l 0
 IFND FF1_PLAYER_HOOKS
fuel_remainders: ds.w 8
 ENDC
boost_record:
 IFD VERIFY
 move.l boost_samples(pc),d0
 cmpi.l #100,d0
 IFD VERIFY
 bhs.w velocity_fault
 ENDC
 mulu.w #48,d0
 lea (boost_records.l,pc),a4
 adda.l d0,a4
 rts
 ELSE
 rts
 ENDC
boost_before:
 IFD VERIFY
 bsr.w boost_record
 move.l ticks(pc),(a4)
 moveq #1,d0
 cmpi.w #8,modeval(pc)
 bne.b .decided
 move.w events_pulse(pc),d0
.decided:
 move.w d0,4(a4)
 move.w $6f270,6(a4)
 move.w $1bf52,8(a4)
 move.w $66c76,10(a4)
 move.l $66c3e,12(a4)
 move.l $6bf84,20(a4)
 move.w $6bf82,28(a4)
 move.w $6f272,30(a4)
 movea.l $26600,a0
 move.l 12(a0),32(a4)
 move.l 20(a0),36(a4)
 move.w 4(a4),d0
 rts
 ELSE
 moveq #1,d0
 cmpi.w #8,modeval(pc)
 bne.b .done
 move.w events_pulse(pc),d0
.done:
 rts
 ENDC
boost_after:
 IFD VERIFY
 bsr.w boost_record
 move.w $66c76,16(a4)
 move.w $6bf82,18(a4)
 move.l $6bf84,24(a4)
 movea.l $26600,a0
 move.l 12(a0),40(a4)
 move.l 20(a0),44(a4)
 IFD VERIFY
 lea boost_samples(pc),a0
 addq.l #1,(a0)
 ENDC
 rts
 ELSE
 rts
 ENDC
boost_samples: dc.l 0
install_recovery:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #7,d0
 blo.w .done
 cmpi.w #$3039,$6c20c
 bne.w .bad
 cmpi.w #$0002,$6c20e
 bne.w .bad
 cmpi.w #$268e,$6c210
 bne.w .bad
 cmpi.w #$4279,$6c5de
 bne.w .bad
 cmpi.w #$0006,$6c5e0
 bne.w .bad
 cmpi.w #$a694,$6c5e2
 bne.w .bad
 cmpi.w #$48c0,$6c5f6
 bne.w .bad
 cmpi.w #$e380,$6c5f8
 bne.w .bad
 cmpi.w #$2040,$6c5fa
 bne.w .bad
 cmpi.w #$3010,$682c0
 bne.w .bad
 cmpi.w #$5340,$682c2
 bne.w .bad
 cmpi.w #$3080,$682c4
 bne.w .bad
 cmpi.w #$302e,$6c6ea
 bne.w .bad
 cmpi.w #$fff0,$6c6ec
 bne.w .bad
 cmpi.w #$48c0,$6c6ee
 bne.w .bad
 cmpi.w #$3039,$6c7c8
 bne.w .bad
 cmpi.w #$0006,$6c7ca
 bne.w .bad
 cmpi.w #$a694,$6c7cc
 bne.w .bad
 lea (recovery_6c20c.l,pc),a0
 move.w #$4ef9,$6c20c
 move.l a0,$6c20e
 lea (recovery_6c5de.l,pc),a0
 move.w #$4ef9,$6c5de
 move.l a0,$6c5e0
 lea (recovery_6c5f6.l,pc),a0
 move.w #$4ef9,$6c5f6
 move.l a0,$6c5f8
 lea (recovery_682c0.l,pc),a0
 move.w #$4ef9,$682c0
 move.l a0,$682c2
 lea (recovery_6c6ea.l,pc),a0
 move.w #$4ef9,$6c6ea
 move.l a0,$6c6ec
 lea (recovery_6c7c8.l,pc),a0
 move.w #$4ef9,$6c7c8
 move.l a0,$6c7ca
 lea recovery_installed(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #33,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
recovery_6c20c:
 move.w ccr,-(sp)
 cmpi.w #8,modeval(pc)
 beq.b .presentation
 move.w (sp)+,ccr
 move.w $2268e,d0
 jmp $6c212
.presentation:
 move.w (sp)+,ccr
 jmp $6c220
recovery_6c5de:
 move.w ccr,-(sp)
 tst.w recovery_simulation(pc)
 bne.b .simulation
 move.w (sp)+,ccr
 clr.w $6a694
 jmp $6c5e4
.simulation:
 move.w (sp)+,ccr
 jmp $6c5e4
recovery_6c5f6:
 move.w ccr,-(sp)
 cmpi.w #8,modeval(pc)
 bne.b .native
 tst.w recovery_simulation(pc)
 beq.b .presentation
.native:
 move.w (sp)+,ccr
 ext.l d0
 asl.l #1,d0
 movea.l d0,a0
 jmp $6c5fc
.presentation:
 move.w (sp)+,ccr
 jmp $6c6ea
recovery_6c6ea:
 move.w ccr,-(sp)
 tst.w recovery_simulation(pc)
 beq.b .native
 move.w (sp)+,ccr
 jmp $6c7c0
.native:
 move.w (sp)+,ccr
 move.w -$10(a6),d0
 ext.l d0
 jmp $6c6f0
recovery_6c7c8:
 move.w ccr,-(sp)
 tst.w recovery_simulation(pc)
 beq.b .native
 move.w (sp)+,ccr
 movem.l (sp)+,d2-d5
 unlk a6
 rts
.native:
 move.w (sp)+,ccr
 move.w $6a694,d0
 jmp $6c7ce
recovery_682c0:
 IFD FF1_PLAN_B
 tst.w $32fbc
 beq.b .b3_player
 dc.w $3010,$5340,$3080
 jmp $682c6
.b3_player:
 ENDC
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 IFD VERIFY
 bsr.w recovery_contact_before
 ENDC
 cmpi.w #8,modeval(pc)
 bne.b .run
 tst.w events_pulse(pc)
 beq.b .skip
.run:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 move.w (a0),d0
 subq.w #1,d0
 move.w d0,(a0)
 bra.b .record
.skip:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 move.w (a0),d0
.record:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 IFD VERIFY
 bsr.w recovery_contact_after
 ENDC
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $682c6
recovery_contact_record:
 IFD VERIFY
 move.l recovery_contacts(pc),d0
 cmpi.l #800,d0
 IFD VERIFY
 bhs.w velocity_fault
 ENDC
 lsl.l #4,d0
 lea (recovery_contact_records.l,pc),a4
 adda.l d0,a4
 rts
 ELSE
 rts
 ENDC
recovery_contact_before:
 IFD VERIFY
 bsr.w recovery_contact_record
 move.l ticks(pc),(a4)
 move.w $32fbc,4(a4)
 move.w (a0),8(a4)
 moveq #1,d0
 cmpi.w #8,modeval(pc)
 bne.b .store
 move.w events_pulse(pc),d0
.store:
 move.w d0,6(a4)
 rts
 ELSE
 rts
 ENDC
recovery_contact_after:
 IFD VERIFY
 bsr.w recovery_contact_record
 move.w (a0),10(a4)
 IFD VERIFY
 lea recovery_contacts(pc),a1
 addq.l #1,(a1)
 ENDC
 rts
 ELSE
 rts
 ENDC
recovery_record:
 IFD VERIFY
 move.l recovery_samples(pc),d0
 cmpi.l #100,d0
 IFD VERIFY
 bhs.w velocity_fault
 ENDC
 mulu.w #256,d0
 lea (recovery_records.l,pc),a4
 adda.l d0,a4
 rts
 ELSE
 rts
 ENDC
recovery_snapshot:
 IFD VERIFY
 lea $2268e,a0
 moveq #7,d0
.status:
 move.w (a0)+,(a1)+
 dbra d0,.status
 lea $22356,a0
 moveq #15,d0
.fueltyre:
 move.l (a0)+,(a1)+
 dbra d0,.fueltyre
 lea $22604,a0
 moveq #7,d0
.flags:
 move.b (a0)+,(a1)+
 dbra d0,.flags
 IFD FF1_PLAYER_HOOKS
 clr.w (a1)+
 move.b fuel_remainders(pc),-1(a1)
 moveq #14,d0
.emptycarry:
 clr.w (a1)+
 dbra d0,.emptycarry
 ELSE
 lea fuel_remainders(pc),a0
 moveq #7,d0
.fuelcarry:
 move.w (a0)+,(a1)+
 dbra d0,.fuelcarry
 lea wear_remainders+8(pc),a0
 moveq #7,d0
.tyrecarry:
 move.w (a0)+,(a1)+
 dbra d0,.tyrecarry
 ENDC
 rts
 ELSE
 rts
 ENDC
recovery_tick:
 IFD VERIFY
 cmpi.w #7,modeval(pc)
 blo.w .done
 bsr.w recovery_record
 move.l ticks(pc),(a4)
 moveq #1,d0
 cmpi.w #8,modeval(pc)
 bne.b .pulse
 move.w events_pulse(pc),d0
.pulse:
 move.w d0,4(a4)
 move.w $1c21e,6(a4)
 move.w $66c7c,8(a4)
 move.w $66f94,10(a4)
 move.w $1c222,12(a4)
 lea 16(a4),a1
 bsr.w recovery_snapshot
 tst.w 4(a4)
 beq.b .after
 lea $2268e,a0
 moveq #1,d0
 bsr.w FF1AdvanceRecovery
 tst.w $1c21e
 bne.b .after
 lea recovery_simulation(pc),a0
 move.w #1,(a0)
 jsr $6c5c6
 lea recovery_simulation(pc),a0
 clr.w (a0)
.after:
 bsr.w recovery_record
 lea 136(a4),a1
 bsr.w recovery_snapshot
 IFD VERIFY
 lea recovery_samples(pc),a0
 addq.l #1,(a0)
 ENDC
.done:
 rts
 ELSE
 cmpi.w #7,modeval(pc)
 blo.b .done
 cmpi.w #8,modeval(pc)
 bne.b .run
 tst.w events_pulse(pc)
 beq.b .done
.run:
 lea $2268e,a0
 moveq #1,d0
 bsr.w FF1AdvanceRecovery
 tst.w $1c21e
 bne.b .done
 lea recovery_simulation(pc),a0
 move.w #1,(a0)
 jsr $6c5c6
 lea recovery_simulation(pc),a0
 clr.w (a0)
.done:
 rts
 ENDC
recovery_installed: dc.l 0
recovery_contacts: dc.l 0
recovery_samples: dc.l 0
recovery_simulation: dc.w 0
 include "FerrariFormulaOne_Logic.s"

schedule_install:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.l #$33c10002,$24946
 bne.w schedule_bad
 cmpi.w #$4ad2,$2494a
 bne.w schedule_bad
 lea (schedule_context.l,pc),a0
 moveq #20,d0
 bsr.w FF1TimeInit
 move.l $4.w,a6
 jsr -120(a6)
 lea (schedule_vbl.l,pc),a0
 move.w #$4eb9,$24946
 move.l a0,$24948
 lea (start.l,pc),a2
 suba.l #FF1_HOST_CODE_SIZE,a2
 IFD FF1_PRODUCTION
 move.l FF1_HOST_RESLOAD(a2),a2
 ELSE
 move.l $1180(a2),a2
 ENDC
 jsr $20(a2)
 move.l $4.w,a6
 jsr -126(a6)
 movem.l (sp)+,d0-d7/a0-a6
 rts
schedule_bad:
 lea error(pc),a0
 move.l #35,(a0)
 bra.w velocity_fault
schedule_vbl:
 move.w d1,$24ad2
 movem.l d0-d3/a0-a1,-(sp)
 move.w ccr,-(sp)
 lea (schedule_context.l,pc),a0
 bsr.w FF1TimeField
 IFD FF1_FAST_RENDER
 bsr.l FF1FastRenderVbl
 ENDC
 IFD FF1_FAST_RENDER_PACING
 bsr.l FR8Vbl
 ENDC
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d3/a0-a1
 rts
schedule_record:
 move.l schedule_completed(pc),d0
 cmpi.l #100,d0
 bhs.w schedule_stop
 mulu.w #32,d0
 lea (schedule_records.l,pc),a4
 adda.l d0,a4
 rts
schedule_begin:
 IFND FF1_PRODUCTION
 cmpi.l #126,ticks(pc)
 blo.w .done
 ENDC
 lea (schedule_context.l,pc),a0
.wait:
 bsr.w FF1TimeDue
 tst.l d0
 beq.b .wait
 IFD VERIFY
 IFD VERIFY
 bsr.w schedule_record
 ENDC
 move.l FF1T_FIELDS(a0),(a4)
 move.l d2,8(a4)
 move.l d1,12(a4)
 move.l ticks(pc),24(a4)
 ENDC
 ; Preview this tick's native pulse. Only schedule_end commits elapsed time.
 move.w FF1T_PHASE_MS(a0),d0
 addi.w #20,d0
 lea events_pulse(pc),a1
 clr.w (a1)
 cmpi.w #100,d0
 blo.b .done
 move.w #1,(a1)
 IFD VERIFY
 lea events_pulses(pc),a1
 addq.l #1,(a1)
 ENDC
.done:
 IFD FF1_FAST_RENDER_PACING
 bsr.l FR8MarkBegin
 ENDC
 rts
schedule_end:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 IFD VERIFY
 bsr.w schedule_record
 ENDC
 lea (schedule_context.l,pc),a0
 IFD VERIFY
 move.l FF1T_FIELDS(a0),4(a4)
 ENDC
 bsr.w FF1TimeConsume
 IFD VERIFY
 move.l d0,28(a4)
 ENDC
 IFD VERIFY
 cmp.w events_pulse(pc),d0
 bne.w schedule_bad
 ENDC
 IFD VERIFY
 bsr.w FF1TimeDue
 move.l d2,16(a4)
 move.l d1,20(a4)
 lea schedule_completed(pc),a1
 addq.l #1,(a1)
 ENDC
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 ; Optional host presentation hook: preserve every register and CCR.
 ; It runs after consumption, outside the measured simulation body.
 IFD FF1_PRESENTATION_CALLBACK
 bsr.w FF1PresentationAfterTick
 ENDC
 jmp $65174
schedule_stop:
 bra.b schedule_stop
 IFD VERIFY
schedule_completed: dc.l 0
 ELSE
schedule_completed equ schedule_context+FF1T_TICKS
 ENDC
 include "FerrariFormulaOne_Time.s"
schedule_context: ds.b FF1T_SIZE

 IFD FF1_PRESENTATION_SPLIT
 include "FerrariFormulaOne_Presentation.s"
 ENDC

 IFD FF1_PLAN_B
 include "FerrariFormulaOne_Opponents.s"
 ENDC
