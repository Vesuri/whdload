from pathlib import Path
import json
r=Path(__file__).resolve().parents[1];p=r.parents[1]/'Games/FerrariFormulaOne_NativeExact.s';s=p.read_text();assert 'FF1NativeMultiply:' not in s
mem=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
s=s.replace(' lea FF1NativeSites(pc),a0\n.check:', ''' ifgt FF1_NATIVE_EXACT-4
 lea FF1MultiplySignature(pc),a0
 lea $29500,a1
 moveq #32,d1
.multiply_check:
 move.w (a0)+,d2
 cmp.w (a1)+,d2
 bne.w .bad
 dbra d1,.multiply_check
 endc
 lea FF1NativeSites(pc),a0
.check:''')
s=s.replace(' tst.w d2\n bmi.b .guarded',' btst #13,d2              ; guard-only proof fragment\n bne.b .patch\n tst.w d2\n bmi.b .guarded')
s=s.replace('.complete:\n', '''.complete:
 ifgt FF1_NATIVE_EXACT-4
 lea FF1NativeMultiply(pc),a0
 move.w #$4ef9,$29500
 move.l a0,$29502
 endc
''')
helper=''' ifgt FF1_NATIVE_EXACT-4
; Exact native multiply ABI, including its unusual CCR contract. This catches
; remaining callers where flags cannot simply be discarded. D1-D3 preserved.
; For same-sign nonzero operands, native X is the carry of its FINAL partial
; product add, not full-product overflow. Reconstruct that carry from the low
; product and H=((abs(A).lo * abs(B).hi) & $ffff)<<16: carry iff result < H.
; Native N/Z then describe A xor B, not the product. Opposite signs use native
; NEG flags; double NEG preserves the hardware product and yields those flags.
; Zero-input cases retain the native incoming-X / normalization behavior.
FF1NativeMultiply:
 movem.l d1-d3,-(sp)
 move.l d0,d2
 beq.b .done
 move.l d0,d3
 eor.l d1,d3
 tst.l d1
 beq.b .zero_b
 muls.l d1,d0
 tst.l d3
 bmi.b .negative
 tst.l d2
 bpl.b .positive
 neg.l d2
 neg.l d1
.positive:
 swap d1
 mulu.w d2,d1
 swap d1
 clr.w d1
 move.l d0,d2
 sub.l d1,d2
 tst.l d3
 bra.b .done
.negative:
 neg.l d0
 neg.l d0
 bra.b .done
.zero_b:
 tst.l d2
 bpl.b .zero
 neg.l d2
.zero:
 clr.l d0
.done:
 movem.l (sp)+,d1-d3
 rts
FF1MultiplySignature:
'''+ ' dc.w '+','.join('$'+mem[i:i+2].hex() for i in range(0x29500,0x29542,2))+'\n endc\n\n'
s=s.replace('FF1NativeSites:\n',helper+'FF1NativeSites:\n')
rows=json.loads((r/'manifest/step5-b6-cfg-sites.json').read_text());table=' ifgt FF1_NATIVE_EXACT-4\n; Additional sites with BOTH paths of conditional branches audited. Guard-only\n; fragments cover every visited instruction through the final XNZVC kill.\n';proof={}
for x in rows:
 pc=x['pc'];table+='; $%x %s: CFG proof fragments below.\n dc.l $%x\n dc.w 6,$%04x\n dc.w $4eb9,$0002,$%04x\n'%(pc,x['kind'],pc,0x4000 if x['kind']=='multiply' else 0x8000,0x9500 if x['kind']=='multiply' else 0x93d0)
 for k,v in x['proof'].items():proof[int(k,16)]=v
for pc,v in sorted(proof.items()):
 raw=bytes.fromhex(v['bytes']);table+='; $%x %s\n dc.l $%x\n dc.w %d,$2000\n dc.b %s\n'%(pc,v['instruction'],pc,len(raw),','.join('$%02x'%b for b in raw))
table+=' endc\n';s=s.replace(' dc.l 0\n endc\n',table+' dc.l 0\n endc\n');p.write_text(s)
print('Additional CFG sites',len(rows),'proof instructions',len(proof))
