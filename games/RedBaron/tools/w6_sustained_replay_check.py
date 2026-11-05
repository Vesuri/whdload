"""Validate scheduled replay records and native input rows in a field census."""
import json,re,struct,sys
from pathlib import Path
sys.path.insert(0,'tools')
from keyboard_replay import check_capture
p=Path(sys.argv[1])
def read(n):return (p/(n+'.bin')).read_bytes()
meta=json.loads((p/'entry.json').read_text())
options=int(re.search(r'CUSTOM5=(-?\d+)',meta['whd_args'])[1]) & 0xffffffff
assert options & (1<<31)
first_key=0x51 if options & (1<<4) else 0x4e
status,origin=struct.unpack('>HI',read('time_input_replay_done'))
assert status==2
records=read('time_input_replay_records')
fixture=b''
for i,(key,down) in enumerate(((first_key,1),(first_key,0),(0x40,1),(0x40,0))):
 deadline,k,d,x,y=struct.unpack_from('>IHHII',records,16*i)
 assert (deadline,k,d,x,y)==((origin+32*(i+1))&0xffffffff,key,down,0,0)
 # Existing acquisition oracle maps acquired+1 to the eligible boundary.
 # These are scheduled deadlines, not evidence of physical key acquisition.
 fixture+=struct.pack('>IHH',(deadline-1)&0xffffffff,key,down)
rows=[list(map(int,x.split())) for log in sorted(p.glob('census-*.log')) for x in re.findall(r'^KEY ([0-9 -]+)$',log.read_text(),re.M)]
h=(p/'entry-h3.bin').read_bytes()
result=check_capture(read('time_input_observe_queue'),fixture,rows,0,struct.unpack_from('>h',h,0x1e30)[0],struct.unpack_from('>h',h,0x1e40)[0],read('time_keys_commands'),read('time_keys_consumed'),first_key=first_key)
result.update(origin=origin,scope='Scheduled first-key/Fire replay and native per-world inputs; not physical acquisition, resulting camera state or gameplay-state equivalence.')
(p/'scheduled-replay-check.json').write_text(json.dumps(result,indent=2)+'\n')
print(result)
