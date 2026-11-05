from pathlib import Path
import re,json
r=Path(__file__).resolve().parents[1];lines=(r/'tmp/step4/active.dis').read_text().splitlines();mem=(r/'tmp/step5/a1200-fast-b5-v5-matrix-lean-fine/loop126.bin').read_bytes()
def parse(l):
 m=re.fullmatch(r'([0-9a-f]+): ([0-9a-f]+)\s+(.*?)\s*;.*',l)
 return (int(m[1],16),bytes.fromhex(m[2]),m[3].strip()) if m else None
code=[parse(l) for l in lines];code=[x for x in code if x];targets=set()
for pc,b,t in code:
 if t.startswith(('b','j')):
  m=re.search(r'\$([0-9a-f]+)(?:\.l)?$',t)
  if m:targets.add(int(m[1],16))
rows=[]
for i,(pc,b,t) in enumerate(code):
 if t!='jsr $293d0.l':continue
 proof=[];ok=False;end=pc+len(b)
 for p,raw,ins in code[i+1:i+25]:
  if p!=end:break
  end=p+len(raw);op=ins.split()[0];proof.append((p,raw,ins))
  if re.fullmatch(r'(add|sub|neg)(i|q)?\.[bwl]',op) and not re.search(r', a[0-7]$',ins):ok=True;break
  if re.fullmatch(r'(as|ls)[lr]\.[bwl]',op):
   if re.search(r'#\$[1-8],',ins):ok=True
   elif len(proof)>1:
    m=re.fullmatch(r'moveq #\$([0-9a-f]+), (d[0-7])',proof[-2][2]);ok=bool(m and 0<int(m[1],16)<64 and ins.split()[1]==m[2]+',')
   break
  if not re.fullmatch(r'(move|movea|movem|lea|ext|clr|tst|cmp|cmpi|adda|suba|and|andi|or|ori|eor|eori)\.[bwl]|moveq|swap',op):break
  if 'ccr' in ins or 'sr' in ins:break
 if not ok or mem[pc:end]!=b+b''.join(x[1] for x in proof):continue
 prev=code[i-1];m=re.fullmatch(r'(?:moveq|move.l) #\$([0-9a-f]+), d1',prev[2]);constant=int(m[1],16) if m else None
 if constant is not None and (not 0<constant<0x80000000 or pc in targets):constant=None
 start=prev[0] if constant is not None else pc
 if mem[start:pc]!=(prev[1] if constant is not None else b''):continue
 rows.append(dict(pc=pc,start=start,constant=constant,signature=mem[start:end].hex(),proof=[dict(pc=p,instruction=t) for p,b,t in proof]))
(r/'manifest/step5-b6-division-sites.json').write_text(json.dumps(rows,indent=2)+'\n')
head='''; SPS 0481 native arithmetic candidate, 68020 only, default off.
; Host installs after conversion hooks and flushes instruction caches afterward.
; Every site has a straight-line proof below: all XNZVC bits are overwritten
; before a branch/call/return or any flag consumer. No CCR equivalence claimed.
; Positive immediate divisors cannot divide by zero or overflow signed 32-bit.
; Variable divisors use FF1NativeDivide, preserving native zero and wrap results.
; Signatures include the complete flag-killing sequence and constant load.
 ifnd FF1_NATIVE_EXACT
FF1_NATIVE_EXACT equ 0
 endc
 ifgt FF1_NATIVE_EXACT
FF1InstallNativeExact:
 movem.l d0-d2/a0-a2,-(sp)
 lea FF1NativeSites(pc),a0
.check:
 move.l (a0)+,d0
 beq.b .checked
 move.l d0,a1
 move.w (a0)+,d1
 addq.l #2,a0
 subq.w #1,d1
.bytes:
 move.b (a0)+,d2
 cmp.b (a1)+,d2
 bne.b .bad
 dbra d1,.bytes
 bra.b .check
.checked:
 lea FF1NativeSites(pc),a0
.patch:
 move.l (a0)+,d0
 beq.b .done
 move.l d0,a1
 move.w (a0)+,d1
 move.w (a0)+,d2
 adda.w d1,a0
 ; D2 = call offset from signature start, bit15 selects guarded call.
 tst.w d2
 bmi.b .guarded
 adda.w d2,a1
 move.l #$4c410801,(a1)       ; divsl.l d1,d1:d0 (32-bit dividend)
 move.w #$4e71,4(a1)
 bra.b .patch
.guarded:
 andi.w #$7fff,d2
 adda.w d2,a1
 lea FF1NativeDivide(pc),a2
 move.l a2,2(a1)            ; keep JSR opcode
 bra.b .patch
.bad:
 lea error(pc),a0
 move.l #39,(a0)
.done:
 movem.l (sp)+,d0-d2/a0-a2
 rts

; D0 dividend -> quotient, D1 divisor -> remainder. Everything else preserved.
; Zero divisor returns 0,0; INT_MIN/-1 returns INT_MIN,0, like native.
FF1NativeDivide:
 tst.l d1
 beq.b .zero
 divsl.l d1,d1:d0
 bvs.b .overflow
 rts
.overflow:
 move.l #$80000000,d0
.zero:
 clr.l d1
 tst.l d0                 ; overflow keeps wrapped quotient
 ; Zero-divisor entry must clear D0; separate entry below is used instead.
 rts

FF1NativeSites:
'''
head=head.replace('beq.b .zero\n divsl','beq.b .zero_divisor\n divsl').replace('.zero:\n clr.l d1\n tst.l d0                 ; overflow keeps wrapped quotient\n ; Zero-divisor entry must clear D0; separate entry below is used instead.\n rts','.zero:\n clr.l d1\n rts\n.zero_divisor:\n clr.l d0\n clr.l d1\n rts')
for x in rows:
 head+='; $%x: %s\n'%(x['pc'],'; '.join('$%x %s'%(p['pc'],p['instruction']) for p in x['proof']))
 head+=' dc.l $%x\n dc.w %d,$%04x\n dc.b %s\n'%(x['start'],len(bytes.fromhex(x['signature'])),x['pc']-x['start']+(0x8000 if x['constant'] is None else 0),','.join('$'+x['signature'][j:j+2] for j in range(0,len(x['signature']),2)))
head+=' dc.l 0\n endc\n'
(r.parents[1]/'Games/FerrariFormulaOne_NativeExact.s').write_text(head)
print('division sites',len(rows),'inline',sum(x['constant'] is not None for x in rows))
