"""Capture actual scheduled world boundaries; never infer progress from swaps."""
import argparse,json,re
from pathlib import Path
import route_status as r
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--steps',type=int,default=80);a=p.parse_args()
m=json.loads((a.capture/'entry.json').read_text());lines=(a.capture/'slave.lst').read_text(errors='replace').splitlines()
def symbol(name):
 for i,line in enumerate(lines):
  if re.search(r'\b'+re.escape(name)+r':',line):
   for following in lines[i:]:
    match=re.match(r'00:([0-9A-F]+)\s',following)
    if match:return int(match[1],16)
 raise ValueError(name)
base=m['entry']['game_anchor']-symbol('tape_game_anchor');state=base+symbol('time_loop_state');sim=m['entry']['sim']
# h3 is read from the installed relocation, not guessed from another boot.
reply=r.command(f'gdb x/wx {base+symbol("time_loop_h3"):#x}')
h3=int(re.search(r':\s+0x([0-9a-f]+)',reply)[1],16)
fmt='LOOP %u %u %u %u %u %u %u %u %u %u %u\\n'
args=[f'*(unsigned int*){x:#x}' for x in (state+28,state+20,sim+0x30006,state+32,state+36)]
args += [f'*(unsigned short*){x:#x}' for x in (h3+0x4834,h3+0x4838,state+24,state+26)]
args += [f'*(unsigned int*){x:#x}' for x in (state+40,state+44)]
log=f'printf "{fmt}", '+', '.join(args)
cmd=['delete',log,'set $w6seen=0',f'break *{m["entry"]["game_anchor"]:#x}','commands','silent',log,'set $w6seen=$w6seen+1',f'if $w6seen < {a.steps}','continue','end','end','continue']
reply=r.command('gdb '+'\n'.join(cmd));(a.capture/'loop.log').write_text(reply)
rows=[list(map(int,x.split())) for x in re.findall(r'^LOOP ([0-9 ]+)$',reply,re.M)]
assert len(rows)==a.steps+1,(len(rows),reply[-2000:])
assert all(row[5]==225 and row[6]==33 and row[9]==1 for row in rows),rows[:3]
# With zero initial phase and F=33, tick N is due at ceil(N*225*33/1024).
epoch=(rows[0][1] - rows[0][10] - ((rows[0][0]*225*33+1023)//1024)) & 0xffffffff
for row in rows:
 step,cursor,now,*_=row
 assert (cursor-row[10]-epoch)&0xffffffff == (step*225*33+1023)//1024,row
 assert ((now-cursor)&0xffffffff)<2**31,row
assert all(y[0]==x[0]+1 for x,y in zip(rows,rows[1:]))
result={'sha256':m['slave_sha256'],'epoch':epoch,'rows':len(rows),'first':rows[0],'last':rows[-1],'schema':['scheduled_world_tick','cursor','CIA_now','skipped_draws','draw_opportunities','primary_dt','F','same_boundary_due','unserviced_secondary','active','paused_CIA'],'exact_deadlines':True,'note':'Native world/input/camera not yet certified render-independent; no FPS claim.'}
(a.capture/'loop-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
