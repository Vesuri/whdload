from pathlib import Path
import json
r=Path(__file__).resolve().parents[1];items=json.loads((r/'tools/step5-c4-q03-modal-replay.json').read_text())
# All menu navigation and native session-clock assertions are unchanged.
# Production activates immediately, so install the first-update breakpoint
# before entering the cockpit; the old fixture waited 125 native iterations.
last=next(i for i,x in enumerate(items) if x.get('op')=='move' and x.get('x')==115 and x.get('y')==83)
items=items[:last+1]+[{'op':'exec','code':'''cmd('delete')
cmd(f'break *{probe+sym(fine_listing,"C1Checkpoint")}')
cmd('monitor input JOY1_FIRE_BUTTON 1')
assert 'Breakpoint' in cmd('continue')
cmd('monitor input JOY1_FIRE_BUTTON 0')
assert val('$pc')==probe+sym(fine_listing,'C1Checkpoint')
m,fresh=snapshot('fresh-session-update')
f=fresh['context'];interval=20 if fine else 200 if kind=='000' else 100
assert fresh['completed']==1 and f[6]==1 and f[7]==interval and f[8:]==[0,0,0,0,0,0]
assert (f[3]<<32|f[4])==f[5]
if kind=='000':assert fresh['owned']==64 and not fresh['intena']&64
report['fresh_epoch_after_actual_session_change']=True
cmd('ignore $bpnum 19');assert 'Breakpoint' in cmd('continue')
m,settled=snapshot('fresh-session-step21');assert settled['completed']==21 and val(f'*(unsigned int*){probe+sym(fine_listing,"error")}')==0
report['fresh_race']=hex(struct.unpack_from('>I',m,table+160*4)[0]*4+4)
report['status']='passed';save()
cmd('delete');s.handle(g,'shot '+str(out/'fresh-session-driving.png'))
'''},{'op':'quit'}]
(r/'tools/production-modal-replay.json').write_text(json.dumps(items,indent=2)+'\n')
