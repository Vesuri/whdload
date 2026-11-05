from pathlib import Path
r=Path(__file__).resolve().parents[1];s=(r/'tmp/build/render-h13-gauge-source/FerrariFormulaOne/Fine.s').read_text();s=s[s.index('H13Install:\n'):s.index('H13Control: dc.w 1')+len('H13Control: dc.w 1')];s=s.replace('H13Install','FF1RenderInstallGauges').replace('H13Gauge','FF1RenderGaugeStrip').replace('H13Control','FF1RenderGaugeControl')
s=s.replace('FF1RenderInstallGauges:\n','''FF1RenderInstallGauges:
 lea start(pc),a0
 suba.l #FF1_HOST_CODE_SIZE,a0
 move.l FF1_HOST_ATTN(a0),d0
 andi.l #$8c,d0
 beq.b .done
 cmpi.w #$4eb9,$6bd66
 bne.l FF1ProductionFault
 cmpi.l #$24ae0,$6bd68
 bne.l FF1ProductionFault
 cmpi.w #$4eb9,$6bdb6
 bne.l FF1ProductionFault
 cmpi.l #$24ae0,$6bdb8
 bne.l FF1ProductionFault
''')
s=s.replace(' move.w 38(a6),d0',''' move.l 4(a6),a0
 cmpa.l #$255be,a0
 beq.b .source
 cmpa.l #$255da,a0
 bne.w .fallback
.source:
 move.w 38(a6),d0''')
s='''; H13: bounded one-row monochrome gauge strips on 030/040/060+Fast.
; Two native call sites draw live source pixels into the cockpit's Chip planes.
; Preserve the native ownership boundary and finish through its DisownBlitter.
; All other dimensions, colours and destinations retain the general operation.
'''+s+'\n';(r/'tmp/RenderGauges.s').write_text(s)
