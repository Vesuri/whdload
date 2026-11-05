"""Exercise real Preferences with decoded-key register injection, not physical input."""
import json,re,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,'tools')
from presentation_state import symbol
p=Path(sys.argv[1]);m=json.loads((p/'entry.json').read_text());lines=(p/'slave.lst').read_text(encoding='latin-1').splitlines();from runtime_buffers import live_address
base=m['entry']['game_anchor']-symbol(lines,'tape_game_anchor');at=lambda n:live_address(lines,base,n,r.command);sim=m['entry']['sim'];h3=json.loads((p/'entry-steps.json').read_text())['h3'];state=at('time_loop_state')
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
 (p/'preferences-capture.json').write_text(json.dumps(dict(sha256=m['slave_sha256'],input='Existing CUSTOM5 bit-22 IRQ Pause/Escape fixture; real Pause loop, no host keyboard/CIA serial acquisition claim.',rows=rows),indent=2)+'\n')
# Keep the post-input record across every modal breakpoint.
bitmap=at('time_keys_bitmap')
args=[u(state+28),f'({u(state+20)}-{u(state+44)})',f'({u(sim+0x30006)}-{u(state+44)})',
      f'*(unsigned char*){bitmap+0x4e:#x}',f'*(unsigned char*){bitmap+0x40:#x}',
      '*(unsigned char*)($a5-6)','*(short*)($a5-14)','*(unsigned int*)($a5-4)',u(at('time_keys_popped'))]
commands=['delete','set $n=0',f'break *{sim+0x21d30:#x}','commands','silent',
          'printf "KEY %u %u %u %u %u %u %d %u %u\\n", '+', '.join(args),
          'set $n=$n+1','if $n < 80','continue','end','end']
r.command('gdb '+'\n'.join(commands))
keylog=[]
# The existing IRQ fixture supplies Pause/Escape through native keyboard stores.
def reach(target, label):
    raw=r.command(f'gdb break *{target:#x}\nset $stopbp=$bpnum\ncontinue\ndelete $stopbp\nprintf "STOP %u\\n", $pc')
    keylog.append(raw)
    (p/f'prefs-{label}-stop.log').write_text(raw)
    assert int(re.search(r'STOP (\d+)',raw)[1])==target,raw
reach(at('time_pause_wait'),'before')
snapshot('before')
reach(sim+0x21ac4,'entered')
snapshot('entered')
reach(at('time_pause_end'),'leaving')
snapshot('leaving')
reach(sim+0x21cec,'resumed')
snapshot('resumed')
reach(at('time_pose_captured'),'world')
snapshot('world')
print(rows,flush=True)

keylog.append(r.command('gdb continue\ndelete'))
(p/'keyboard.log').write_text('\n'.join(keylog))
for name,size,file in [('time_input_observe_queue',4112,'keyboard-queue.bin'),('time_input_fixture_log',64,'keyboard-acquisition.bin'),('time_keys_commands',516,'keyboard-commands.bin'),('time_keys_consumed',8,'keyboard-counters.bin'),('time_loop_state',60,'keyboard-clock.bin'),('time_input_fixture_clocks',128,'keyboard-acquisition-clocks.bin'),('time_input_fixture_epoch',4,'pause-epoch.bin'),('time_input_pause_epoch_ready',2,'pause-epoch-ready.bin')]:
    addr=at(name);r.command(f'gdb dump binary memory {p}/{file} {addr:#x} {addr+size:#x}')
import struct
from keyboard_replay import check_capture
observed=[list(map(int,x.split())) for x in re.findall(r'^KEY ([0-9 -]+)$','\n'.join(keylog),re.M)]
assert len(observed)==80,len(observed)
h=(p/'entry-h3.bin').read_bytes();center=struct.unpack_from('>h',h,0x1e30)[0];right=struct.unpack_from('>h',h,0x1e40)[0]
excluded=struct.unpack_from('>I',(p/'keyboard-clock.bin').read_bytes(),44)[0]
result=check_capture((p/'keyboard-queue.bin').read_bytes(),(p/'keyboard-acquisition.bin').read_bytes(),observed,excluded,center,right,(p/'keyboard-commands.bin').read_bytes(),(p/'keyboard-counters.bin').read_bytes(),clocks=(p/'keyboard-acquisition-clocks.bin').read_bytes(),modal_key=0x19)
assert (p/'pause-epoch-ready.bin').read_bytes()==b'\x00\x01'
clocks=(p/'keyboard-acquisition-clocks.bin').read_bytes()
assert all(struct.unpack_from('>I',clocks,i*16)[0]==1 for i in range(6))
result.update(sha256=m['slave_sha256'],excluded_cia_ticks=excluded)
(p/'keyboard-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(result,flush=True)
