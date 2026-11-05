#!/usr/bin/env python3
"""Pin native wheel-position writes and their old-position reconstruction sites.
This local alias/write audit is not a complete CFG or collision-accuracy proof.
"""
from pathlib import Path
import capstone,hashlib,json,re
root=Path(__file__).resolve().parents[1]
raw=(root/'tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes();code=raw[0x28:]
md=capstone.Cs(capstone.CS_ARCH_M68K,capstone.CS_MODE_M68K_000)
items=list(md.disasm(code[0xc49c:0xd346],0xc49c));assert sum(i.size for i in items)==0xd346-0xc49c
ins={i.address:(i.mnemonic,i.op_str) for i in items}
aliases={};writes=[]
for i in items:
 ops=i.op_str.split(', ')
 if len(ops)==2 and ops[1] in ('a0','a1'):
  reg=ops[1];src=ops[0]
  if i.mnemonic=='movea.l' and src in ('-$e6(a5)','-$ea(a5)'):aliases[reg]=('candidate' if src=='-$e6(a5)' else 'original',0)
  elif i.mnemonic in ('addq.l','adda.l') and src.startswith('#$') and reg in aliases:aliases[reg]=(aliases[reg][0],aliases[reg][1]+int(src[2:],16))
  else:aliases.pop(reg,None)
 if len(ops)==2 and i.mnemonic in ('move.l','add.l','sub.l'):
  z=re.fullmatch(r'(?:\$(\w+))?\((a[01])\)',ops[1])
  if z and z[2] in aliases:writes.append(dict(address=i.address,operation=i.mnemonic,root=aliases[z[2]][0],axis_offset=aliases[z[2]][1]+int(z[1] or '0',16)))
 if i.mnemonic=='jsr':aliases={}
initial={0xc530,0xc53e,0xc54e};oldcopy={0xc55a,0xc564,0xc572}
rebase={0xcaae:(0xcaa4,0xcaa8,'add.l','(a0), d0'),0xcac6:(0xcaba,0xcabe,'add.l','$4(a0), d0'),0xcae0:(0xcad4,0xcad8,'add.l','$8(a0), d0'),0xcee2:(0xced8,0xcedc,'adda.l','(a1), a0'),0xcef4:(0xcee8,0xceec,'adda.l','$4(a1), a0'),0xcf08:(0xcefc,0xcf00,'adda.l','$8(a1), a0'),0xd06a:(0xd060,0xd064,'adda.l','(a1), a0'),0xd082:(0xd076,0xd07a,'adda.l','$4(a1), a0'),0xd09c:(0xd090,0xd094,'adda.l','$8(a1), a0')}
assert len(writes)==33
for w in writes:
 a=w['address'];assert w['axis_offset'] in (0,4,8)
 if w['root']=='original':assert a in oldcopy
 if w['operation']=='move.l':assert a in initial|oldcopy|set(rebase)
for store,(load,add,op,args) in rebase.items():
 assert ins[load][0]=='movea.l' and ins[load][1].startswith('-$ea(a5), ')
 assert ins[add]==(op,args)
# The only old-buffer writes are the initial candidate-to-original copies.
assert {w['address'] for w in writes if w['root']=='original'}==oldcopy
result=dict(executable_sha256=hashlib.sha256(raw).hexdigest(),range_sha256=hashlib.sha256(code[0xc49c:0xd346]).hexdigest(),writes=[dict(w,address=hex(w['address'])) for w in writes],original_copy_sites=sorted(map(hex,oldcopy)),old_plus_integer_reconstruction_sites=sorted(map(hex,rebase)),scope='Local alias/write inventory and exact rebase patterns. Integer collision decisions are unchanged; fractional precision of all collision calculations is not proven.')
(root/'tmp/prof/centroid-ownership-audit.json').write_text(json.dumps(result,indent=2)+'\n');print('Verified33 wheel-position writes,3 initial old-buffer copies and9 old-plus-integer reconstruction sites')
