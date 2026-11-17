; Player bolts' near plane (CD32 E:2a086, OCS O:290fa): the projection culls
; a slot until it is past the near plane, 256 times the radius of the ship
; the view belongs to (E:713e, O:6eb4): 100 in the Hornet, 180 in the first
; Gimle mission's ship. A bolt leaves its gun mount inside that radius, so a
; wide ship's bolts first appeared well inside the screen, up to six fields
; after leaving the gun, while a Hornet's show from the canopy edges. In the
; forward view the player's own cannon bolts (class 8, shooter slot 0) now
; use at most the Hornet's plane; every other object, view and the intro
; keep the native one.
;
; OCS (O:291da/29224, assembled with NEAR_OCS set) is the same source with OCS
; A4 offsets. Both sites replace "moveq #0,d0; move.w near(a4),d0" (6 bytes)
; before "asl.l #8,d0"; d2 is the slot. d0 = the near plane, zero-extended;
; keeps every other register (the flags are set again by the asl).

PLAYER_BOLT_NEAR = 100          ; the Hornet's radius

        ifd     NEAR_OCS
NEAR_PLANE = 4868
NEAR_CLASS = 3726
NEAR_OWNER = 12376
NEAR_VIEW = -18318
        else
NEAR_PLANE = A_7030
NEAR_CLASS = A_5888
NEAR_OWNER = A_14954
NEAR_VIEW = A_m18280
        endc

near_plane:
        moveq   #0,d0
        move.w  NEAR_PLANE(a4),d0
        cmpi.w  #PLAYER_BOLT_NEAR,d0
        bls.s   .done
        move.l  a0,-(sp)
        lea     intro_active(pc),a0
        tst.w   (a0)
        bne.s   .native
        tst.w   NEAR_VIEW(a4)           ; 0: the forward view
        bne.s   .native
        lea     NEAR_CLASS(a4),a0
        adda.w  d2,a0
        cmpi.w  #8,(a0,d2.w)            ; cannon bolt
        bne.s   .native
        lea     NEAR_OWNER(a4),a0
        tst.b   (a0,d2.w)               ; shooter: the player is slot 0
        bne.s   .native
        moveq   #PLAYER_BOLT_NEAR,d0
.native:
        movea.l (sp)+,a0
.done:
        rts
