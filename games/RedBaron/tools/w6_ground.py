import json,re,sys
from pathlib import Path
import route_status as r,step_log
out=Path(sys.argv[1]);at=r.locate();st=r.read(at);obs,h=step_log.header();sim,h3=st['sim'],h[5]
raw=r.command(f'gdb x/wx {h3+0x4578:#x}');player=int(re.findall(r':\s*(0x[0-9a-f]+)',raw)[0],16)
cmd=[]
for name,off,reg in [('ground',0x1926a,'$a0'),('impact',0x193a2,'*(unsigned long *)($a5+16)')]:
 cmd += [f'break *{sim+off:#x}',f'condition $bpnum {reg} == {player:#x}','commands','silent',f'printf "GROUND {name} %u %u %d %d %u\\n", *(unsigned long *){at+44:#x}, *(unsigned long *){obs+36:#x}, *(int *)({player:#x}+16), *(short *)({player:#x}+254), *(unsigned char *)({player:#x}+266)','continue','end']
cmd += [f'break *{sim+0x21f4a:#x}',f'break *{st["game_anchor"]:#x}','ignore $bpnum 9','continue','printf "GROUND_STOP %u\\n", $pc','delete']
reply=r.command('gdb '+'\n'.join(cmd));(out/'ground-log.txt').write_text(reply)
steps=step_log.collect();(out/'ground-steps.json').write_text(json.dumps(steps,indent=2)+'\n')
r.command(f'gdb dump binary memory {out}/ground-end-player.bin {player:#x} {player+0x118:#x}')
rows=re.findall(r'GROUND (ground|impact) (\d+) (\d+) (-?\d+) (-?\d+) (\d+)',reply)
stop=re.search(r'GROUND_STOP (\d+)',reply)
assert stop,reply[-1000:]
result=dict(events=rows,flight_ended=int(stop[1])==sim+0x21f4a,last_step=steps['records'][-1]['step'],fixture='Synthetic low-altitude descent; no timing/pixel claim')
(out/'ground-result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
