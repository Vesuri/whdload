; FR0 benchmark data, appended after public_bindings (outside the binding scan).
 cnop 0,4
FR0Mask:
 rept 13*57
 dc.w $5af3
 endr
 cnop 0,4
FR0Buffer:
 rept (3*FR0_PLANE+16)/4
 dc.l $a5a5a5a5
 endr
