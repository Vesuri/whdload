#!/usr/bin/env python3
"""Read clearance, gravity selection and contact reset at the takeoff boundary."""
import json,re,sys
from pathlib import Path
from profile_window import command
precise='--precise' in sys.argv
p=Path(sys.argv[1]); m=json.loads((p/'anchor.json').read_text()); g=m['game_base']; end=round(float(sys.argv[2])*m['active_simulation_word'])
mem=(p/'memory.bin').read_bytes(); private=m['memory_base']+mem.index(b'4DA4PHYS')+12
s='gdb delete\n'
fields=['*(unsigned short *)($a4-0x940)','*(unsigned char *)($a5-3)','*(short *)($a4+0xbc0)','*(short *)($a5-8)','*(short *)(*(unsigned int *)($a5+8)+0x4c+2*(*(unsigned char *)($a5-3)))','*(int *)(*(unsigned int *)($a5-0xe6)+4)']
fields += ['*(int *)(*(unsigned int *)($a5-0xe6))','*(int *)(*(unsigned int *)($a5-0xe6)+8)','*(short *)($a4+0x96)']
fields += [f'*(short *)($a4+{o})' for o in (0x94,0x92,0x90)]
fields += [f'*(short *)(*(unsigned int *)($a4+0x1ee)+{o})' for o in (4,6,8,10,12,14)]
fields += ['*(short *)(*(unsigned int *)($a5+8)+0x54+2*(*(unsigned char *)($a5-3)))']
fields += [f'*(short *)({private+off}+{stride}*(*(unsigned char *)($a5-3)))' for off,stride in ((8,4),(10,4),(24,2))]
for off,tag in [(0xcb06,'SELECT'),(0xcb48,'GRAVITY'),(0xcc2e,'AFTER'),(0xcc9e,'ZERO'),(0xd1b0,'PENETRATION_ZERO')]:
 s+=f'break *{g+off:#x}\ncommands\nsilent\nprintf "{tag} '+ ' '.join(['%d']*len(fields))+'\\n", '+', '.join(fields)+'\ncontinue\nend\n'
s+=f'break *{g+0xe7b4:#x}\ncommands\nsilent\nif *(unsigned short *)($a4-0x940)<{end}\ncontinue\nend\nend\ncontinue\ndelete\n'
(p/'takeoff-plane.gdb').write_text(s);out=command(s);(p/'takeoff-plane.txt').write_text(out)
rows=[]
for tag,v in re.findall(r'^(SELECT|GRAVITY|AFTER|ZERO|PENETRATION_ZERO) (.*)$',out,re.M):
 row=dict(zip(('tick','wheel','clearance','correction','velocity','world_y','world_x','world_z','plane','base_x','base_y','base_z','node_x','node_y','node_z','normal_x','normal_y','normal_z','extension','velocity_fraction','position_fraction','extension_fraction'),map(int,v.split())));row['event']=tag;rows.append(row)
assert rows and max(r['tick'] for r in rows)==end
result=dict(rate=m['active_simulation_word'],end=end,rows=rows,counts={t:sum(r['event']==t for r in rows) for t in ('SELECT','GRAVITY','AFTER','ZERO','PENETRATION_ZERO')})
(p/'takeoff-plane.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['counts']))

# Reconstruct the native signed-word inputs and truncating signed quotient.
from fractions import Fraction
def w(n):return (n+32768)%65536-32768
def trunc(n,d):return (abs(n)//d)*(1 if n>=0 else -1)
checks=[]
for r in rows:
 if r['event'] not in ('SELECT','AFTER'):continue
 origin=[w(r['base_'+a]+r['node_'+a]) for a in 'xyz']
 world=[r['world_'+a] for a in 'xyz']
 delta=[w(w(v>>6)-o) for v,o in zip(world,origin)]
 if r['plane']<4:
  predicted=delta[1]; exact=Fraction(world[1],64)-origin[1]
 else:
  normal=[r['normal_'+a] for a in 'xyz']
  dot=sum(v*n for v,n in zip(delta,normal));predicted=w(trunc(dot,8192))
  exact=sum((Fraction(v,64)-o)*n for v,o,n in zip(world,origin,normal))/8192
 native_prediction=predicted
 if precise and r['plane']>=4:predicted=w(int(exact))
 assert predicted==r['clearance'],(r,predicted)
 checks.append(dict(tick=r['tick'],wheel=r['wheel'],event=r['event'],native_prediction=native_prediction,plane=r['plane'],clearance=predicted,unrounded_plane_distance=str(exact),unrounded_world_distance=float(exact*64)))
result['precision']='raw-coordinate-single-truncation' if precise else 'native-coordinate-floors'
result['plane_checks']=checks
(p/'takeoff-plane.json').write_text(json.dumps(result,indent=2)+'\n')
print(f'{len(checks)} plane distances independently reproduced')
