#!/usr/bin/env python3
"""Verify menu selection and native-derived rate state without fixture arming."""
import argparse,json,re,struct
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--rate',type=int,choices=(10,20,50),required=True);a=p.parse_args()
b=(a.capture/'memory.bin').read_bytes();m=json.loads((a.capture/'anchor.json').read_text());lst=(a.capture/'slave.lst').read_text(encoding='latin1')
sym={n:int(v,16) for n,v in re.findall(r'^([\w.]+)\s+00:([0-9A-Fa-f]+)\s*$',lst,re.M)}
base=m['marker']+8-sym['tape_game']-m['memory_base'];pos=base+sym['sim_mode_opens'];opens,changes,old,new,active,recorded=struct.unpack_from('>II4H',b,pos)
assert opens>=1
if a.rate!=20:
 assert (changes,old,new,active,recorded)==(1,20,a.rate,20,20),(changes,old,new,active,recorded)
else:assert changes==0
at=m['data_base']+0x7ffe-m['memory_base'];word=lambda off:struct.unpack_from('>H',b,at+off)[0]
assert (word(-0xbc),word(-0x15fa),b[at-0x173a])==(a.rate,)*3
assert (word(-0xba),word(0xb30),word(-0xbe))==(a.rate*30,a.rate*600,100//a.rate)
ptr=struct.unpack_from('>I',b,at-0xb8)[0];assert ptr==m['data_base']+0x7ffe-(0x73b4 if a.rate==10 else 0x73f4)
result={'opens':opens,'changes':changes,'choice':{'previous':old,'selected':new,'active_at_choice':active,'recorded_at_choice':recorded},'after_restart_rate':a.rate,'snapshot_ticks':word(-0xba),'history_bytes':word(0xb30),'divider':word(-0xbe),'steering_table':'Normal' if a.rate==10 else 'A2500'}
(a.capture/'mode-menu-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
