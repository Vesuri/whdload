"""Read-only cap/wrap probe for the compiled VERIFY fast-draw fixture."""
import json,re,threading,signal,os,sys
from pathlib import Path
import route_status as r,step_log
out=Path(sys.argv[1]);m=json.loads((out/'entry.json').read_text());sim=m['entry']['sim']
listing=(out/'slave.lst').read_text(encoding='latin1')
def label(n): return int(re.search(r'^'+n+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16)
base=m['entry']['game_anchor']-label('tape_game_anchor');counter=base+label('pace_state');obs,h=step_log.header();state=r.read(r.locate())
cmd=[f'break *{sim+0x3154a:#x}','commands','silent',f'printf "PACE %u %u %u %u\\n", *(unsigned long *){counter:#x}, *(unsigned long *){obs+36:#x}, *(unsigned long *)0xdff004, *(unsigned long *){sim+0x30006:#x}','continue','end',f'break *{state["game_anchor"]:#x}','ignore $bpnum 39','continue','delete']
pid=int(Path('tmp/run/default/.run/gdb.pid').read_text());timer=threading.Timer(55,lambda:os.kill(pid,signal.SIGINT));timer.start()
try: reply=r.command('gdb '+'\n'.join(cmd))
finally: timer.cancel()
(out/'stress-log.txt').write_text(reply)
rows=[dict(counter=int(c),vbl=int(v),beam=int(b),ticks=int(t)) for c,v,b,t in re.findall(r'PACE (\d+) (\d+) (\d+) (\d+)',reply)]
assert len(rows)==40,reply
intervals=[b['vbl']-a['vbl'] for a,b in zip(rows,rows[1:])]
assert min(intervals)>=2 and intervals.count(2)>=30,intervals
for a,b in zip(rows,rows[1:]): assert ((b['counter']-a['counter'])&0xffffffff)==b['vbl']-a['vbl']
assert any(a['counter']>b['counter'] for a,b in zip(rows,rows[1:]))
lines=[(x['beam']>>8)&511 for x in rows];assert all(n<=40 or n>244 for n in lines),lines
result=dict(rows=rows,interval_fields=intervals,lines=lines,scope='Compiled VERIFY fast-frame fixture: skipped 3D and forced counter wrap, not game performance')
(out/'stress.json').write_text(json.dumps(result,indent=2)+'\n');print(dict(swaps=len(rows),interval_fields=intervals,lines=lines))
