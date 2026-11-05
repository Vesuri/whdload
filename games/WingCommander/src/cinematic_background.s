; Running-pilot shots draw two 320-pixel tiles. The native scroll keeps
; decreasing for the whole field-timed shot, so fast draws exhaust both tiles.
; Wrap each tile's draw coordinate over the full 640-pixel pair, preserving
; the upper shot's alternating tile identities. Do not wrap the pilot motion.
; C bitmap ABI: return.l, surface.l, x.w, y.w, image.l, frame.w.
cinematic_background:
        move.w  8(sp),d0
.left:
        cmpi.w  #-319,d0
        bge.s   .right
        addi.w  #640,d0
        bra.s   .left
.right:
        cmpi.w  #320,d0
        ble.s   .draw
        subi.w  #640,d0
        bra.s   .right
.draw:
        move.w  d0,8(sp)         ; this call's disposable argument only
        CINEMATIC_DRAW
