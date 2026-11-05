 include "timing-offsets.i"
; Native 0658 geometry selection with private scratch; not installed.
; Requires timing-scene-state.i. Only validated native model data is supported.
; Native model/map/actor inputs remain read-only shared inputs and must be
; stable throughout a step. This is not a transactional snapshot of the world.
SCENE_START equ GS0_5a24
SCENE_CODE_SIZE equ $1d94
SCENE_COORD equ SCENE_CODE_SIZE
SCENE_CONTEXT equ SCENE_COORD+$b8
SCENE_H0 equ SCENE_CONTEXT+$64
SCENE_H6 equ SCENE_H0+4
SCENE_SIZE equ SCENE_H6+4

; a0=validated hunk 0, a1=validated hunk 6, a2=even SCENE_SIZE workspace.
; Preserve other registers, return 0/-1. No writes on signature failure.
; Buffers must not overlap; flush instruction caches before first execution.
scene_private_prepare:
 movem.l d1-d7/a0-a6,-(sp)
 movea.l a0,a4
 movea.l a1,a5
 movea.l a2,a6
 ; World geometry must retain committed heading reads. Refuse a source
 ; already patched for presentation, even if every private relocation still
 ; matches. Shared absolute reads are not covered by the relocation table.
 lea $3ce3(a5),a0
 cmpi.w #$1239,GS0_5d20(a4)
 bne .bad
 cmpa.l GS0_5d22(a4),a0
 bne .bad
 cmpi.w #$1439,GS0_68a2(a4)
 bne .bad
 cmpa.l GS0_68a4(a4),a0
 bne .bad
 cmpi.w #$1439,GS0_68d2(a4)
 bne .bad
 cmpa.l GS0_68d4(a4),a0
 bne .bad
 cmpi.w #$7000,GS0_63f8(a4)
 bne .bad
 cmpi.l #$242d004c,GS0_6372(a4)
 bne .bad
 cmpi.w #$41f9,GS0_6642(a4)
 bne .bad
 cmpi.w #$4eb9,GS0_6356(a4)
 bne .bad
 movea.l a4,a0
 adda.l #GS0_a450,a0
 cmpa.l GS0_6358(a4),a0
 bne .bad
 cmpi.w #$4eb9,GS0_5c5c(a4)
 bne .bad
 lea GS0_77b8(a4),a0
 cmpa.l GS0_5c5e(a4),a0
 bne .bad
 lea scene_private_relocs(pc),a3
 move.w #150,d7
.check:
 moveq #0,d1
 move.w (a3)+,d1
 movea.l a4,a0
 tst.w (a3)+
 beq .h0
 movea.l a5,a0
.h0:
 moveq #0,d2
 move.w (a3)+,d2
 adda.l d2,a0
 addq.l #2,a3
 lea SCENE_START(a4),a1
 cmpa.l 0(a1,d1.w),a0
 bne .bad
 dbf d7,.check
 lea SCENE_START(a4),a0
 movea.l a6,a1
 move.w #SCENE_CODE_SIZE/2-1,d7
.copy:
 move.w (a0)+,(a1)+
 dbf d7,.copy
 lea $18dc(a5),a0
 moveq #$b8/2-1,d7
.coords:
 move.w (a0)+,(a1)+
 dbf d7,.coords
 moveq #$64/2-1,d7
.context:
 clr.w (a1)+
 dbf d7,.context
 move.l a4,(a1)+
 move.l a5,(a1)+
 lea scene_private_relocs(pc),a3
 move.w #150,d7
.patch:
 moveq #0,d1
 move.w (a3)+,d1
 addq.l #4,a3
 moveq #0,d2
 move.w (a3)+,d2
 movea.l a6,a0
 adda.l d2,a0
 move.l a0,0(a6,d1.w)
 dbf d7,.patch
 move.w #$4e75,GS0_5c5c-SCENE_START(a6)
 move.w #$4e75,GS0_63f8-SCENE_START(a6)
 move.l #$6000ffe8,GS0_6372-SCENE_START(a6)
 move.l #$4e714e71,GS0_6356-SCENE_START(a6)
 move.w #$4e71,GS0_635a-SCENE_START(a6)
 lea .vertices(pc),a0
 lea GS0_6642-SCENE_START(a6),a1
 moveq #6,d7
