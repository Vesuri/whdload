import json,os,re,sys,subprocess
from pathlib import Path
from profile_window import command
p=Path(sys.argv[1]);m=json.loads((p/'anchor.json').read_text());a=m['data_base']+0x7ffe;sb=m['slave_base']
sym={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9a-fA-F]+)\s*$',(p/'slave.lst').read_text(encoding='latin1'),re.M)}
def rd(addr,typ='unsigned short'):
 s=command(f'gdb p /u *({typ}*){addr:#x}');return int(re.search(r'\$\d+ = (\d+)',s)[1])
def tap(k):command(f'gdb monitor key {k:x} 1\nmonitor fields 10\nmonitor key {k:x} 0\nmonitor fields 15')
assert rd(sb+sym['sim_time_field_hz'])==60
assert rd(sb+sym['sim_preferences_status'],'unsigned int')==5
assert rd(a-0x15fa)==rd(a-0xbc)==20
w=json.loads((p/'window.json').read_text());ticks=w['end']['sim_schedule_ticks']-w['start']['sim_schedule_ticks'];duration=w['emulated_seconds'];assert abs(ticks/duration/20-1)<.005,(ticks,duration)
opens=rd(sb+sym['sim_mode_opens'],'unsigned int')
command('gdb monitor key 4c 0\nmonitor key 63 1');tap(0x24);command('gdb monitor key 63 0\nmonitor fields 100')
assert rd(sb+sym['sim_mode_opens'],'unsigned int')==opens+1
command('shot '+str(p/'ntsc-dialog.png'))
# Initial selection is row one; marked A2500 row six is skipped.
for _ in range(5):tap(0x4d)
command('shot '+str(p/'ntsc-a4000-selected.png'))
tap(0x44);tap(0x45)
assert rd(a-0x15fa)==rd(a-0xbc)==20
command('shot '+str(p/'ntsc-menu.png'))
# Exit race into replay menu, then native Load of the tagged A4000 fixture.
if rd(a+0x45,'unsigned char')!=2:
 tap(0x45);command('gdb monitor fields 40')
assert rd(a-0x74c1,'unsigned char')==6
tap(0x44);command('gdb monitor fields 30')
for _ in range(3):tap(0x4d)
tap(0x44);command('gdb monitor fields 40');tap(0x4d);tap(0x44);command('gdb monitor fields 100')
command('shot '+str(p/'ntsc-load-result.png'))
status=rd(sb+sym['sim_replay_menu_status'],'unsigned int');assert status==4,status
assert rd(a-0x15fa)==20
command('shot '+str(p/'ntsc-replay-rejected.png'))
(p/'ntsc-check.json').write_text(json.dumps(dict(field_hz=60,saved50_status=5,active_rate=20,menu50_blocked=True,replay50_status=status,funded_steps_per_second=ticks/duration,slave_sha256=m['slave_sha256']),indent=2))
print('NTSC gating and native timing PASS')
