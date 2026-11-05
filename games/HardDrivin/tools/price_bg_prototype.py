import json,re,sys,collections
from pathlib import Path
import numpy as np
import barto_mmap as barto
from capstone import *
p=Path(sys.argv[1]);m=json.loads((p/'metadata.json').read_text());base=m['layout']['code_base'];lst=(p/'slave.lst').read_text(encoding='latin1');sym=lambda n:int(re.search(r'^'+re.escape(n)+r'\s+00:([0-9a-fA-F]+)',lst,re.M)[1],16);slave=m['layout']['published']-sym('_code_start');start=slave+sym('_render_background');b=(p/'slave.slave').read_bytes()
# Find raw helper signature in load image without assuming hunk-header size.
sign=bytes.fromhex('48e77c20402f');off=b.find(bytes.fromhex('48e77c20302f001c'));assert off>=0
code=b[off:off+512];md=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000);ins=[]
for i in md.disasm(code,start):
 ins.append(i)
 if i.mnemonic=='rts':break
end=ins[-1].address+2
writes=[i for i in ins if '$dff058' in i.op_str];assert len(writes)==1
waitlo=writes[0].address+writes[0].size;waithi=next(i.address for i in ins if i.address>=waitlo and i.mnemonic.startswith('bra') and '$' in i.op_str and int(i.op_str[1:],16)>i.address)
t=barto.load(p/'trace.bin');total=cost=lastwait=rows=0;calls=0
for f in t.fields:
 a=np.frombuffer(t.data,dtype='<u4',count=(f.insn_end-f.insn_off)//4,offset=f.insn_off).reshape(-1,19);pc=a[:,0];c=0xffffffff-a[:,1];total+=int(c.sum());cost+=int(c[(pc>=start)&(pc<end)].sum());calls+=int(np.count_nonzero(pc==start));lastwait+=int(c[(pc>=waitlo)&(pc<waithi)&(a[:,6]==0)].sum())
 for r in a[pc==writes[0].address]:rows+=int(r[7]&65535)>>6
r=dict(calls=calls,rows=rows,total_cycles=total,cycles=cost,cycles_per_call=cost/calls if calls else None,cycles_per_row=cost/rows if rows else None,last_plane_wait_cycles=lastwait,last_plane_wait_percent=100*lastwait/total,share_percent=100*cost/total,wait_pc=[hex(waitlo),hex(waithi)]);(p/'background-price.json').write_text(json.dumps(r,indent=2)+'\n');print(p.name,r)
