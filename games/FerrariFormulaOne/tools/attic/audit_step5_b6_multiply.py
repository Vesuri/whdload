from pathlib import Path
import re,json
r=Path(__file__).resolve().parents[1];s=(r/'tmp/step4/active.dis').read_text().splitlines();mem=(r/'tmp/step5/a1200-fast-b5-v5-matrix-lean-fine/loop126.bin').read_bytes()
code=[]
for l in s:
 m=re.fullmatch(r'([0-9a-f]+): ([0-9a-f]+)\s+(.*?)\s*;.*',l)
 if m:code.append((int(m[1],16),bytes.fromhex(m[2]),m[3].strip()))
rows=[]
for i,(pc,b,t) in enumerate(code):
 if t!='jsr $29500.l':continue
 proof=[];ok=False;end=pc+len(b)
 for p,raw,ins in code[i+1:i+35]:
  if p!=end:break
  end=p+len(raw);op=ins.split()[0];proof.append((p,raw,ins))
  if re.fullmatch(r'(add|sub|neg)(i|q)?\.[bwl]',op) and not re.search(r', a[0-7]$',ins):ok=True;break
  if re.fullmatch(r'(as|ls)[lr]\.[bwl]',op):
   if re.search(r'#\$[1-8],',ins):ok=True
   elif len(proof)>1:
    m=re.fullmatch(r'moveq #\$([0-9a-f]+), (d[0-7])',proof[-2][2]);ok=bool(m and 0<int(m[1],16)<64 and ins.split()[1]==m[2]+',')
   break
  if ins in ('jsr $29500.l','jsr $293d0.l'):continue # neither routine reads incoming flags
  if not re.fullmatch(r'(move|movea|movem|lea|ext|clr|tst|cmp|cmpi|adda|suba|and|andi|or|ori|eor|eori)\.[bwl]|moveq|swap',op):break
  if 'ccr' in ins or 'sr' in ins:break
 if not ok or mem[pc:end]!=b+b''.join(x[1] for x in proof):continue
 rows.append(dict(pc=pc,signature=mem[pc:end].hex(),proof=[dict(pc=p,instruction=t) for p,b,t in proof]))
(r/'manifest/step5-b6-multiply-sites.json').write_text(json.dumps(rows,indent=2)+'\n');print('additional multiply candidates',len(rows),[hex(x['pc']) for x in rows])
