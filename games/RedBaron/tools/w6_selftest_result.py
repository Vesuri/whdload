"""Read W6 native self-test counters using the capture's frozen listing."""
import argparse,json,re,struct
from pathlib import Path
import route_status as r
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--ram',type=Path);a=p.parse_args()
m=json.loads((a.capture/'entry.json').read_text());lines=(a.capture/'slave.lst').read_text(errors='replace').splitlines()
def symbol(name):
    for i,line in enumerate(lines):
        if re.search(r'\b'+re.escape(name)+r':',line):
            for following in lines[i:]:
                match=re.match(r'00:([0-9A-F]+)\s',following)
                if match:return int(match[1],16)
    raise ValueError('Missing listing symbol '+name)
base=m['entry']['game_anchor']-symbol('tape_game_anchor')
result={'sha256':m['slave_sha256']}
if a.ram:
    ram=a.ram.read_bytes()
    names=['menu_hook','emit_hook','baron','ps','sim','polls','events','anchor','control_calls','game_steps','game_anchor','inflight']
    needle=b'RBVERIFY'+struct.pack('>12I',*(m['entry'][n] for n in names))
    matches=[i for i in range(len(ram)) if ram.startswith(needle,i)]
    if len(matches)!=1:raise ValueError('Saved RAM does not match this capture marker')
    ram_base=base+symbol('tape_marker')-matches[0]
    result['source']='Saved RAM snapshot with exact flight-entry marker match'
else:
    result['source']='Live read-only debugger counter'

for name,expected in [('time_exp_result',20480),('time_core_result',426),('time_input_test_result',512),('time_present_result',638),('time_model_terrain_result',2),('time_terrain_cache_result',1),('time_present_list_result',2)]:
    address=base+symbol(name)
    if a.ram:
        got=struct.unpack_from('>I',ram,address-ram_base)[0]
    else:
        raw=r.command(f'gdb x/wu {address:#x}')
        got=int(raw.split(':',1)[1].strip())
    assert got==expected,(name,got,expected)
    result[name]=got
address=base+symbol('time_present_result')+4
if a.ram:
    got=struct.unpack_from('>I',ram,address-ram_base)[0]
else:
    raw=r.command(f'gdb x/wu {address:#x}')
    got=int(raw.split(':',1)[1].strip())
assert got==133,got
result['time_present_phase_result']=got
(a.capture/'selftest-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(result)
