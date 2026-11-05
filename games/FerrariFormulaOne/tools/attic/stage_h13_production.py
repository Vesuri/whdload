from pathlib import Path
r=Path(__file__).resolve().parents[1];s=(r/'tmp/build/render-h13-probe-source/FerrariFormulaOne/Fine.s').read_text();s=s[s.index('H13Install:\n'):s.index('H13Control: dc.w 1')+len('H13Control: dc.w 1')];s=s.replace('H13Install','FF1RenderInstallCockpit').replace('H13Blit','FF1RenderCockpit').replace('H13Control','FF1RenderCockpitControl')
s=s.replace('FF1RenderInstallCockpit:\n','''FF1RenderInstallCockpit:
 lea start(pc),a0
 suba.l #FF1_HOST_CODE_SIZE,a0
 move.l FF1_HOST_ATTN(a0),d0
 andi.l #$8c,d0
 beq.b .done
 cmpi.w #$33c0,$6bbe6
 bne.l FF1ProductionFault
 cmpi.l #$00dff058,$6bbe8
 bne.l FF1ProductionFault
''')
s=s.replace(' movem.l d0-d7/a0-a5,-(sp)\n',''' movem.l d0-d7/a0-a5,-(sp)
 ; Retain native BLTSIZE semantics for zero/oversized rectangles.
 move.w d0,d1
 andi.w #63,d1
 beq.w .native
 cmpi.w #25,d1
 bhi.w .native
 move.w d0,d1
 lsr.w #6,d1
 beq.w .native
 cmpi.w #200,d1
 bhi.w .native
''')
s=s.replace('FF1RenderCockpitControl: dc.w 1','''.native:
 movem.l (sp)+,d0-d7/a0-a5
 move.w (sp)+,ccr
 move.w d0,$dff058
 rts
; Immutable equal-layout measurement preset, outside lifecycle reset ranges.
FF1RenderCockpitControl: dc.w 1''')
s='''; H13: exact CPU cockpit cookie-cut after the native clipping and WaitBlit.
; Read live mask/source data. Opaque words copy without reading the destination;
; transparent words leave it untouched. The native last mask is always zero.
; Native plane loops, geometry, ownership and subsequent waits remain in place.
'''+s+'\n';(r/'tmp/RenderCockpit.s').write_text(s)
