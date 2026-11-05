import sys,json,struct
from session_a import Session
from route import run
from flight_profile import ROUTE
from verify_run import marker
s=Session(sys.argv[1])
try:
 run(s,ROUTE);M=marker(s.read(0x200000,0x800000));c=M['hunks'][0];d=M['hunks'][6]
 s.cmd(f"break *{M['checkpoint']:#x}");s.cmd(f'condition $bpnum *(unsigned short*){d+0x3b94:#x} >= 104');s.cmd('continue');s.cmd('delete')
 s.cmd(f'break *{c+0xa494:#x}')
 rows=[]
 for i in range(24):
  s.cmd('continue',timeout=120)
  def w(o):return int.from_bytes(s.read(c+o,2),'big',signed=True)
  rows.append(dict(tick=int.from_bytes(s.read(d+0x3b94,2),'big'),object=w(0x6ac6),cell=w(0x5b00),shape=w(0x6ac8),screen_x=w(0x76e2),screen_y=w(0x770c)))
 (s.out/'visible-targets.json').write_text(json.dumps(rows,indent=2));print(rows,flush=True)
 s.cmd('delete');s.shot('scene.png')
finally:s.quit()
