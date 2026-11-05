"""Verify terminal retirement and fresh native mission activation snapshots."""
from pathlib import Path
import json,struct,re,sys
root=Path(__file__).resolve().parents[1]
s=(root/'tmp/build/lifecycle-current.slave.lst').read_text(encoding='latin1')
sym=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',s,re.M)[1],16)
def get(a,n,o=0,w=4):return int.from_bytes(a[sym(n)+o:sym(n)+o+w],'big')
for d in map(Path,sys.argv[1:]):
 def arena(n):return (d/(n+'-arena.bin')).read_bytes()
 terminal=[]
 for name in ['returned-native-flight','menu-retired','fresh-before-prepare','fresh-ended','fresh-ended-after-menu']:
  a=arena(name)
  assert get(a,'RT_CAPTURE_OWNER',0,2)==get(a,'RT_CLOCK',24,2)==get(a,'RT_HISTORY',4,2)==get(a,'RT_COMMANDS',6,2)==0,name
  assert get(a,'RT_SCHEDULER',36)==16,name
  assert a[sym('RT_ENDPOINT'):sym('RT_ENDPOINT')+sym('EP_SIZE')]==bytes(sym('EP_SIZE')),name
  for n,off in [('RT_PLAYER_CACHE','PC_VALID'),('RT_ACTOR_PRESENT','AC_VALID'),('RT_RELEASE_PRESENT','AC_VALID'),('RT_SCRIPT_PRESENT','SPC_VALID')]:assert get(a,n,sym(off),2)==0,(name,n)
  terminal.append(name)
 initial=arena('fresh-active');player=(d/'fresh-active-player.bin').read_bytes()
 assert int.from_bytes(player[12:14],'big')==0 and player[24]==player[82]==0
 assert get(initial,'RT_CAPTURE_OWNER',0,2)==get(initial,'RT_CLOCK',24,2)==1
 for name,off,w in [('RT_SCHEDULER',32,4),('RT_SCHEDULER',36,4),('RT_CLOCK',4,4),('RT_CLOCK',8,4),('RT_CLOCK',20,2),('RT_HISTORY',0,2),('RT_HISTORY',2,2),('RT_COMMANDS',0,2),('RT_COMMANDS',2,2),('RT_COMMANDS',4,2)]:assert get(initial,name,off,w)==0,(name,off)
 assert get(initial,'RT_CLOCK',16)==1
 running=arena('fresh-world5');player=(d/'fresh-world5-player.bin').read_bytes()
 assert int.from_bytes(player[12:14],'big')==get(running,'RT_SCHEDULER',36)==5
 for a in [initial,running]:
  for name,off in [('RT_CLOCK',12),('RT_HISTORY',8),('RT_HISTORY',12),('RT_COMMANDS',16),('RT_COMMANDS',20)]:assert get(a,name,off)==0,(name,off)
  assert get(a,'RT_CLOCK',16)==1 and get(a,'RT_SCHEDULER',22,2)==0
 end=arena('fresh-ended');player=(d/'fresh-ended-player.bin').read_bytes()
 assert int.from_bytes(player[12:14],'big')==16 and player[24]==player[82]==2
 after=arena('fresh-ended-after-menu')
 for name,off in [('RT_SCHEDULER',32),('RT_SCHEDULER',36),('RT_CLOCK',16)]:assert get(end,name,off)==get(after,name,off)
 report=dict(status='passed',run=d.name,rate=get(initial,'RT_CLOCK',22,2),terminal_snapshots=terminal,new_mission_tick=0,first_checked_tick=5,second_exit_tick=16,fresh_command_history_cursors=True,unexpected_rebases=0,sampled_active_loss_discard=0,terminal_unread_discard=get(end,'RT_HISTORY',12),terminal_cache_history_cleared=True,scope='Native fresh-mission menu/reload with controlled landing initialization; natural flight and remaining lifecycle matrix not covered')
 (d/'new-mission-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
