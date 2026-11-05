from pathlib import Path
import json
r=Path(__file__).resolve().parents[1];p=r.parents[1]/'Games/FerrariFormulaOne_NativeExact.s';s=p.read_text();assert 'FF1NativeMultiplyPatch' not in s
s=s.replace(' bne.b .bad',' bne.w .bad')
s=s.replace(' adda.w d2,a1\n move.l #$4c410801',' btst #14,d2\n bne.b FF1NativeMultiplyPatch\n adda.w d2,a1\n move.l #$4c410801')
# Nonlocal label would change local symbol scope: retain local assembler label.
s=s.replace('FF1NativeMultiplyPatch','.multiply')
s=s.replace('.bad:\n lea error', '''.multiply:
 andi.w #$3fff,d2
 adda.w d2,a1
 move.l #$4c010800,(a1)       ; muls.l d1,d0 (low signed product)
 move.w #$4e71,4(a1)
 bra.b .patch
.bad:
 lea error''')
rows=json.loads((r/'manifest/step5-b6-multiply-sites.json').read_text());table=' ifgt FF1_NATIVE_EXACT-1\n; Additional multiply sites. Intervening $29500/$293d0 calls do not\n; read incoming flags; the recorded arithmetic instruction kills XNZVC.\n'
for x in rows:
 table+='; $%x: %s\n'%(x['pc'],'; '.join('$%x %s'%(p['pc'],p['instruction']) for p in x['proof']))
 table+=' dc.l $%x\n dc.w %d,$4000\n dc.b %s\n'%(x['pc'],len(bytes.fromhex(x['signature'])),','.join('$'+x['signature'][j:j+2] for j in range(0,len(x['signature']),2)))
s=s.replace(' dc.l 0\n endc\n',table+' endc\n dc.l 0\n endc\n');p.write_text(s)
