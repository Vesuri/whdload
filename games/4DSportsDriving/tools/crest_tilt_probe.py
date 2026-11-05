#!/usr/bin/env python3
"""Capture native geometry needed to derive pitch/roll reconstruction bias."""
import json,re,sys
from pathlib import Path
from profile_window import command,ROOT
cap=Path(sys.argv[1]).resolve();m=json.loads((cap/'anchor.json').read_text());g=m['game_base'];rate=m['active_simulation_word'];steps=round(float(sys.argv[2])*rate)-m['simulation_tick']
assert steps>0 and m['opponent']==0

def log(tag,expr):return 'printf "'+tag+' '+' '.join('%d' for _ in expr)+'\\n", '+', '.join(expr)+'\n'
def words(at,n):return [f'*(short *)({at}{2*i:+d})' for i in range(n)]
script='gdb delete\nset $n=0\n'
for address,tag in [(0xc60c,'BUILT'),(0xd49e,'YAW'),(0xd4aa,'YAW_OUT'),(0xd514,'PITCH'),(0xd584,'PITCH_OUT'),(0xd5f2,'ROLL'),(0xd65e,'ROLL_OUT')]:
 script+=f'break *{g+address:#x}\ncommands\nsilent\n'
 expr=['*(unsigned short *)($a4-0x940)']
 if tag=='BUILT':
  expr+=['*(unsigned int *)($a5+8)']+words('(*(unsigned int *)($a5+8))+24',3)
  expr+=words('(*(unsigned int *)($a5+8))+84',4)+words('$a4+0xbae',9)
  expr+=[f'*(int *)($a5-0xe2+{4*i})' for i in range(12)]
  expr+=['*(short *)($a5-8)','*(char *)($a5-0x1cc)']
  expr += [f'*(int *)(*(unsigned int *)($a5+8)+{4*i})' for i in range(3)]
 elif tag=='YAW':
  expr+=words('$a5-0x72',1)+words('$a5-0x74',1)
 elif tag=='YAW_OUT':
  expr+=['*(unsigned short *)($a4+0xbac)']
 elif tag in ('PITCH','ROLL'):
  expr+=words('$a5-0x28',9)+words('$a5-0x102',12)
  expr+=['*(short *)($a4+0xbaa)','*(short *)($a4+0xbac)']
 else:expr+=['*(short *)($a4+0xbaa)' if tag=='PITCH_OUT' else '*(short *)($a4+0xba8)']
 script+=log(tag,expr)+'continue\nend\n'
script+=f'break *{g+0xe7b4:#x}\ncommands\nsilent\nset $n=$n+1\nif $n<{steps}\ncontinue\nend\nend\ncontinue\ninfo registers pc'
(cap/'tilt-baseline.gdb').write_text(script);command_file=cap/'tilt-baseline.commands.gdb';command_file.write_text(script.removeprefix('gdb '));out=command('gdb source '+str(command_file));(cap/'tilt-baseline.txt').write_text(out)
assert int(re.search(r'^pc\s+0x([0-9a-f]+)',out,re.M)[1],16)==g+0xe7b4
records={tag:[list(map(int,s.split())) for s in re.findall(r'^'+tag+r' (.*)$',out,re.M)] for tag in ('BUILT','YAW','YAW_OUT','PITCH','PITCH_OUT','ROLL','ROLL_OUT')}
assert all(len(v)==steps for v in records.values()),{k:len(v) for k,v in records.items()}
result=dict(rate=rate,steps=steps,records=records)
(cap/'tilt-baseline.json').write_text(json.dumps(result,indent=2)+'\n')
command('gdb delete')
print({k:len(v) for k,v in records.items()})
