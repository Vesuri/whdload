"""Explicit synthetic F-key input for a paused W6 camera inspection."""
import argparse,json,re,struct,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path('tools').resolve()))
from presentation_state import symbol
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--key',type=lambda x:int(x,0),default=0x51);a=p.parse_args()
m=json.loads((a.capture/'entry.json').read_text());lines=(a.capture/'slave.lst').read_text(errors='replace').splitlines();from runtime_buffers import live_address
base=m['entry']['game_anchor']-symbol(lines,'tape_game_anchor');at=lambda x:live_address(lines,base,x,r.command)
q=at('time_input_observe_queue');state=at('time_loop_state');h3=json.loads((a.capture/'entry-steps.json').read_text())['h3']
raw=r.command(f'gdb printf "INPUT %u %u %u %u %u %u %u\\n", *(unsigned short*){q:#x}, *(unsigned short*){q+2:#x}, *(unsigned short*){q+4:#x}, *(unsigned int*){state+20:#x}, *(unsigned int*){state+44:#x}, *(unsigned int*){state+40:#x}, *(unsigned short*){at("time_keys_ready"):#x}')
v=list(map(int,re.search(r'INPUT ([0-9 ]+)',raw)[1].split()));head,tail,overflow,cursor,paused,active,ready=v
assert head==tail and not overflow and active==ready==1,v
records=[struct.pack('>IHHII',(cursor-paused+delta)&0xffffffff,a.key,down,0,0) for delta,down in ((1,1),(2,0))]
commands=[]
for index,record in enumerate(records):
 address=q+16+((head+index)&255)*16
 commands += [f'set {{unsigned int}}{address+i:#x}={int.from_bytes(record[i:i+4],"big"):#x}' for i in range(0,16,4)]
commands += [f'set {{unsigned short}}{q+6:#x}=2',f'set {{unsigned short}}{q:#x}={(head+2)&65535}']
(a.capture/'view-probe-input.json').write_text(json.dumps(dict(kind='synthetic queued F-key; not physical acquisition',before=v,key=a.key,records=[x.hex() for x in records],commands=commands),indent=2)+'\n')
r.command('gdb '+'\n'.join(commands))
stop=at('time_pose_captured')
raw=r.command(f'gdb delete\nbreak *{stop:#x}\ncontinue\ndelete\nprintf "VIEW %u %u %u %u %u\\n", *(unsigned int*){at("time_pose_header")+4:#x}, *(unsigned short*){h3+0x6712:#x}, *(unsigned int*){h3+0x8d72:#x}, *(unsigned int*){h3+0x67ae:#x}, *(unsigned int*){h3+0x1a70:#x}')
(a.capture/'view-probe-result.log').write_text(raw);print(raw)
files=[]
for lo,hi in r.memory_regions():
 file=a.capture/f'view-probe-after-{lo:x}.bin';r.command(f'gdb dump binary memory {file} {lo:#x} {hi:#x}')
 files.append(dict(base=lo,size=hi-lo,file=file.name))
(a.capture/'view-probe.json').write_text(json.dumps(dict(sha256=m['slave_sha256'],h3=h3,banks=files),indent=2)+'\n')
