"""Exercise real Preferences with decoded-key register injection, not physical input."""
import json,re,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,'tools')
from presentation_state import symbol
p=Path(sys.argv[1]);m=json.loads((p/'entry.json').read_text());lines=(p/'slave.lst').read_text(encoding='latin-1').splitlines();base=m['entry']['game_anchor']-symbol(lines,'tape_game_anchor');at=lambda n:base+symbol(lines,n);sim=m['entry']['sim'];h3=json.loads((p/'entry-steps.json').read_text())['h3'];state=at('time_loop_state')
def u(a):return f'*(unsigned int*){a:#x}'
def w(a):return f'*(unsigned short*){a:#x}'
rows=[]
def snapshot(label):
 fields=[u(sim+0x30006),u(at('pace_state')),u(at('time_pose_header')+4),w(h3+0x4834),u(h3+0x4578)]
 raw=r.command('gdb printf "STATE %u %u %u %u %u\\n", '+', '.join(fields));(p/f'prefs-{label}.log').write_text(raw)
 values=list(map(int,re.search(r'STATE ([0-9 ]+)',raw)[1].split()))
 r.command(f'gdb dump binary memory {p}/prefs-{label}-clock.bin {state:#x} {state+60:#x}')
 player=values[-1];r.command(f'gdb dump binary memory {p}/prefs-{label}-player.bin {player:#x} {player+0x118:#x}')
 rows.append(dict(label=label,cia=values[0],field=values[1],completed=values[2],dt=values[3],player=player))
 (p/'preferences-capture.json').write_text(json.dumps(dict(sha256=m['slave_sha256'],input='Decoded Pause command at world input return and nonzero native wait result; real pause loop, no physical input claim.',rows=rows),indent=2)+'\n')
# The existing IRQ fixture supplies F10/Escape through native keyboard stores.
def reach(target, label, condition=""):
    raw=r.command(f'gdb delete\nbreak *{target:#x}{condition}\ncontinue\ndelete\nprintf "STOP %u\\n", $pc')
    (p/f'prefs-{label}-stop.log').write_text(raw)
    assert int(re.search(r'STOP (\d+)',raw)[1])==target,raw
reach(sim+0x1ee82,'world-input', f' if {w(at("time_camera_sampling"))} == 0')
r.command('gdb set $d0=0x19')
reach(at('time_pause_wait'),'before')
snapshot('before')
reach(sim+0x21ac4,'entered')
snapshot('entered')
start=rows[-1]['cia']
raw=r.command(f'gdb delete\nbreak *{sim+0x21aec:#x} if (unsigned int)({u(sim+0x30006)} - {start}) >= 180\ncontinue\ndelete\nprintf "STOP %u\\n", $pc')
(p/'pause-wait.log').write_text(raw)
assert int(re.search(r'STOP (\d+)',raw)[1])==sim+0x21aec,raw
r.command('gdb set $d0=1')
reach(at('time_pause_end'),'leaving')
snapshot('leaving')
reach(sim+0x21cec,'resumed')
snapshot('resumed')
reach(at('time_pose_captured'),'world')
snapshot('world')
print(rows,flush=True)