.vertex_copy:
 move.w (a0)+,(a1)+
 dbf d7,.vertex_copy
 moveq #0,d0
 bra .done
.bad:
 moveq #-1,d0
.done:
 movem.l (sp)+,d1-d7/a0-a6
 rts
.vertices:
 move.b (a2,d5.w),d0
 cmpi.b #$ff,d0
 bne.s .vertex_done
 addq.l #2,a2
.vertex_done:
 rts

; a0=prepared workspace, a1=committed camera, a2=committed object coordinates.
; Return 0/1 native final flag, -1 missing bindings; preserve other registers.
; Builds fresh context/transforms, evaluates both native selection passes.
; Only workspace/stack writes. No native player mutation or flight-end cleanup.
; Do not use predicted poses. Native view/LOD/last-nonempty-shape semantics stay.
scene_private_step:
 movem.l d1-d7/a0-a6,-(sp)
 movea.l a0,a6
 tst.l SCENE_H0(a6)
 beq .bad
 tst.l SCENE_H6(a6)
 beq .bad
 ; Preparation runs before flight initialization. The native coordinate
 ; table's transform ranges are initialized later and can change between
 ; flights. Refresh the source table before rebuilding committed actor
 ; coordinates; never retain the loader-time ranges or transformed scratch.
 movea.l SCENE_H6(a6),a3
 lea $18dc(a3),a3
 lea SCENE_COORD(a6),a4
 moveq #$b8/2-1,d1
.coords:
 move.w (a3)+,(a4)+
 dbf d1,.coords
 movea.l a1,a0
 movea.l a2,a1
 movea.l SCENE_H6(a6),a2
 lea SCENE_CONTEXT+14(a6),a3
 bsr scene_state_build
 lea SCENE_CONTEXT(a6),a5
 lea $15dc(a2),a0
 move.l a0,$5e(a5)
 clr.b $62(a5)
 lea GS0_5c2e-SCENE_START(a6),a0
 jsr (a0)
 lea GS0_60a8-SCENE_START(a6),a0
 jsr (a0)
 lea GS0_6224-SCENE_START(a6),a0
 jsr (a0)
 moveq #0,d0
 move.b $62(a5),d0
 andi.w #1,d0
 bra .done
.bad:
 moveq #-1,d0
.done:
 movem.l (sp)+,d1-d7/a0-a6
 rts

