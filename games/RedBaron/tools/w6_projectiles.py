import json,re,sys
from pathlib import Path
import route_status as r,step_log
out=Path(sys.argv[1]);at=r.locate();st=r.read(at);obs,h=step_log.header();sim,h3=st['sim'],h[5]
raw=r.command(f'gdb x/wx {h3+0x4578:#x}');player=int(re.findall(r':\s*(0x[0-9a-f]+)',raw)[0],16)
cmd=[]
for name,off in [('move',0x10e74),('result',0x11256)]:
 cmd += [f'break *{sim+off:#x}','commands','silent',f'printf "PROJECTILE {name} %u %u %u %u %d %d %d %d %d %d %d %d %d\\n", *(unsigned long *){at+44:#x}, $a2, *(unsigned long *)($a2+38), $d0, *(short *)($a2+34), *(short *)($a2+36), (short)$d7, *(int *)$a3, *(int *)($a3+4), *(int *)($a3+8), *(int *)($a2+8), *(int *)($a2+12), *(int *)($a2+16)','continue','end']
cmd += [f'break *{sim+0x21f4a:#x}',f'break *{st["game_anchor"]:#x}','ignore $bpnum 39','continue','printf "PROJECTILE_STOP %u\\n", $pc','delete']
reply=r.command('gdb '+'\n'.join(cmd));(out/'projectile-log.txt').write_text(reply)
rows=[]
for match in re.finditer(r'PROJECTILE (move|result) ((?:-?\d+ ?){13})',reply):
 v=list(map(int,match[2].split()));assert len(v)==13,v
 rows.append(dict(kind=match[1],step=v[0],object=v[1],owner=v[2],d0=v[3],life=v[4],speed=v[5],distance=v[6],old=v[7:10],new=v[10:13]))
stop=re.search(r'PROJECTILE_STOP (\d+)',reply);assert stop,reply[-1000:]
steps=step_log.collect();(out/'projectile-steps.json').write_text(json.dumps(steps,indent=2)+'\n')
result=dict(player=player,events=rows,flight_ended=int(stop[1])==sim+0x21f4a,last_step=steps['records'][-1]['step'])
(out/'projectiles.json').write_text(json.dumps(result,indent=2)+'\n')
print('PROJECTILE',len(rows),'events','player moves',sum(x['kind']=='move' and x['owner']==player for x in rows),'hit returns',sum(x['kind']=='result' and x['d0']!=0 for x in rows),flush=True)
