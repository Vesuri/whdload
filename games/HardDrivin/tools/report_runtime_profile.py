"""Attribute current development-slave code using the exact retained listing."""
import argparse,bisect,collections,json,re,sys
from pathlib import Path
from harddrivin_report import Memory,Namer,analyse,locate
from amigaxdev.env import path
import barto_mmap as barto
p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--listing',type=Path,required=True);a=p.parse_args()
symbols={name:int(off,16) for off,name in re.findall(r'^([0-9A-F]{8}) (_[A-Za-z][A-Za-z0-9_]*)(?:\s|$)',a.listing.read_text(errors='replace'),re.M)}
layout=json.loads((a.run/'metadata.json').read_text())['layout'];game=layout['code_base'];slave=layout['published']-symbols['_code_start']
t=barto.load(a.run/'trace.bin');dump=(a.run/'before-slow.bin').read_bytes();base=0xc00000;mem=Memory(t,dump,base)
assert mem.long(slave+symbols['_code_start'])==game
kick=locate(dump,Path(path('KICKSTART13')).read_bytes()[:0x40000],base,256);assert kick
regs=[(game,game+0x11a4e,'game',game),(slave,slave+0x5000,'slave',slave),(kick,kick+0x40000,'kick',kick-0xfc0000)]
ordered=sorted((off,name) for name,off in symbols.items() if 0<=off<0x5000);offsets=[off for off,name in ordered]
class CurrentNamer(Namer):
 def addr(self,pc):
  if pc is not None and slave<=pc<slave+0x5000:
   off=pc-slave;i=bisect.bisect_right(offsets,off)-1
   if i>=0:
    origin,name=ordered[i];return 'slave:'+name+(f'+{off-origin:x}' if off!=origin else '')
  return super().addr(pc)
n=CurrentNamer(regs,mem);selfc,incl,calls,edges,pcs,kinds,contexts=analyse(t,mem,n,t.fields);total=sum(kinds.values())
result=dict(regions=regs,fields=len(t.fields),cycles=total,coverage=total/sum(f.cycles for f in t.fields),self=[dict(name=k,cycles=v,share=v/total,calls=calls[k]) for k,v in selfc.most_common(50)],inclusive=[dict(name=k,cycles=v,share=v/total,calls=calls[k],per_call=v/calls[k] if calls[k] else None) for k,v in incl.most_common(50)],instructions=[dict(name=n.addr(k),pc=k,cycles=v,share=v/total) for k,v in pcs.most_common(40)])
(a.run/'attribution.json').write_text(json.dumps(result,indent=2)+'\n')
for kind in ['self','inclusive']:
 print(kind)
 for row in result[kind][:25]:print(f'{row["share"]*100:6.2f}% {row["cycles"]:10d} {row["calls"]:6d} {row["name"]}')
