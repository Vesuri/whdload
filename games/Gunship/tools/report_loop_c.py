import os
from pathlib import Path
import sys,re,json,bisect,collections
import _amigaxdev
from amigaxdev.callprofile import Reduction
import report
folder=Path(sys.argv[1]);root=Path(__file__).resolve().parents[1];info=json.loads((folder/'addresses.json').read_text());listing=Path(os.environ.get('LISTING',str(root/'tmp/build/verify/Gunship.lst'))).read_text(encoding='latin1')
symbols={n:int(v,16) for v,n in re.findall(r'^([0-9A-F]{8}) ([A-Za-z_][A-Za-z_0-9]*)$',listing,re.M)}
source=root/'src'
names=set()
for f in list(source.glob('*.i'))+[source/'GunshipHD.s']:
 names.update(re.findall(r'^([A-Za-z_][A-Za-z_0-9]*):',f.read_text(),re.M))
labels=sorted((info['base']+symbols[n],n) for n in names if n in symbols)
labels+=sorted((info['arena']+v,n) for n,v in symbols.items() if n.startswith('RT_') and n!='RT_ARENA_SIZE' and v<symbols['RT_ARENA_SIZE'])
report.use_layout(str(folder));mem=(folder/'fast.bin').read_bytes()
for name in ('gamemule','Gunship'):
 rb=next(b for n,b,l in report.REGIONS if n==name)
 labels.extend((rb+v,f'{name}+{v:04x}') for v in report.starts(mem,name))
labels.sort();addresses=[a for a,n in labels];red=Reduction.load(folder/'profile.pkl.gz');cycles=collections.Counter()
for pc,cost in red.self.items():
 if not isinstance(pc,int):continue
 idx=bisect.bisect_right(addresses,pc)-1
 name=labels[idx][1] if idx>=0 else f'other {pc&~255:x}'
 if idx>=0 and pc-addresses[idx]>0x1000:name=f'other {pc&~255:x}'
 cycles[name]+=cost
print('fields',len(red.fields),'total',red.total())
for n,c in cycles.most_common(35):print(f'{100*c/red.total():6.2f}% {n}')
print('hot PCs',[(hex(pc),round(c/red.total()*100,2)) for pc,c in red.self.most_common(10)])
