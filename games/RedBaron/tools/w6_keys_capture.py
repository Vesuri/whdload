import argparse,json,re,struct,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path('tools').resolve()))
from keyboard_replay import check_capture
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--modal',action='store_true');a=p.parse_args()
m=json.loads((a.capture/'entry.json').read_text());lines=(a.capture/'slave.lst').read_text(errors='replace').splitlines()
def symbol(name):
 for i,line in enumerate(lines):
  if re.search(r'\b'+re.escape(name)+r':',line):
   for following in lines[i:]:
    match=re.match(r'00:([0-9A-F]+)\s',following)
    if match:return int(match[1],16)
 raise ValueError(name)
from runtime_buffers import live_address
base=m['entry']['game_anchor']-symbol('tape_game_anchor');sim=m['entry']['sim']
state=base+symbol('time_loop_state');bitmap=base+symbol('time_keys_bitmap')
args=[f'*(unsigned int*){state+28:#x}',f'(*(unsigned int*){state+20:#x}-*(unsigned int*){state+44:#x})',f'(*(unsigned int*){sim+0x30006:#x}-*(unsigned int*){state+44:#x})',f'*(unsigned char*){bitmap+0x4e:#x}',f'*(unsigned char*){bitmap+0x40:#x}','*(unsigned char*)($a5-6)','*(short*)($a5-14)','*(unsigned int*)($a5-4)',f'*(unsigned int*){base+symbol("time_keys_popped"):#x}']
cmd=['delete','set $n=0',f'break *{sim+0x21d30:#x}','commands','silent','printf "KEY %u %u %u %u %u %u %d %u %u\\n", '+', '.join(args),'set $n=$n+1',f'if $n < {80 if a.modal else 40}','continue','end','end','continue']
if a.modal:
 cmd[1:1]=[f'break *{base+symbol("time_pause_preferences"):#x}','commands','silent','printf "PREFERENCES\\n"','continue','end',f'break *{sim+0x1098:#x}','commands','silent',f'printf "WORLD %u\\n", *(unsigned int*){state+40:#x}','continue','end']
reply=r.command('gdb '+'\n'.join(cmd));(a.capture/'keyboard.log').write_text(reply)
rows=[list(map(int,s.split())) for s in re.findall(r'^KEY ([0-9 -]+)$',reply,re.M)]
assert len(rows)==(80 if a.modal else 40),reply[-2000:]
for name,size,file in [('time_input_observe_queue',4112,'keyboard-queue.bin'),('time_input_fixture_log',64 if a.modal else 32,'keyboard-acquisition.bin'),('time_keys_commands',516,'keyboard-commands.bin'),('time_keys_consumed',8,'keyboard-counters.bin'),('time_loop_state',60,'keyboard-clock.bin')]:
 addr=live_address(lines,base,name,r.command);r.command(f'gdb dump binary memory {a.capture}/{file} {addr:#x} {addr+size:#x}')
clocks=None
if a.modal:
 addr=base+symbol('time_input_fixture_clocks');r.command(f'gdb dump binary memory {a.capture}/keyboard-acquisition-clocks.bin {addr:#x} {addr+128:#x}')
 clocks=(a.capture/'keyboard-acquisition-clocks.bin').read_bytes()
 assert reply.count('PREFERENCES\n')==1,reply[-2000:]
 worlds=re.findall(r'^WORLD (\d+)$',reply,re.M)
 assert len(worlds)==79 and set(worlds)=={'1'},worlds
 epoch=rows[0][1]-(rows[0][0]*225*33+1023)//1024
 assert all(r[1]-epoch==(r[0]*225*33+1023)//1024 for r in rows)
h3=(a.capture/'entry-h3.bin').read_bytes();center=struct.unpack_from('>h',h3,0x1e30)[0];right=struct.unpack_from('>h',h3,0x1e40)[0]
excluded=struct.unpack_from('>I',(a.capture/'keyboard-clock.bin').read_bytes(),44)[0]
result=check_capture((a.capture/'keyboard-queue.bin').read_bytes(),(a.capture/'keyboard-acquisition.bin').read_bytes(),rows,excluded,center,right,(a.capture/'keyboard-commands.bin').read_bytes(),(a.capture/'keyboard-counters.bin').read_bytes(),clocks=clocks)
result.update(modal_test=a.modal,sha256=m['slave_sha256'],excluded=excluded,center_x=center,right_x=right)
(a.capture/'keyboard-result.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
