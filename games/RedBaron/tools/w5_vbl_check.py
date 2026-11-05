"""Read-only live check of the W5 VBlank replay against its architecture model."""
import json,re,struct,sys
from pathlib import Path
import route_status as r,step_log
sys.path.insert(0,'tools')
from pacing_model import vbl_replay
out=Path(sys.argv[1]);m=json.loads((out/'entry.json').read_text());sim=m['entry']['sim']
listing=(out/'slave.lst').read_text(encoding='latin1')
def label(n): return int(re.search(r'^'+n+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16)
base=m['entry']['game_anchor']-label('tape_game_anchor');counter=base+label('pace_state')
def regs(): return {k:int(v,16) for k,v in re.findall(r'^(\w+)\s+0x([0-9a-f]+)',r.command('gdb info registers'),re.M)}
def dump(name,address,length):
 path=out/name;r.command(f'gdb dump binary memory {path} {address:#x} {address+length:#x}');return path.read_bytes()
assert dump('pacing-call-bytes.bin',sim+0xb06,10)==bytes.fromhex('7001')+struct.pack('>HIH',0x4eb9,base+label('pace_flight'),0x4e71)
assert dump('pacing-vbl-bytes.bin',sim+0x2d34e,6)==struct.pack('>HI',0x4eb9,base+label('pace_vbl'))
r.command(f'until {sim+0x2d34e:#x}');before=regs();assert before['pc']==sim+0x2d34e
values=struct.unpack('>4IH',dump('vbl-input.bin',before['a1'],18));count=struct.unpack('>I',dump('vbl-counter-before.bin',counter,4))[0]
r.command(f'until {sim+0x2d354:#x}');after=regs();expected=vbl_replay(before,values[:4],values[4]);expected['pc']=sim+0x2d354
actual_count=struct.unpack('>I',dump('vbl-counter-after.bin',counter,4))[0]
result=dict(before=before,after=after,expected=expected,count_before=count,count_after=actual_count,registers_match=all(after[k]==v for k,v in expected.items() if k not in ('sr','ps')),condition_code_scope='GDB exposes stale packed SR: known-zero MOVE control retains Z=0; CCR contract follows replayed instructions and host model',counter_match=actual_count==((count+1)&0xffffffff))
(out/'vbl-contract.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
assert result['registers_match'] and result['counter_match']
# Return to a main-flight checkpoint before any subsequent helper.
r.command(f'until {m["entry"]["game_anchor"]:#x}')
