#!/usr/bin/env python3
"""Stop at a source-owned scenario checkpoint, save game state and visible output."""
import argparse,json,re,struct
from pathlib import Path
from profile_window import command
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--symbol',default='tape_scenario_done');p.add_argument('--label',default='scenario');a=p.parse_args();cap=a.capture
m=json.loads((cap/'anchor.json').read_text());b=(cap/'slave.slave').read_bytes();sl=m['marker']-b.index(b'4DTAPE!!')+32
symbols={n:int(v,16)+sl for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
command('stop');command('gdb delete')
checks='\n'.join(f'tbreak *{symbols[n]:#x}' for n in [a.symbol,'tape_scenario_failed','twin_failed','math_failed','book_failed'] if n in symbols)
answer=command('gdb '+checks+'\ncontinue\ninfo registers');print(answer,flush=True)
pc=int(re.search(r'^pc\s+0x([0-9a-f]+)',answer,re.M)[1],16)
assert pc==symbols[a.symbol],f'Scenario stopped at failure checkpoint {pc:#x}; emulator left paused'
path=cap/f'{a.label}-state.bin';data=m['data_base'];print(command(f'gdb dump binary memory {path} {data:#x} {data+0xa77c:#x}'))
state=path.read_bytes();a4=0x7ffe;result={'mode':state[a4+0x45],'attract':state[a4-0x16d8],'end_flag':state[a4+0x42],'car_end_reason':state[a4-0x92e+0xc9],'replay_selector':state[a4-0x74c1],'replay_paused':state[a4+0x44],'replay_position':struct.unpack_from('>H',state,a4-0x940)[0],'graphics':state[a4-0x7708],'simulation':struct.unpack_from('>H',state,a4-0xbc)[0]}
path=cap/f'{a.label}-perf.bin';at=symbols['perf_game'];command(f'gdb dump binary memory {path} {at:#x} {at+20:#x}');raw=path.read_bytes();result['perf']=struct.unpack('>IHHII',raw[:16]);assert result['perf'][3]==0,result
assert result['mode']==2 and result['attract']==0,result
assert result['replay_selector']==3 and result['replay_paused']==0,result
assert result['replay_position']>0,result
assert result['graphics']==0 and result['simulation']==10,result
result['validation_passed']=True
(cap/f'{a.label}.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
# Wait for a completed buffer switch: the keyboard task can stop mid-draw.
print(command(f'gdb tbreak *{m["game_base"]+0x7500:#x}\ncontinue\ninfo registers pc'),flush=True)
print(command(f'shot {cap}/{a.label}.png'),flush=True)
