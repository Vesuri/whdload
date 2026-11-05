"""Read-only publication/clock trace; optional compiled fast-draw fixture."""
import argparse,json,re,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path('tools').resolve()))
from presentation_state import symbol
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--count',type=int,default=40);a=p.parse_args()
m=json.loads((a.capture/'entry.json').read_text());lines=(a.capture/'slave.lst').read_text(encoding='latin-1').splitlines();base=m['entry']['game_anchor']-symbol(lines,'tape_game_anchor');at=lambda n:base+symbol(lines,n);sim=m['entry']['sim'];state=at('time_loop_state')
fields=[('field','long',at('pace_state')),('beam','long',0xdff004),('cia','long',sim+0x30006),('mask','long',at('perf_mask')),('active','long',state+40),('cursor','long',state+20),('due','short',state+24),('steps','long',state+28),('draws','long',state+36),('divisor','short',at('time_rate_queue')+8)]+[(f'phase{i}','long',state+i*4) for i in range(4)]
fmt='PUB '+' '.join(['%u']*len(fields))+'\\n';args=', '.join(f'*(unsigned {typ}*){addr:#x}' for _,typ,addr in fields)
cmd=['delete','set $pub_count=0',f'break *{sim+0x3154a:#x}','commands','silent',f'printf "{fmt}", {args}','set $pub_count=$pub_count+1',f'if $pub_count < {a.count}','continue','end','end','continue','delete']
raw=r.command('gdb '+'\n'.join(cmd));(a.capture/'publication-log.txt').write_text(raw)
rows=[dict(zip([x[0] for x in fields],map(int,line.split()[1:]))) for line in raw.splitlines() if line.startswith('PUB ')]
assert len(rows)==a.count,(len(rows),raw[-1000:])
result=dict(sha256=m['slave_sha256'],whd_args=m['whd_args'],rows=rows)
(a.capture/'publication.json').write_text(json.dumps(result,indent=2)+'\n');print('Captured publications:',len(rows),flush=True)
