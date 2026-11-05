#!/usr/bin/env python3
"""Disable only the isolated test duration at the pre-stall checkpoint."""
import json,re,struct,sys
from pathlib import Path
from profile_window import command,ROOT
p=Path(sys.argv[1]).resolve();m=json.loads((p/'anchor.json').read_text());before=(p/'memory.bin').read_bytes()
s={k:int(v,16) for k,v in re.findall(r'^(\w+)\s+00:([0-9a-fA-F]+)\s*$',(p/'slave.lst').read_text(encoding='latin1'),re.M)}
base=m['marker']+8-s['tape_game'];at=base+s['sim_stall_duration'];offset=at-m['memory_base']
assert struct.unpack_from('>I',before,offset)[0]==80
assert struct.unpack_from('>H',before,base+s['sim_stall_done']-m['memory_base'])[0]==0
pc=command('gdb info registers pc')
assert int(re.search(r'pc\s+0x([0-9a-f]+)',pc)[1],16)==m['game_base']+0xe5f8
target=(p/'control-seeded.bin').relative_to(ROOT)
command(f'gdb set {{unsigned int}}{at:#x} = 0\ndump binary memory {target} 0x200000 0x600000')
after=(p/'control-seeded.bin').read_bytes();assert struct.unpack_from('>I',after,offset)[0]==0
assert all(a==b or offset<=i<offset+4 for i,(a,b) in enumerate(zip(before,after)))
(p/'control-write.json').write_text(json.dumps(dict(address=at,before=80,after=0,only_duration_changed=True),indent=2)+'\n')
print('Verified: only the private duration changed from80 to0')
