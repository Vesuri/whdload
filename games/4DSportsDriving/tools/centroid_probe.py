#!/usr/bin/env python3
"""Attribute stopped-car displacement to native wheel reconstruction stages."""
import json,re,sys
from pathlib import Path
from profile_window import command
cap=Path(sys.argv[1]).resolve();m=json.loads((cap/'anchor.json').read_text());g=m['game_base'];aa=m['data_base']+0x7ffe;car=aa-0x92e

def sum_expr(base,axis):
 return '+'.join(f'*(int *)($a5{base+12*i+4*axis:+#x})' for i in range(4))

def log(label,expressions):
 return 'printf "'+label+' '+' '.join(['%d']*len(expressions))+'\\n", '+', '.join(expressions)+'\n'
script='gdb delete\nset $n=0\n'
for off,label in [(0xc60c,'REBUILD'),(0xd1d6,'CONTACT'),(0xd346,'SUSPENSION'),(0xd388,'CENTER')]:
 script+=f'break *{g+off:#x}\ncommands\nsilent\n'
 if label=='REBUILD':
  expr=[f'*(unsigned short *){aa-0x940:#x}']+[f'*(int *){car+4*i:#x}' for i in range(3)]+[sum_expr(-0xe2,i) for i in range(3)]+[sum_expr(-0xb2,i) for i in range(3)]+[f'*(unsigned short *){car+o:#x}' for o in (0x18,0x1a,0x1c,0x2a,0x2c)]
 elif label=='CENTER':expr=[f'*(int *){aa+0xb9c+4*i:#x}' for i in range(3)]
 else:expr=[sum_expr(-0xb2,i) for i in range(3)]
 script+=log(label,expr)+'continue\nend\n'
script+=f'break *{g+0xe7b4:#x}\ncommands\nsilent\nset $n=$n+1\n'
script+=log('END',[f'*(int *){car+4*i:#x}' for i in range(3)])+'if $n<20\ncontinue\nend\nend\ncontinue\ndelete'
(cap/'centroid-probe.gdb').write_text(script);out=command(script);(cap/'centroid-probe.txt').write_text(out)
records={tag:[list(map(int,s.split())) for s in re.findall(r'^'+tag+r' (.*)$',out,re.M)] for tag in ('REBUILD','CONTACT','SUSPENSION','CENTER','END')}
assert all(len(rows)==20 for rows in records.values()),{k:len(v) for k,v in records.items()}
rows=[]
for r,c,s,center,end in zip(*records.values()):
 assert r[-2:]==[0,0]
 assert center==[n//4 for n in s] and end==center
 rows.append(dict(tick=r[0],angles=r[10:13],rebuild=[r[4+i]/4-r[1+i] for i in range(3)],translation=[(r[7+i]-r[4+i])/4 for i in range(3)],contact=[(c[i]-r[7+i])/4 for i in range(3)],suspension=[(s[i]-c[i])/4 for i in range(3)],centroid_rounding=[center[i]-s[i]/4 for i in range(3)],total=[end[i]-r[1+i] for i in range(3)]))
keys=('rebuild','translation','contact','suspension','centroid_rounding','total');totals={k:[sum(r[k][i] for r in rows) for i in range(3)] for k in keys}
result=dict(rate=m['active_simulation_word'],updates=20,totals=totals,rows=rows)
(cap/'centroid-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(totals,indent=2))
