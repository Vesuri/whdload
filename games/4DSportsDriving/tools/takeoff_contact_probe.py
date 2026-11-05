#!/usr/bin/env python3
"""Read clearance, gravity selection and contact reset at the takeoff boundary."""
import json,re,sys
from pathlib import Path
from profile_window import command
p=Path(sys.argv[1]); m=json.loads((p/'anchor.json').read_text()); g=m['game_base']; end=round(float(sys.argv[2])*m['active_simulation_word'])
s='gdb delete\n'
fields=['*(unsigned short *)($a4-0x940)','*(unsigned char *)($a5-3)','*(short *)($a4+0xbc0)','*(short *)($a5-8)','*(short *)(*(unsigned int *)($a5+8)+0x4c+2*(*(unsigned char *)($a5-3)))','*(int *)(*(unsigned int *)($a5-0xe6)+4)']
for off,tag in [(0xcb06,'SELECT'),(0xcb48,'GRAVITY'),(0xcc2e,'AFTER'),(0xcc9e,'ZERO'),(0xd1b0,'PENETRATION_ZERO')]:
 s+=f'break *{g+off:#x}\ncommands\nsilent\nprintf "{tag} '+ ' '.join(['%d']*len(fields))+'\\n", '+', '.join(fields)+'\ncontinue\nend\n'
s+=f'break *{g+0xe7b4:#x}\ncommands\nsilent\nif *(unsigned short *)($a4-0x940)<{end}\ncontinue\nend\nend\ncontinue\ndelete\n'
(p/'takeoff-contact.gdb').write_text(s);out=command(s);(p/'takeoff-contact.txt').write_text(out)
rows=[]
for tag,v in re.findall(r'^(SELECT|GRAVITY|AFTER|ZERO|PENETRATION_ZERO) (.*)$',out,re.M):
 row=dict(zip(('tick','wheel','clearance','correction','velocity','world_y'),map(int,v.split())));row['event']=tag;rows.append(row)
assert rows and max(r['tick'] for r in rows)==end
result=dict(rate=m['active_simulation_word'],end=end,rows=rows,counts={t:sum(r['event']==t for r in rows) for t in ('SELECT','GRAVITY','AFTER','ZERO','PENETRATION_ZERO')})
(p/'takeoff-contact.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['counts']))
