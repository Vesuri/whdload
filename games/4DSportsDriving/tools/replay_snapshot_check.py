#!/usr/bin/env python3
"""Follow the native keyboard replay fixture to a real companion restore."""
import argparse,json,re,struct
from pathlib import Path
from profile_window import command,ROOT
from simulation_fixture import read_fixture
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--slot',type=int,default=0);p.add_argument('--restore-only',action='store_true');p.add_argument('--replay-tick',type=int,default=155);a=p.parse_args();cap=a.capture.resolve();m=json.loads((cap/'anchor.json').read_text());mem=(cap/'memory.bin').read_bytes();syms={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
base=m['memory_base']+mem.index(b'4DHISTRY')+28-syms['sim_history_records'];at=m['game_base']+0xe5e0
answer=command(f'gdb delete\ntbreak *{at:#x} if *(unsigned short *)($a5-2)=={a.slot}\ntbreak *{base+syms["sim_history_failed"]:#x}\ncontinue\ninfo registers pc');print(answer,flush=True)
assert int(re.search(r'^pc\s+0x([0-9a-f]+)',answer,re.M)[1],16)==at

def dump(name):
 path=cap/name;command(f'gdb dump binary memory {path.relative_to(ROOT)} 0x200000 0x600000');return path.read_bytes()
b=dump('restored-memory.bin');a4=m['data_base']+0x7ffe-m['memory_base'];tick=struct.unpack_from('>H',b,a4-0x940)[0];private=b.index(b'4DA4PHYS')+12;record_size=struct.unpack_from('>H',b,b.index(b'4DHISTRY')+12)[0];h=b.index(b'4DHISTRY')+28+a.slot*record_size
private_size=struct.unpack_from('>H',b,private-2)[0]
time_offset=8+private_size
aux_offset=time_offset+32
cam_offset=aux_offset+192
saved_native=struct.unpack_from('>I',b,a4-0x16bc)[0]-m['memory_base']+a.slot*0x460
assert b[a4-0xa80:a4-0x620]==b[saved_native:saved_native+0x460]
assert b[a4+0x228:a4+0x22e]==b[h+2:h+8]
assert b[private:private+private_size]==b[h+8:h+time_offset]
if b'4DTSTATE' in b:
 time=b.index(b'4DTSTATE')+12;time_size=struct.unpack_from('>H',b,time-2)[0];assert b[time:time+time_size]==b[h+time_offset:h+time_offset+time_size];assert struct.unpack_from('>H',b,a4+0x50)[0]==struct.unpack_from('>I',b,time+12)[0]&65535
if b'4DTSTATE' in b and time_size>=32:
 assert struct.unpack_from('>I',b,a4-0x944)[0]==struct.unpack_from('>I',b,time+28)[0]
aux=b.index(b'4DAUXPHY')+12;assert b[aux:aux+192]==b[h+aux_offset:h+cam_offset]
cam=b.index(b'4DCAM050')+12;assert b[cam:cam+8]==b[h+cam_offset:h+cam_offset+8]
result={'restored_slot':a.slot,'restored_tick':tick,'native_snapshot_exact':True,'rng_exact':True,'private_exact':True,'nonzero_private_bytes':sum(x!=0 for x in b[private:private+private_size])}
if b'4DTSTATE' in b:
 result['time_state_exact']=True;result['time_state_values']=struct.unpack_from('>'+str(time_size//4)+'I',b,b.index(b'4DTSTATE')+12)
print(result,flush=True)
if a.restore_only:
 (cap/'replay-check.json').write_text(json.dumps(result,indent=2)+'\n');raise SystemExit(0)
at=m['game_base']+0xe5f8
answer=command(f'gdb delete\ntbreak *{at:#x} if *(unsigned short *)($a4-0x940)=={a.replay_tick} && *(unsigned char *)($a4+0x45)==2\ncontinue\ninfo registers pc');print(answer,flush=True)
b=dump('replayed-memory.bin');private=b.index(b'4DA4PHYS')+12
now=b[a4-0xa80:a4-0x620]+b[a4+0x228:a4+0x22e]+b[private:private+private_size]
if b'4DTSTATE' in b:
 time=b.index(b'4DTSTATE')+12;now+=b[time:time+time_size]
aux=b.index(b'4DAUXPHY')+12;now+=b[aux:aux+192]
cam=b.index(b'4DCAM050')+12;now+=b[cam:cam+8]
old=next(state for tick,mode,state in read_fixture(cap) if tick==a.replay_tick)
assert len(now)==len(old),(len(now),len(old))
diff=[i for i,(x,y) in enumerate(zip(now,old)) if x!=y]
result.update(replayed_tick=a.replay_tick,differing_offsets=diff,replay_equal=not diff)
(cap/'replay-check.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True);assert not diff
