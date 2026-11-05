from pathlib import Path
import re,json
r=Path(__file__).resolve().parents[1];mem=(r/'tmp/step5/a1200-fast-b5-v5-matrix-lean-fine/loop126.bin').read_bytes();code={}
for l in (r/'tmp/step4/active.dis').read_text().splitlines():
 m=re.fullmatch(r'([0-9a-f]+): ([0-9a-f]+)\s+(.*?)\s*;.*',l)
 if m:code[int(m[1],16)]=(bytes.fromhex(m[2]),m[3].strip())
old={x['pc'] for f in ('division','multiply') for x in json.loads((r/f'manifest/step5-b6-{f}-sites.json').read_text())}
conds={'hi':5,'ls':5,'cc':1,'cs':1,'ne':4,'eq':4,'vc':2,'vs':2,'pl':8,'mi':8,'ge':10,'lt':10,'gt':14,'le':14}
def audit(pc,mask,seen,proof):
 if not mask:return True
 if len(seen)>200 or (pc,mask) in seen or pc not in code:return False
 seen=seen|{(pc,mask)};raw,ins=code[pc];op=ins.split()[0];end=pc+len(raw)
 if mem[pc:end]!=raw:return False
 proof[pc]=dict(bytes=raw.hex(),instruction=ins)
 if 'ccr' in ins or re.search(r'\bsr\b',ins):return False
 if re.fullmatch(r'(add|sub|neg)(i|q)?\.[bwl]',op) and not re.search(r', a[0-7]$',ins):return True
 if re.fullmatch(r'(as|ls)[lr]\.[bwl]',op):
  if re.search(r'#\$[1-8],',ins):return True
  mask &=16
 elif re.fullmatch(r'(move|moveq|ext|clr|tst|cmp|cmpi|and|andi|or|ori|eor|eori|muls|mulu)(\.[bwl])?|swap',op):mask &=16
 elif re.fullmatch(r'(movea|movem|lea|adda|suba|link|unlk)\.?[wl]?',op) or ins=='nop':pass
 elif ins in ('jsr $293d0.l','jsr $29500.l'):mask &=16
 elif re.fullmatch(r'b(ra|hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le)\.[bw]',op):
  cond=op[1:].split('.')[0];dest=int(re.search(r'\$([0-9a-f]+)',ins)[1],16)
  if cond=='ra':return audit(dest,mask,seen,proof)
  if mask&conds[cond]:return False
  return audit(dest,mask,seen,proof) and audit(end,mask,seen,proof)
 else:return False
 return audit(end,mask,seen,proof)
rows=[]
for pc,(raw,ins) in code.items():
 if ins not in ('jsr $24fe0.l','jsr $25000.l') or mem[pc:pc+len(raw)]!=raw:continue
 proof={pc:dict(bytes=raw.hex(),instruction=ins)}
 if audit(pc+len(raw),31,set(),proof):rows.append(dict(pc=pc,kind='sine' if '24fe0' in ins else 'cosine',proof={hex(k):v for k,v in sorted(proof.items())}))
(r/'manifest/step5-b6-trig-sites.json').write_text(json.dumps(rows,indent=2)+'\n');print('additional CFG-audited candidates',len(rows));print([(hex(x['pc']),x['kind']) for x in rows])
