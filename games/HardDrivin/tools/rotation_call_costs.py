import json,re,sys,collections
from pathlib import Path
import numpy as np
import barto_mmap as barto
from capstone import *
p=Path(sys.argv[1]);m=json.loads((p/'metadata.json').read_text());base=m['layout']['code_base'];lst=(p/'slave.lst').read_text(encoding='latin1');sym=lambda n:int(re.search(r'^'+re.escape(n)+r'\s+00:([0-9a-fA-F]+)',lst,re.M)[1],16);slave=m['layout']['published']-sym('_code_start');enabled=m['render_window']['custom3']&2;raw=(p/'slave.slave').read_bytes();md=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000)
# Locate code bytes via retained listing offsets and the unique rotation prefix.
first=raw.find(bytes.fromhex('48e71f00302f0018302f'))
# The literal second opcode is MOVE.W into D1, so locate a shorter unique prefix.
first=raw.find(bytes.fromhex('48e71f00302f001c')) if first<0 else first
from machine_profiles import banks
mem=[(b,(p/('anchor-'+n+'.bin')).read_bytes()) for n,b,z in banks(m['configuration'])]
def rd(addr,n):return next(b[addr-a:addr-a+n] for a,b in mem if a<=addr and addr+n<=a+len(b))
starts={};probe={};ends={};ranges=[]
for axis,off,nativeret in [('y',0x2a2e,0x2a78),('x',0x2a7a,0x2ac2)]:
 start=slave+sym('_render_rotate_'+axis) if enabled else base+off;ret=next(i.address for i in md.disasm(rd(start,1024),start) if i.mnemonic=='rts')
 starts[base+off]=axis;probe[start+24]=axis;ends[ret]=axis;ranges.append((start,ret+2));ranges.append((base+off,base+off+2))
t=barto.load(p/'trace.bin');active=None;groups=collections.defaultdict(list)
for f in t.fields:
 a=np.frombuffer(t.data,dtype='<u4',count=(f.insn_end-f.insn_off)//4,offset=f.insn_off).reshape(-1,19);pc=a[:,0];keep=np.zeros(len(a),bool)
 for lo,hi in ranges:keep|=(pc>=lo)&(pc<hi)
 for r in a[keep]:
  addr=int(r[0]);cycles=0xffffffff-int(r[1])
  if addr in starts:active=[starts[addr],None,0]
  if active is None:continue
  active[2]+=cycles
  if addr in probe:active[1]=(int(r[2]&65535),int(r[3]&65535),int(r[4]&65535))
  if addr in ends:
   if active[1] is not None:groups[(active[0],*active[1])].append(active[2])
   active=None
result=[dict(axis=k[0],vertices=k[1],cos=k[2],sin=k[3],calls=len(v),cycles=sum(v),cycles_per_call=sum(v)/len(v)) for k,v in groups.items()];(p/'rotation-calls.json').write_text(json.dumps(result,indent=2)+'\n');print(p.name,'completed calls',sum(x['calls'] for x in result),'groups',len(result))
