#!/usr/bin/env python3
"""Trace native penetration branch decisions and before/after wheel vectors."""
import json,re,sys
from pathlib import Path
from profile_window import command
p=Path(sys.argv[1]);m=json.loads((p/'anchor.json').read_text());g=m['game_base'];end=round(float(sys.argv[2])*m['active_simulation_word'])
fields=[('tick','*(unsigned short *)($a4-0x940)'),('wheel','*(unsigned char *)($a5-3)'),('clearance','*(short *)($a4+0xbc0)'),('plane','*(short *)($a4+0x96)'),('distance','*(unsigned short *)($a5-6)'),('velocity','*(short *)(*(unsigned int *)($a5+8)+0x4c+2*(*(unsigned char *)($a5-3)))')]
for prefix,ptr in [('old', '-0xea'),('new','-0xe6')]:
 for i,a in enumerate('xyz'):fields.append((prefix+'_'+a,f'*(int *)(*(unsigned int *)($a5{ptr})+{4*i})'))
for prefix,off in [('old_plane',-0x5e),('new_plane',-0x64),('correction',-0x46)]:
 for i,a in enumerate('xyz'):fields.append((prefix+'_'+a,f'*(short *)($a5+({off+2*i}))'))
for i in range(9):fields.append((f'matrix{i}',f'*(short *)($a5+({-0x3a+2*i}))'))
for i,a in enumerate('xyz'):fields.append(('origin_'+a,f'*(short *)($a5+({-0x4c+2*i}))'))
for i,a in enumerate('xyz'):fields.append(('normal_'+a,f'*(short *)(*(unsigned int *)($a4+0x1ee)+{10+2*i})'))
for i,a in enumerate('xyz'):fields.append(('resolved_'+a,f'*(short *)($a4+{0x1f8+2*i})'))
fields += [('ratio_total','*(short *)($a5-0x76)'),('ratio_rest','*(short *)($a5-0x74)'),('plane_flags','*(unsigned char *)($a4+0x40)'),('impact_flags','*(unsigned char *)(*(unsigned int *)($a5+8)+0xcf)')]
expr=', '.join(v for _,v in fields);fmt=' '.join('%d' for _ in fields)
s='gdb delete\nset $pen=0\n'
stages=[(0xccb2,'ENTER'),(0xcda8,'ROTATED'),(0xce3e,'CLASSIFY'),(0xd0a2,'REQUERY'),(0xd132,'PUSH_VECTOR'),(0xd15a,'RESOLVED'),(0xd1b8,'DONE')]
for off,tag in stages:
 s+=f'break *{g+off:#x}\ncommands\nsilent\n'
 if tag=='ENTER':s+='set $pen=1\n'
 s+='if $pen\n'+f'printf "{tag} {fmt}\\n", {expr}\n'
 if tag=='DONE':s+='set $pen=0\n'
 s+='end\ncontinue\nend\n'
s+=f'break *{g+0xe7b4:#x}\ncommands\nsilent\nif *(unsigned short *)($a4-0x940)<{end}\ncontinue\nend\nend\ncontinue\ndelete\n'
(p/'penetration.gdb').write_text(s);script=p/'penetration.commands.gdb';script.write_text(s.removeprefix('gdb '));out=command('gdb source '+str(script));(p/'penetration.txt').write_text(out);tags='|'.join(t for _,t in stages);rows=[]
for tag,line in re.findall(r'^('+tags+r') (.*)$',out,re.M):
 r=dict(zip((k for k,_ in fields),map(int,line.split())));r['stage']=tag;rows.append(r)
assert rows
result=dict(rate=m['active_simulation_word'],end=end,rows=rows,scope='Read-only native penetration branch trace; fields are meaningful only after their initializing stage.')
(p/'penetration.json').write_text(json.dumps(result,indent=2)+'\n')
print([(r['tick'],r['wheel'],r['stage'],r['clearance']) for r in rows])
