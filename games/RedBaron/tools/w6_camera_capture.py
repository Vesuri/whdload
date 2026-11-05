import argparse,json,re,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path("tools").resolve()))
from camera_service import check_capture
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args()
m=json.loads((a.capture/'entry.json').read_text());lines=(a.capture/'slave.lst').read_text(errors='replace').splitlines()
def symbol(name):
 for i,line in enumerate(lines):
  if re.search(r'\b'+re.escape(name)+r':',line):
   for following in lines[i:]:
    match=re.match(r'00:([0-9A-F]+)\s',following)
    if match:return int(match[1],16)
 raise ValueError(name)
base=m['entry']['game_anchor']-symbol('tape_game_anchor');sim=m['entry']['sim'];state=base+symbol('time_loop_state');h3=json.loads((a.capture/'entry-steps.json').read_text())['h3'];keys=base+symbol('time_keys_commands');mouse=base+symbol('time_mouse_live');cam=base+symbol('time_mouse_camera');controls=base+symbol('time_camera_controls')
def u(at):return f'*(unsigned int*){at:#x}'
def w(at):return f'*(unsigned short*){at:#x}'
def s(at):return f'*(short*){at:#x}'
def dump(at,n,name):r.command(f'gdb dump binary memory {a.capture}/{name} {at:#x} {at+n:#x}')
dump(state,60,'camera-initial-clock.bin')
common=[f'({u(state+20)}-{u(state+44)})',w(state+26),u(state+28),w(state+16),w(keys),w(keys+2),u(base+symbol('time_keys_popped')),w(h3+0x4836),w(mouse),w(mouse+2),w(cam),w(cam+2),w(h3+0x678e),w(h3+0x6792),w(h3+0x6712),w(h3+0x1ada)]
post=common+[w(controls),w(controls+2),s(controls+4),s(controls+6),u(base+symbol('time_camera_calls')),u(base+symbol('time_camera_updates'))]
cmd=['delete','set $n=0',f'break *{base+symbol("time_camera_advance"):#x} if ($d1 & 65535) && {w(base+symbol("time_keys_ready"))}', 'commands','silent','printf "CPRE '+('%u '*16).strip()+'\\n", '+', '.join(common),'continue','end',f'break *{base+symbol("time_camera_observe"):#x}','commands','silent','printf "CPOST '+('%u '*18+'%d %d %u %u').strip()+'\\n", '+', '.join(post),'set $n=$n+1','if $n < 160','continue','end','end','continue']
reply=r.command('gdb '+'\n'.join(cmd));(a.capture/'camera.log').write_text(reply)
pre=[list(map(int,x.split())) for x in re.findall(r'^CPRE ([0-9 -]+)$',reply,re.M)];posts=[list(map(int,x.split())) for x in re.findall(r'^CPOST ([0-9 -]+)$',reply,re.M)]
assert len(pre)==len(posts)==160,(len(pre),len(posts),reply[-2000:])
result=check_capture(pre,posts)
result['sha256']=m['slave_sha256']
(a.capture/'camera-result.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
