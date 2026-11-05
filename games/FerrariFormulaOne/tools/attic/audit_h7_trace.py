from pathlib import Path
import sys,json,struct,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
p=Path(sys.argv[1]);r=json.loads((p/'result.json').read_text());t=barto.load(p/'detail.bin')
def memory(label):
 m=bytearray((p/(label+'.bin')).read_bytes());m+=bytes(0x200000-len(m))+(p/(label+'-fast.bin')).read_bytes();return m
m=memory('start');u=lambda a:struct.unpack_from('>I',m,a)[0];execbase=u(4);vector=execbase+84+6*12;gfx,handler,node=struct.unpack_from('>III',m,vector)
queue=u(gfx-276+2);bsqueue=u(gfx-294+2);assert m[handler:handler+10]==bytes.fromhex('317c0040009c2029003a')
report={'server':list(map(hex,(gfx,handler,node))),'queue_entries':{'QBlit':hex(queue),'QBSBlit':hex(bsqueue)},'queue_snapshots':[]};counts=collections.Counter();bad=[];dma=collections.Counter();maxaddr=0;ena=[]
for label in ['start','end']:
 v=memory(label);server=struct.unpack_from('>III',v,vector);assert server==(gfx,handler,node)
 heads=[struct.unpack_from('>I',v,gfx+x)[0] for x in (0x3a,0x42)];assert heads==[0,0];report['queue_snapshots'].append({'label':label,'heads':heads})
for f in t.fields:
 n=0
 for pc,cost,regs in t.instructions(f):
  n+=pc not in (None,0x7fffffff)
  if pc in (queue,bsqueue):bad.append(('queue-call',f.index,hex(pc)))
  if pc==handler:counts['blit_entries']+=1
  if pc==handler+10:
   counts['queue_head_tests']+=1
   if regs[0]!=0:bad.append(('queue-head',f.index,hex(regs[0])))
 counts['instructions']+=n
 state=struct.unpack_from('>H',f.custom,4+0x9a)[0]
 if state&64:ena.append((f.index,'start'))
 for at in range(0,len(f.dma),f.dma_size):
  typ=struct.unpack_from('<h',f.dma,at+29)[0];addr=struct.unpack_from('<I',f.dma,at+12)[0]
  if typ in (3,4,5,6,7,8):
   dma[typ]+=1
   if addr!=0xffffffff:
    maxaddr=max(maxaddr,addr)
    if addr>=0x200000:bad.append(('DMA',f.index,typ,hex(addr)))
  reg=struct.unpack_from('<H',f.dma,at)[0];dat=struct.unpack_from('<Q',f.dma,at+2)[0]&65535
  if reg==0x9a or (reg&0xff00)==0x1100 and addr==0xdff09a:
   state=state|(dat&0x7fff) if dat&0x8000 else state&~dat
   if state&64:ena.append((f.index,at//f.dma_size))
assert not bad,bad[:10];assert counts['instructions']>0
if 'candidate' in p.name:assert not ena,ena[:10]
report.update(status='passed',counts=dict(counts),dma_transfers=dict(dma),maximum_dma_address=hex(maxaddr),blit_enabled_observations=len(ena),fields=len(t.fields),scope='Observed race window and start/end server/queue snapshots; native CODE vector-call audit complements bounded dynamic evidence.')
(p/'h7-safety.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
