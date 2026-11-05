#!/usr/bin/env python3
"""Verify the native full-history move against immutable pre-operation bytes."""
import argparse,json,re,struct
from pathlib import Path
from profile_window import command,ROOT
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args();cap=a.capture.resolve();meta=json.loads((cap/'anchor.json').read_text());mem=(cap/'memory.bin').read_bytes();syms={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
base=meta['memory_base']+mem.index(b'4DHISTRY')+28-syms['sim_history_records']
def stop(symbol):
 at=base+syms[symbol];out=command(f'gdb delete\ntbreak *{at:#x}\ncontinue\ninfo registers pc');print(out,flush=True);assert int(re.search(r'^pc\s+0x([0-9a-f]+)',out,re.M)[1],16)==at

def dump(name):
 path=cap/name;command(f'gdb dump binary memory {path.relative_to(ROOT)} 0x200000 0x600000');return path.read_bytes()
stop('sim_history_rotation_ready');before=dump('rotation-before.bin');stop('sim_history_rotation_done');after=dump('rotation-after.bin')
a4=meta['data_base']+0x7ffe-meta['memory_base'];native=struct.unpack_from('>I',before,a4-0x16bc)[0]-meta['memory_base'];inputs=struct.unpack_from('>I',before,a4-0x1770)[0]-meta['memory_base'];companion=before.index(b'4DHISTRY')+28
old=before[native:native+20*0x460];expected=bytearray(old)
for slot in range(19):
 row=bytearray(old[(slot+1)*0x460:(slot+2)*0x460]);tick=struct.unpack_from('>H',row,0x140)[0];struct.pack_into('>H',row,0x140,(tick-1500)&65535);expected[slot*0x460:(slot+1)*0x460]=row
# The original loop modifies the final source row's cursor before copying it.
struct.pack_into('>H',expected,19*0x460+0x140,(struct.unpack_from('>H',old,19*0x460+0x140)[0]-1500)&65535)
assert after[native:native+len(expected)]==expected,'native snapshots/rebased cursors'
size=struct.unpack_from('>H',before,before.index(b'4DHISTRY')+12)[0]
old=before[companion:companion+20*size];expected=bytearray(old[size:]+old[-size:]);expected[19*size:19*size+2]=b'\0\0';assert after[companion:companion+len(expected)]==expected,'companion snapshots'
old=before[inputs:inputs+30000];expected=bytearray(old[1500:]+old[28500:]);expected[28500]=0;assert after[inputs:inputs+30000]==expected,'input shift/write'
assert before[inputs+30000:inputs+30008]==after[inputs+30000:inputs+30008]==b'4DGUARD!'
fields={'producer':0xa0,'recorded':-0x1738,'consumer':-0x940,'base':-0x2e0};actual={n:struct.unpack_from('>H',after,a4+off)[0] for n,off in fields.items()};assert actual=={'producer':28501,'recorded':28501,'consumer':28500,'base':struct.unpack_from('>H',before,a4-0x2e0)[0]+1500},actual
priv=before.index(b'4DA4PHYS')+12;assert before[priv:priv+128]==after[priv:priv+128];assert before[a4+0x228:a4+0x22e]==after[a4+0x228:a4+0x22e]
if b'4DTSTATE' in before:
 time=before.index(b'4DTSTATE')+12;time_size=struct.unpack_from('>H',before,time-2)[0];assert before[time:time+time_size]==after[time:time+time_size]
rot=before.index(b'4DHISTRY')+24;assert struct.unpack_from('>I',after,rot)[0]==struct.unpack_from('>I',before,rot)[0]+1
result={'native_snapshot_bytes_checked':22400,'companion_bytes_checked':20*size,'input_bytes_checked':30000,'guard_intact':True,'live_private_unchanged':True,'live_rng_unchanged':True,'cursors':actual,'native_rotation_passed':True}
(cap/'rotation-check.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
