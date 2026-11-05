; Private input controller: a fixed mouse X while the road cursor is on the loop (37..48).
_private_loop_input:
 move.l d0,-(a7)
 move.l -$671c(a4),d0
 sub.l -$66ae(a4),d0
 cmpi.l #37*20,d0
 blo .done
 cmpi.l #49*20,d0
 bhs .done
 move.w #PRIVATE_LOOP_MOUSE,-$6a06(a4)
.done:
 move.l (a7)+,d0
 rts
 cnop 0,4
