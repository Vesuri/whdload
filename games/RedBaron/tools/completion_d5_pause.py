"""Exercise player commands through real keyboard IRQs, never state injection."""
import json,re,subprocess,sys
from pathlib import Path
import route_status as r
out=Path(sys.argv[1]);m=json.loads((out/'runtime.json').read_text());sim,h3=m['sim'],m['h3']
tools=Path('tools');rows=[]
def value(expr):
 raw=r.command('gdb p/u '+expr);return int(raw.split('=')[1])
def irq(raw,up=False):
 subprocess.run([sys.executable,'-B',str(tools/'completion_host_input.py'),f'irq-{"up" if up else "down"}:{sim},{0x30f8c},{raw}'],check=True)
def read_throttle():return value(f'*(unsigned short*)(*(unsigned int*){h3+0x457c:#x}+6)')
# Real Pause excludes modal wall time and resumes with the CPU's quantum.
listing=(out/'slave.lst').read_text(encoding='latin1')
syms={match[1]:int(match[2],16) for line in listing.splitlines() if (match:=re.match(r'^(\w+)\s+00:([0-9a-fA-F]+)\s*$',line))}
state=m['slave']+syms['time_loop_state']
def snap():
 return dict(cia=value(f'*(unsigned int*){sim+0x30006:#x}'),
  cursor=value(f'*(unsigned int*){state+20:#x}'),steps=value(f'*(unsigned int*){state+28:#x}'),
  active=value(f'*(unsigned int*){state+40:#x}'),paused=value(f'*(unsigned int*){state+44:#x}'),
  dt=value(f'*(unsigned short*){h3+0x4834:#x}'))
irq(0x19);r.command(f'until {sim+0x21ac4:#x}');irq(0x19,True);before=snap()
assert before['active']==0
r.command(f'gdb delete\nbreak *{sim+0x2d34e:#x}\nignore $bpnum 199\ncontinue\ndelete')
held=snap();assert held['steps']==before['steps'] and held['cursor']==before['cursor']
irq(0x44);r.command(f'until {sim+0x21cec:#x}');irq(0x44,True);after=snap()
assert after['active']==1 and after['steps']==before['steps']
assert after['cursor']-before['cursor']==after['paused']-before['paused']
assert after['dt']==json.loads((out/'rate.json').read_text())['quantum']
(out/'pause.json').write_text(json.dumps(dict(before=before,held=held,after=after),indent=2)+'\n')
print('PAUSE/RESUME PASS',flush=True)
