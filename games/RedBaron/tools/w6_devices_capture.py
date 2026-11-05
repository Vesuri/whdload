import argparse,json,re,struct,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path('tools').resolve()))
from device_replay import check
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args()
m=json.loads((a.capture/'entry.json').read_text());lines=(a.capture/'slave.lst').read_text(errors='replace').splitlines()
def symbol(name):
 for i,line in enumerate(lines):
  if re.search(r'\b'+re.escape(name)+r':',line):
   for following in lines[i:]:
    match=re.match(r'00:([0-9A-F]+)\s',following)
    if match:return int(match[1],16)
 raise ValueError(name)
from runtime_buffers import live_address
base=m['entry']['game_anchor']-symbol('tape_game_anchor');sim=m['entry']['sim'];state=base+symbol('time_loop_state');live=base+symbol('time_devices_live')
args=[f'*(unsigned int*){state+28:#x}',f'(*(unsigned int*){state+20:#x}-*(unsigned int*){state+44:#x})',f'(*(unsigned int*){sim+0x30006:#x}-*(unsigned int*){state+44:#x})',f'*(unsigned int*){live:#x}',f'*(unsigned int*){live+4:#x}','*(short*)($a5-14)','*(unsigned int*)($a5-4)','*(unsigned char*)($a5-6)']
cmd=['delete','set $n=0',f'break *{sim+0x21d30:#x}','commands','silent','printf "DEV %u %u %u %u %u %d %u %u\\n", '+', '.join(args),'set $n=$n+1','if $n < 48','continue','end','end','continue']
reply=r.command('gdb '+'\n'.join(cmd));(a.capture/'devices.log').write_text(reply)
rows=[list(map(int,s.split())) for s in re.findall(r'^DEV ([0-9 -]+)$',reply,re.M)];assert len(rows)==48,reply[-2000:]
for name,size,file in [('time_input_observe_queue',4112,'device-queue.bin'),('time_devices_log',640,'device-acquisition.bin'),('time_devices_count',8,'device-counters.bin'),('time_devices_epoch',4,'device-epoch.bin'),('time_keys_consumed',8,'device-keyboard-counters.bin')]:
 addr=live_address(lines,base,name,r.command);r.command(f'gdb dump binary memory {a.capture}/{file} {addr:#x} {addr+size:#x}')
h3=(a.capture/'entry-h3.bin').read_bytes();assert struct.unpack_from('>H',h3,0x3d0e)[0]==0,'Fixture requires native digital joystick mode'
axis=struct.unpack_from('>16h',h3,0x1e30)
result=check((a.capture/'device-queue.bin').read_bytes(),(a.capture/'device-acquisition.bin').read_bytes(),(a.capture/'device-counters.bin').read_bytes(),rows,int.from_bytes((a.capture/'device-epoch.bin').read_bytes(),'big'),axis,(a.capture/'device-keyboard-counters.bin').read_bytes())
result.update(sha256=m['slave_sha256'],max_observed_CIA_debt=max((r[2]-r[1])&0xffffffff for r in rows))
(a.capture/'device-result.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
