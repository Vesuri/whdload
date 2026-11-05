; Rendering sets E94A for road and E94B for object surfaces. A culled road
; can still support the car (notably inside the loop). Query its geometry
; when there is no object surface, rather than substituting the flat ground.
; Keep zero-time, forced-native and eight-field branch selection unchanged.
_private_terrain_select:
 tst.b -$16b6(a4)
 bne .road
 IFD VERIFY_DISPATCH_NATIVE
 bra.s .native
 ELSE
 move.w _time_scalar_fields(pc),d0
 beq .native
 cmpi.w #8,d0
 beq .native
 tst.b -$16b5(a4)
 bne .native
 movem.l d1-d7/a1-a3,-(a7)
 lea _private_road_selected(pc),a0
 clr.w (a0)
 move.b #1,-$6bb9(a4)
 movea.l _phase_steering_body(pc),a0
 adda.l #$c022-$b398,a0
 jsr (a0)
 bsr _private_road_mask
 lea -$6bac(a4),a1
 bsr _private_road_bounds
 movem.l (a7)+,d1-d7/a1-a3
 tst.w d0
 beq .native
 ENDC
.road:
 ; Reuse the installed B398 address to reach the two native continuations.
 movea.l _phase_steering_body(pc),a0
 adda.l #$cdc4-$b398,a0
 jmp (a0)
.native:
 movea.l _phase_steering_body(pc),a0
 adda.l #$cdca-$b398,a0
 jmp (a0)


; Preserve the displaced native writes and final MOVE.W condition codes.
_private_road_selected_hook:
 move.l a0,-(a7)
 lea _private_road_selected(pc),a0
 move.w d4,(a0)
 movea.l (a7)+,a0
 move.l a2,-70(a5)
 move.w d5,-62(a5)
 rts
_private_road_selected: dc.w 0

; Only straight indexing within one course list is proven here. Crossing a
; list boundary retains native fallback until the native links are mirrored.
; D2 permits the first/second quad with bits1/0 respectively.
_private_road_mask:
 moveq #0,d2
 move.w _private_road_selected(pc),d0
 cmpi.w #1,d0
 blo.s .done
 cmpi.w #2,d0
 bhi.s .done
 movea.l -$6720(a4),a0
 movea.l -$50da(a4),a2
 tst.b -$66b0(a4)
 beq.s .list
 movea.l -$66ae(a4),a0
 movea.l -$50d6(a4),a2
.list:
 movea.l -$671c(a4),a3
 suba.w #40,a3
 cmpa.l a0,a3
 blo.s .done
 adda.w #100,a3
 cmpa.l a2,a3
 bhi.s .done
 movea.l -$671c(a4),a3
 subq.w #3,d0
 muls.w #20,d0
 adda.l d0,a3
 btst #2,18(a3)
 bne.s .second
 bset #1,d2
.second:
 btst #2,38(a3)
 bne.s .done
 bset #0,d2
.done:
 rts
