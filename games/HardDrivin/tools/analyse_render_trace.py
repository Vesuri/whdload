"""Direct native-range costs and input distributions; no inclusive double counting."""
import sys,json,collections,struct,re
from pathlib import Path
import numpy as np
import barto_mmap as barto
out=Path(sys.argv[1]);meta=json.loads((out/'metadata.json').read_text());base=meta['layout']['code_base'];t=barto.load(out/'trace.bin')
ranges={'rotation_y':(0x2a2e,0x2a7a),'rotation_x':(0x2a7a,0x2ac4),'edge_setup':(0x2da2,0x2de6),'edge_rows':(0x2de6,0x329a),'span':(0x329a,0x3736),'clip':(0x3736,0x39d4),'background':(0x3a28,0x3aac)}
listing=(out/'slave.lst').read_text(encoding='latin1')
if re.search(r'^_render_rotate_y\s',listing,re.M):
 from machine_profiles import banks
 from capstone import Cs,CS_ARCH_M68K,CS_MODE_BIG_ENDIAN,CS_MODE_M68K_000
 def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
 slave=meta['layout']['published']-sym('_code_start')
 memory=[(b,(out/('anchor-'+n+'.bin')).read_bytes()) for n,b,z in banks(meta['configuration'])]
 md=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000)
 for axis in ['y','x']:
  begin=slave+sym('_render_rotate_'+axis)
  data=next(v[begin-b:begin-b+1024] for b,v in memory if b<=begin< b+len(v))
  end=next(i.address+i.size for i in md.disasm(data,begin) if i.mnemonic=='rts')
  ranges['replacement_'+axis]=(begin-base,end-base)
 if re.search(r'^_render_wait\s',listing,re.M):
  begin=slave+sym('_render_wait');data=next(v[begin-b:begin-b+256] for b,v in memory if b<=begin< b+len(v));end=next(i.address+i.size for i in md.disasm(data,begin) if i.mnemonic=='rts');ranges['replacement_wait']=(begin-base,end-base)
 ranges['slave_wait']=(slave+sym('_blitwait')-base,slave+sym('_dbfwait1')-base)
cost=collections.Counter();counts=collections.Counter();rot=collections.Counter();spans=collections.Counter();total=0
for f in t.fields:
 assert (f.insn_end-f.insn_off)%76==0
 rows=np.frombuffer(t.data,dtype='<u4',count=(f.insn_end-f.insn_off)//4,offset=f.insn_off).reshape(-1,19);assert np.all(rows[:,0]<0xffff0000) and np.all(rows[:,1]>=0xffff0000)
 pc=rows[:,0].astype(np.int64)-base;cycles=0xffffffff-rows[:,1];total+=int(cycles.sum())
 for name,(lo,hi) in ranges.items():cost[name]+=int(cycles[(pc>=lo)&(pc<hi)].sum());counts[name]+=int(np.count_nonzero(pc==lo))
 for r in rows[pc==0x2a46]:rot[(int(r[3]&65535),int(r[4]&65535),int(r[2]&65535))]+=1
 for r in rows[pc==0x2a92]:rot[(int(r[3]&65535),int(r[4]&65535),int(r[2]&65535))]+=1
 counts['swaps']+=int(np.count_nonzero(pc==0xb4));counts['edge_scanline_store']+=int(np.count_nonzero((pc>=0x2de6)&(pc<0x329a)&((pc-0x2de6)%6==0)))
seconds=len(t.fields)*142102/7093790
result=dict(fields=len(t.fields),total_cycles=total,counts=dict(counts),ranges={n:dict(cycles=v,share_percent=100*v/total,cycles_per_call=v/counts[n] if counts[n] else None,ms_per_swap=v/total*seconds*1000/counts['swaps']) for n,v in cost.items()},rotation_inputs=[dict(cos=c,sin=s,vertices=n,calls=v) for (c,s,n),v in rot.most_common()])
(out/'render-costs.json').write_text(json.dumps(result,indent=2)+'\n');print(out.name,json.dumps({k:v for k,v in result.items() if k!='rotation_inputs'},indent=1));print('rotation top',result['rotation_inputs'][:12])
