"""Bounded intro event probe; no raw CPU traces or guest-state modifications."""
import os,sys,json,re,collections,struct,hashlib
from pathlib import Path
from gpc import server,ROOT
from gpc_report import regions
root=Path(ROOT); out=root/'tmp/audio040'/sys.argv[1];out.mkdir(exist_ok=True)
server.profile_window=False
g=server.boot();base=int(os.environ.get("DUMP_BASE","0x880000"),0);size=0x180000
original=(root/'tmp/game/GrandPrixCircuit_v1.0_0008/GrandPrixCircuit/data/song1').read_bytes()[40:40+0xb80]
try:
 for i in range(180):
  r=g.cmd('monitor fields 20',timeout=60)
  if 'Protocol error' in r:raise RuntimeError(r)
  r=g.cmd(f'dump binary memory tmp/audio040/{sys.argv[1]}/memory.bin {base:#x} {base+size:#x}')
  if i==0 and r:print('DUMP',r,flush=True)
  if not (out/'memory.bin').exists():continue
  data=(out/'memory.bin').read_bytes();votes=collections.Counter()
  for off in range(0,len(original)-16,64):
   pos=data.find(original[off:off+16])
   while pos>=0:votes[pos-off]+=1;pos=data.find(original[off:off+16],pos+1)
  c=[p for p,n in votes.items() if n>=8 and p>=8 and data[p-8:p-4]==bytes.fromhex('00000b88')]
  if len(c)==1 and data[c[0]+0x86a:c[0]+0x86c]==bytes.fromhex('4eb9'):break
 else:raise RuntimeError('song not found')
 song=base+c[0]; rr={n:lo for lo,hi,n,o in regions(data,base)};h=rr['gpc'];a4=rr['gpc-data']+0x7ffe
 print('song',hex(song),'game',hex(h),flush=True)
 cmd=['set pagination off','set $events=0','set $stopped=0','set $notes=0',f'set $limit=*(unsigned int*){a4-31790:#x}+600',f'break *{song+0x8c6:#x}', 'commands','silent','if ($d0 & $d3 & 0x780) != 0','set $events=$events+1','if (*(unsigned short*)0xdff002 & $d2) == 0','set $stopped=$stopped+1','if $stopped <= 12', 'printf "STOPPED %u %x %x %d\\n", $events, $d2, *(unsigned short*)0xdff01c, *(short*)($a0+18)','end','end','end','continue','end',f'break *{song+0x7e0:#x}','commands','silent','set $notes=$notes+1','printf "NOTE %u %x %d %d %d\\n", $notes, $a3, *(short*)($a3+18), *(unsigned short*)($a3+32), *(unsigned short*)($a3+30)','continue','end',f'break *{h+0x7734:#x}',f'condition $bpnum *(unsigned int*){a4-31790:#x} >= $limit || $events >= 10000','continue']
 log=g.cmd('\n'.join(cmd),timeout=600);(out/'events.txt').write_text(log)
 stats=g.cmd('printf "RESULT %u %u %u\\n", $events, $stopped, $notes');(out/'counts.txt').write_text(stats);print(stats,flush=True)
 if os.environ.get('SMOKE'):
  g.cmd('delete')
  for label,off in [('title',0x4d94),('race',0x7094),('draw',0x39e)]:
   r=g.cmd(f'break *{h+off:#x}\ncontinue',timeout=600)
   assert f'{h+off:x}' in g.cmd('p/x $pc'),r
   g.cmd('delete');print(label,'PASS',flush=True)
   server.handle(g,f'shot {out}/{label}.png')
 print(g.cmd('delete\ninfo all-registers'),file=(out/'registers.txt').open('w'))
 (out/'metadata.json').write_text(json.dumps(dict(song=song,game=h,a4=a4,slave_sha256=hashlib.sha256(Path(os.environ['SLAVE']).read_bytes()).hexdigest(),extra_args=os.environ.get('EXTRA_ARGS')),indent=2)+'\n')
finally:
 server.handle(g,f'shot {out}/last.png')
 (out/'last-registers.txt').write_text(g.cmd('info all-registers'))
 server.handle(g,'quit')
