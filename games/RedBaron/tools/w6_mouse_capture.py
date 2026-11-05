import argparse,json,re,struct,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path('tools').resolve()))
from mouse_replay import check_capture
from mouse_ownership import check_camera_capture
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
base=m['entry']['game_anchor']-symbol('tape_game_anchor');sim=m['entry']['sim'];state=base+symbol('time_loop_state');live=base+symbol('time_mouse_live')
camera=base+symbol('time_mouse_camera')
def u(at):return f'*(unsigned int*){at:#x}'
def w(at):return f'*(unsigned short*){at:#x}'
args=[u(state+28),f'({u(state+20)}-{u(state+44)})',f'({u(sim+0x30006)}-{u(state+44)})','*(short*)($a5-10)','*(short*)($a5-8)',w(live),w(live+2)]
postargs=[u(state+28),'*(short*)($a5-24)','*(short*)($a5-22)',w(live),w(live+2),u(base+symbol('time_mouse_resets'))]
camargs=[u(state+28),'*(short*)($a5-28)','*(short*)($a5-26)',w(live),w(live+2),w(camera),w(camera+2),u(base+symbol('time_mouse_resets'))]
cmd=['delete','set $n=0',f'break *{sim+0x21dd2:#x}','commands','silent','printf "CAMC %u %d %d %u %u %u %u %u\\n", '+', '.join(camargs),'continue','end',f'break *{sim+0x21d30:#x}','commands','silent','printf "MOUSEP %u %u %u %d %d %u %u\\n", '+', '.join(args),'continue','end',f'break *{sim+0x21dba:#x}','commands','silent','printf "MOUSEC %u %d %d %u %u %u\\n", '+', '.join(postargs),'set $n=$n+1','if $n < 48','continue','end','end','continue']
reply=r.command('gdb '+'\n'.join(cmd));(a.capture/'mouse.log').write_text(reply)
rows=[list(map(int,s.split())) for s in re.findall(r'^MOUSEP ([0-9 -]+)$',reply,re.M)]
posts=[list(map(int,s.split())) for s in re.findall(r'^MOUSEC ([0-9 -]+)$',reply,re.M)]
assert len(rows)==len(posts)==48,reply[-3000:]
for name,size,file in [('time_input_observe_queue',4112,'mouse-queue.bin'),('time_mouse_log',1024,'mouse-acquisition.bin'),('time_mouse_count',12,'mouse-counters.bin'),('time_devices_epoch',4,'mouse-epoch.bin'),('time_keys_consumed',8,'mouse-keyboard-counters.bin'),('time_mouse_test_result',4,'mouse-selftest.bin'),('time_mouse_ownership_result',4,'mouse-ownership.bin'),('time_mouse_flags_count',258,'mouse-flags.bin')]:
 addr=live_address(lines,base,name,r.command);r.command(f'gdb dump binary memory {a.capture}/{file} {addr:#x} {addr+size:#x}')
queue=(a.capture/'mouse-queue.bin').read_bytes();acq=(a.capture/'mouse-acquisition.bin').read_bytes();epoch=int.from_bytes((a.capture/'mouse-epoch.bin').read_bytes(),'big')
result=check_capture(queue,acq,(a.capture/'mouse-counters.bin').read_bytes(),rows,posts,epoch,(a.capture/'mouse-keyboard-counters.bin').read_bytes(),int.from_bytes((a.capture/'mouse-selftest.bin').read_bytes(),'big'))
cams=[list(map(int,s.split())) for s in re.findall(r'^CAMC ([0-9 -]+)$',reply,re.M)]
result.update(check_camera_capture(rows,posts,cams,int.from_bytes((a.capture/'mouse-ownership.bin').read_bytes(),'big')))
flag_data=(a.capture/'mouse-flags.bin').read_bytes()
count=struct.unpack_from('>H',flag_data)[0]
assert count==2*result['native_resets'] and count<=128,count
flags=list(struct.iter_unpack('>HH',flag_data[2:2+count*2]))
assert all((old&16)==(new&16) and (new&15)==0 for old,new in flags),flags
result['reset_flag_checks']=len(flags);result['reset_incoming_x_values']=sorted({old&16 for old,_ in flags})
result['sha256']=m['slave_sha256']
(a.capture/'mouse-result.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
