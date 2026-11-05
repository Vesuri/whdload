#!/usr/bin/env python3
"""Observe a native car outcome while the VERIFY tape supplies ordinary input."""
import argparse,json,re,struct
from pathlib import Path
from profile_window import command
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--limit',type=int,default=150);p.add_argument('--expect-reason',type=int,choices=(1,2,3,5));a=p.parse_args();cap=a.capture
m=json.loads((cap/'anchor.json').read_text());g=m['game_base'];b=(cap/'slave.slave').read_bytes();sl=m['marker']-b.index(b'4DTAPE!!')+32
syms={n:int(v,16)+sl for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
def regs():return {k:int(v,16) for k,v in re.findall(r'^(\w+)\s+0x([0-9a-f]+)',command('gdb info registers'),re.M)}
def dump(name,addr,n):
 path=cap/name;command(f'gdb dump binary memory {path} {addr:#x} {addr+n:#x}');raw=path.read_bytes();assert len(raw)==n;return raw
command('stop');command('gdb delete')
lines=[f'tbreak *{g+0x114f6:#x}',f'break *{g+0x7500:#x}',f'condition $bpnum *(unsigned int *){m["marker"]+16:#x}>={a.limit}']
lines += [f'tbreak *{syms[n]:#x}' for n in ('twin_failed','math_failed','book_failed') if n in syms]
print(command('gdb '+'\n'.join(lines)+'\ncontinue'),flush=True);r=regs();result={'stop_pc':hex(r['pc']),'limit':a.limit}
if r['pc']==g+0x114f6:
 stack=dump('outcome-stack.bin',r['sp'],8);ret,reason,car=struct.unpack('>IHH',stack);result.update(reason=reason,car=car)
 print('Native outcome',result,flush=True)
 print(command(f'gdb tbreak *{ret:#x}\ncontinue'),flush=True);after=regs();assert after['pc']==ret and after['sp']==r['sp']+4,after
 result['native_handler_returned']=True
else:result['native_handler_returned']=False
state=dump('outcome-state.bin',m['data_base'],0xa77c);a4=0x7ffe
result.update(mode=state[a4+0x45],car_end_reason=state[a4-0x92e+0xc9],selected_simulation=struct.unpack_from('>H',state,a4-188)[0],active_simulation=struct.unpack_from('>H',state,a4-0x15fa)[0])
if m['memory_base']:
 dump('outcome-memory.bin',m['memory_base'],m['memory_size'])
else:
 memory=bytearray(m['memory_size'])
 for bank,lo,hi in [('chip',0,int(m['settings']['CHIP_KB'])*1024),('slow',0xc00000,m['memory_size'])]:
  memory[lo:hi]=dump(f'outcome-{bank}.bin',lo,hi-lo)
 (cap/'outcome-memory.bin').write_bytes(memory)
(cap/'outcome.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
assert result['native_handler_returned'],'No native outcome within the bounded drive; inspect snapshot'
assert result['reason'] in (1,2,3,5) and result['car']==0,result
if a.expect_reason is not None: assert result['reason']==a.expect_reason,result
command('gdb delete')
print(command(f'gdb tbreak *{g+0x7500:#x}\ncontinue'),flush=True)
print(command(f'shot {cap}/outcome.png'),flush=True)