; Verified HUNK relocation entries: code offset, source hunk (0/6),
; source offset, private destination offset. No guessed pointer scanning.
scene_private_relocs:
 dc.w $01e6,6,$38f6,$1e4c
 dc.w $01fc,0,GS0_6980,$0f5c
 dc.w $0206,6,$3958,$1eae
 dc.w $0228,0,GS0_5f8e,$056a
 dc.w $022e,0,GS0_5cbe,$029a
 dc.w $0234,0,GS0_5ea4,$0480
 dc.w $0248,0,GS0_60a8,$0684
 dc.w $025c,0,GS0_6224,$0800
 dc.w $029e,6,$18dd,$1d95
 dc.w $02a4,0,GS0_77ac,$1d88
 dc.w $02aa,6,$18dc,$1d94
 dc.w $02b0,0,GS0_77ae,$1d8a
 dc.w $02b6,6,$191d,$1dd5
 dc.w $02bc,0,GS0_77b0,$1d8c
 dc.w $02c2,6,$191c,$1dd4
 dc.w $02c8,0,GS0_77b2,$1d8e
 dc.w $02ce,6,$1967,$1e1f
 dc.w $02d4,0,GS0_77b4,$1d90
 dc.w $02da,6,$1966,$1e1e
 dc.w $02e0,0,GS0_77b6,$1d92
 dc.w $02e8,0,GS0_7794,$1d70
 dc.w $02ee,0,GS0_5d62,$033e
 dc.w $0308,0,GS0_7794,$1d70
 dc.w $0310,0,GS0_77ac,$1d88
 dc.w $0316,0,GS0_77ae,$1d8a
 dc.w $031e,0,GS0_77b0,$1d8c
 dc.w $0324,0,GS0_77b2,$1d8e
 dc.w $032c,0,GS0_77b4,$1d90
 dc.w $0332,0,GS0_77b6,$1d92
 dc.w $0338,0,GS0_5d62,$033e
 dc.w $0344,0,GS0_7794,$1d70
 dc.w $0360,0,GS0_7794,$1d70
 dc.w $0372,0,GS0_77ac,$1d88
 dc.w $0378,0,GS0_77ae,$1d8a
 dc.w $0382,6,$18de,$1d96
 dc.w $038c,0,GS0_7312,$18ee
 dc.w $0394,0,GS0_7296,$1872
 dc.w $039c,0,GS0_721a,$17f6
 dc.w $03dc,0,GS0_77b0,$1d8c
 dc.w $03e2,0,GS0_77b2,$1d8e
 dc.w $03ec,6,$191e,$1dd6
 dc.w $03f6,0,GS0_738e,$196a
 dc.w $03fe,0,GS0_741e,$19fa
 dc.w $0406,0,GS0_74ae,$1a8a
 dc.w $0438,0,GS0_77b4,$1d90
 dc.w $043e,0,GS0_77b6,$1d92
 dc.w $0448,6,$1968,$1e20
 dc.w $0452,0,GS0_7592,$1b6e
 dc.w $045a,0,GS0_753e,$1b1a
 dc.w $0482,6,$1992,$1e4a
 dc.w $048e,0,GS0_721a,$17f6
 dc.w $0494,0,GS0_738e,$196a
 dc.w $049a,0,GS0_753e,$1b1a
 dc.w $04a0,0,GS0_6aca,$10a6
 dc.w $0504,6,$1992,$1e4a
 dc.w $0516,0,GS0_6aca,$10a6
 dc.w $051c,0,GS0_6d3a,$1316
 dc.w $0522,0,GS0_6faa,$1586
 dc.w $0594,0,GS0_5b22,$00fe
 dc.w $059e,0,GS0_77a2,$1d7e
 dc.w $05aa,0,GS0_5b2c,$0108
 dc.w $05fc,6,$18e8,$1da0
 dc.w $060a,6,$192a,$1de2
 dc.w $0618,6,$196e,$1e26
 dc.w $0624,6,$18ea,$1da2
 dc.w $0664,6,$18e8,$1da0
 dc.w $0686,0,GS0_7798,$1d74
 dc.w $068c,0,GS0_7797,$1d73
 dc.w $0694,0,GS0_5bbc,$0198
 dc.w $069c,0,GS0_5b22,$00fe
 dc.w $06b4,0,GS0_7799,$1d75
 dc.w $06ce,0,GS0_7796,$1d72
 dc.w $06e8,0,GS0_5b00,$00dc
 dc.w $06f6,0,GS0_5b03,$00df
 dc.w $06fc,0,GS0_6ac6,$10a2
 dc.w $0704,0,GS0_625c,$0838
 dc.w $0710,0,GS0_7797,$1d73
 dc.w $071a,0,GS0_5b22,$00fe
 dc.w $0720,0,GS0_5b74,$0150
 dc.w $0738,0,GS0_7799,$1d75
 dc.w $0750,0,GS0_7796,$1d72
 dc.w $0768,0,GS0_5b01,$00dd
 dc.w $0770,0,GS0_5b02,$00de
 dc.w $0778,0,GS0_625c,$0838
 dc.w $0786,0,GS0_7797,$1d73
 dc.w $07c6,0,GS0_7796,$1d72
 dc.w $07ce,0,GS0_5b02,$00de
 dc.w $07d4,0,GS0_5acc,$00a8
 dc.w $07e6,0,GS0_779a,$1d76
 dc.w $07ec,0,GS0_5b00,$00dc
 dc.w $07f4,0,GS0_6ac6,$10a2
 dc.w $07fa,0,GS0_625c,$0838
 dc.w $0804,0,GS0_7796,$1d72
 dc.w $080a,0,GS0_5ad2,$00ae
 dc.w $081c,0,GS0_7798,$1d74
 dc.w $0826,0,GS0_5b02,$00de
 dc.w $082c,0,GS0_6ac6,$10a2
 dc.w $0832,0,GS0_625c,$0838
 dc.w $083a,0,GS0_5b02,$00de
 dc.w $0862,0,GS0_6faa,$1586
 dc.w $0872,0,GS0_5b0e,$00ea
 dc.w $088e,0,GS0_6d3a,$1316
 dc.w $08a4,0,GS0_6aca,$10a6
 dc.w $08ba,0,GS0_5b04,$00e0
 dc.w $08e4,0,GS0_5afe,$00da
 dc.w $08f4,0,GS0_5b18,$00f4
 dc.w $0904,0,GS0_6ac8,$10a4
 dc.w $0918,0,GS0_5a24,$0000
 dc.w $0926,0,GS0_63dc,$09b8
 dc.w $092c,0,GS0_7797,$1d73
 dc.w $093a,0,GS0_6ac6,$10a2
 dc.w $0944,0,GS0_7796,$1d72
 dc.w $0954,0,GS0_768e,$1c6a
 dc.w $096c,0,GS0_66e8,$0cc4
 dc.w $0972,0,GS0_76e2,$1cbe
 dc.w $0978,0,GS0_770c,$1ce8
 dc.w $0986,0,GS0_7798,$1d74
 dc.w $0998,0,GS0_6ac6,$10a2
 dc.w $09c0,0,GS0_6642,$0c1e
 dc.w $09d0,0,GS0_6818,$0df4
 dc.w $09e8,0,GS0_768e,$1c6a
 dc.w $09ee,0,GS0_6a74,$1050
 dc.w $09f4,0,GS0_76e2,$1cbe
 dc.w $0a06,0,GS0_778a,$1d66
 dc.w $0aac,0,GS0_6792,$0d6e
 dc.w $0ab8,0,GS0_6984,$0f60
 dc.w $0af2,0,GS0_6a74,$1050
 dc.w $0afe,0,GS0_6984,$0f60
 dc.w $0b4e,0,GS0_778a,$1d66
 dc.w $0b5e,0,GS0_6ab0,$108c
 dc.w $0b70,0,GS0_6984,$0f60
 dc.w $0b98,0,GS0_6ab0,$108c
 dc.w $0b9e,0,GS0_6ab2,$108e
 dc.w $0ba8,0,GS0_6ab0,$108c
 dc.w $0bc0,0,GS0_6ab0,$108c
 dc.w $0bd2,0,GS0_69fc,$0fd8
 dc.w $0bd8,0,GS0_6ab2,$108e
 dc.w $0bea,0,GS0_6ab4,$1090
 dc.w $0c20,0,GS0_6aca,$10a6
 dc.w $0c26,0,GS0_75e6,$1bc2
 dc.w $0cd8,0,GS0_7736,$1d12
 dc.w $0d2a,0,GS0_5af6,$00d2
 dc.w $0d5e,0,GS0_5af8,$00d4
 dc.w $0d7c,0,GS0_768e,$1c6a
 dc.w $0dde,0,GS0_66e8,$0cc4
 dc.w $0de4,0,GS0_7708,$1ce4
 dc.w $0dec,0,GS0_7732,$1d0e
 dc.w $0df6,0,GS0_778a,$1d66
 dc.w $0e28,6,$18de,$1d96
 dc.w $0e64,0,GS0_6ac6,$10a2
 dc.w $0efa,6,$3958,$1eae
