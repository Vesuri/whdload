"""VERIFY-only fast-frame cap probe; skip 3D drawing, force counter wrap.
This deliberately altered workload is not a game-performance measurement.
"""
import json,re,struct,threading,signal,os
from pathlib import Path
import route_status as r,step_log
out=Path('tmp/prof/w5-030-768-probe');m=json.loads((out/'entry.json').read_text());sim=m['entry']['sim']
listing=(out/'slave.lst').read_text(encoding='latin1')
def label(n): return int(re.search(r'^'+n+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16)
base=m['entry']['game_anchor']-label('tape_game_anchor');counter=base+label('pace_state');obs,h=step_log.header();state=r.read(r.locate())
r.command(f'gdb dump binary memory {out}/stress-original.bin {sim+0x15b2:#x} {sim+0x15b8:#x}')
raw=(out/'stress-original.bin').read_bytes();assert raw[:2]==bytes.fromhex('4ef9')
r.command(f'gdb dump binary memory {out}/stress-counter.bin {counter:#x} {counter+10:#x}')
old=(out/'stress-counter.bin').read_bytes();now,last,valid=struct.unpack('>IIH',old);shift=(0xfffffffa-now)&0xffffffff
cmd=[f'set {{unsigned short}}{sim+0x15b2:#x}=0x4e75',f'set {{unsigned long}}{counter:#x}=0xfffffffa',f'set {{unsigned long}}{counter+4:#x}={(last+shift)&0xffffffff}',f'break *{sim+0x3154a:#x}','commands','silent',f'printf "PACE %u %u %u %u\\n", *(unsigned long *){counter:#x}, *(unsigned long *){obs+36:#x}, *(unsigned long *)0xdff004, *(unsigned long *){sim+0x30006:#x}','continue','end',f'break *{state["game_anchor"]:#x}','ignore $bpnum 39','continue','delete']
pid=int(Path('tmp/run/default/.run/gdb.pid').read_text());timer=threading.Timer(55,lambda:os.kill(pid,signal.SIGINT));timer.start()
try:reply=r.command('gdb '+'\n'.join(cmd))
finally:
 timer.cancel();r.command(f'gdb set {{unsigned short}}{sim+0x15b2:#x}=0x4ef9')
(out/'stress-log.txt').write_text(reply)
rows=[dict(counter=int(c),vbl=int(v),beam=int(b),ticks=int(t)) for c,v,b,t in re.findall(r'PACE (\d+) (\d+) (\d+) (\d+)',reply)]
assert len(rows)==40,reply
for a,b in zip(rows,rows[1:]):
 assert ((b['counter']-a['counter'])&0xffffffff)==b['vbl']-a['vbl']
 assert b['vbl']-a['vbl']>=2
assert any(a['counter']>b['counter'] for a,b in zip(rows,rows[1:]))
result=dict(rows=rows,interval_fields=[b['vbl']-a['vbl'] for a,b in zip(rows,rows[1:])],lines=[(x['beam']>>8)&511 for x in rows],scope='VERIFY runtime fast-frame fixture: skipped 3D and forced counter wrap, not game performance')
(out/'stress.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
