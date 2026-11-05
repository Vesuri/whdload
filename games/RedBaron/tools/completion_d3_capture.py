import sys,subprocess,re,json
from pathlib import Path
sys.path.insert(0,'tools');from completion_machines import environment
sys.path.insert(0,'tools');import route_status as r,step_log
env=environment('a500',0x32000);env.update(CHIP_KB='1024',FAST_KB='2048',BOOT_TIMEOUT='240',GAME_DIR='completion-benchmark/RedBaron')
env['EXTRA_ARGS']=env['EXTRA_ARGS'].replace('--slow_memory=1536','--slow_memory=0')
env['WHD_ARGS']='CUSTOM2=204800 CUSTOM5=1049088'
out=Path('tmp/prof/completion-d3-a500')
subprocess.run([sys.executable,'-B','tools/reach_flight.py','--no-shot','--out',str(out)],env=env,check=True)
symbols={m[1]:int(m[2],16) for line in (out/'slave.lst').read_text(encoding='latin1').splitlines() if (m:=re.match(r'^(\w+)\s+00:([0-9A-Fa-f]+)\s*$',line))}
state=r.read(r.locate());base=state['game_anchor']-symbols['tape_game_anchor'];cmd=['delete']
for name,sym in [('poses','time_pose_capture'),('blend','time_pose_blend'),('draw','time_render_after_draw')]:
 cmd += [f'set $rb_{name}=0',f'break *{base+symbols[sym]:#x}','commands','silent',f'set $rb_{name}=$rb_{name}+1','continue','end']
cmd += [f'break *{state["game_anchor"]:#x}','ignore $bpnum 18','continue','printf "D3_COUNTS %u %u %u\\n", $rb_poses, $rb_blend, $rb_draw','delete']
raw=r.command('gdb '+'\n'.join(cmd));(out/'counts.log').write_text(raw);print(raw,flush=True)
m=re.search(r'D3_COUNTS (\d+) (\d+) (\d+)',raw);assert m and int(m[1])==0 and int(m[2])==0 and int(m[3])>0
(out/'steps.json').write_text(json.dumps(step_log.collect(),indent=2)+'\n')
print(r.command('quit'),flush=True)
print('D3 NATIVE BYPASS PASSED',flush=True)
