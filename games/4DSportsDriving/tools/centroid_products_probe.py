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
for call,ret,label in [(0xc520,0xc524,'BUILD_PRODUCT'),(0xd2f0,0xd2f4,'SUSP_PRODUCT')]:
 script+=f'break *{g+call:#x}\ncommands\nsilent\n'
 expr=[f'*(unsigned short *){aa-0x940:#x}']
 for axis in range(3):
  expr.append('+'.join(f'(int)*(short *)($a5{(-0x40+2*j):+#x})*(int)*(short *){aa+0xbae+6*j+2*axis:#x}' for j in range(3)))
 script+=log(label,expr)+'continue\nend\n'
 buffer=-0x46 if label=='BUILD_PRODUCT' else -0x52
 script+=f'break *{g+ret:#x}\ncommands\nsilent\n'
 script+=log(label+'_OUT',[f'*(unsigned short *){aa-0x940:#x}']+[f'*(short *)($a5{buffer+2*i:+#x})' for i in range(3)])+'continue\nend\n'
script+=f'break *{g+0xe7b4:#x}\ncommands\nsilent\nset $n=$n+1\n'
script+=log('END',[f'*(int *){car+4*i:#x}' for i in range(3)])+'if $n<20\ncontinue\nend\nend\ncontinue\ndelete'
(cap/'centroid-products.gdb').write_text(script);out=command(script);(cap/'centroid-products.txt').write_text(out)
records={tag:[list(map(int,s.split())) for s in re.findall(r'^'+tag+r' (.*)$',out,re.M)] for tag in ('REBUILD','CONTACT','SUSPENSION','CENTER','END')}
assert all(len(rows)==20 for rows in records.values()),{k:len(v) for k,v in records.items()}
rows=[]
for r,c,s,center,end in zip(*records.values()):
 assert r[-2:]==[0,0]
 assert center==[n//4 for n in s] and end==center
 rows.append(dict(tick=r[0],angles=r[10:13],rebuild=[r[4+i]/4-r[1+i] for i in range(3)],translation=[(r[7+i]-r[4+i])/4 for i in range(3)],contact=[(c[i]-r[7+i])/4 for i in range(3)],suspension=[(s[i]-c[i])/4 for i in range(3)],centroid_rounding=[center[i]-s[i]/4 for i in range(3)],total=[end[i]-r[1+i] for i in range(3)]))
keys=('rebuild','translation','contact','suspension','centroid_rounding','total');totals={k:[sum(r[k][i] for r in rows) for i in range(3)] for k in keys}
products={tag:[list(map(int,x.split())) for x in re.findall(r'^'+tag+r' (.*)$',out,re.M)] for tag in ('BUILD_PRODUCT','SUSP_PRODUCT')}
for tag,values in products.items():
 outputs=[list(map(int,x.split())) for x in re.findall(r'^'+tag+r'_OUT (.*)$',out,re.M)]
 assert len(outputs)==len(values)
 for v,o in zip(values,outputs):
  assert o==[v[0]]+[n//16384 for n in v[1:]], (v,o)
for row in rows:
 terms=[r for records in products.values() for r in records if r[0]==row['tick']]
 assert len([r for r in products['BUILD_PRODUCT'] if r[0]==row['tick']])==4
 row['transform_floor_loss']=[sum((r[i+1]//16384-r[i+1]/16384)/4 for r in terms) for i in range(3)]
 row['without_transform_and_centroid_floor']=[row['total'][i]-row['transform_floor_loss'][i]-row['centroid_rounding'][i] for i in range(3)]
for key in ('transform_floor_loss','without_transform_and_centroid_floor'):
 totals[key]=[sum(r[key][i] for r in rows) for i in range(3)]
result=dict(rate=m['active_simulation_word'],updates=20,totals=totals,rows=rows,products=products)
(cap/'centroid-products-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(totals,indent=2))
