"""Observe automatic menu service cadence and completed-world ownership."""
import argparse,json,re,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path('tools').resolve()))
from presentation_state import symbol
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--services',type=int,default=120);a=p.parse_args()
m=json.loads((a.capture/'entry.json').read_text());lines=(a.capture/'slave.lst').read_text(encoding='latin-1').splitlines();base=m['entry']['game_anchor']-symbol(lines,'tape_game_anchor');at=lambda n:base+symbol(lines,n);h3=json.loads((a.capture/'entry-steps.json').read_text())['h3'];state=at('time_loop_state')
fields=[('calls','long',at('time_auto_calls')),('cursor','long',state+20),('services','short',state+26),('started','long',state+28),('completed','long',at('time_pose_header')+4),('paused','long',state+44),('timer','short',h3+0x783e),('entered','short',h3+0x7838),('completion','short',h3+0x783a),('secondary','short',h3+0x4836),('exit','short',at('time_auto_exit')),('sampling','short',at('time_auto_sampling'))]
fmt='AUTO '+' '.join(['%u']*len(fields))+' %u\\n';args=', '.join(f'*(unsigned {typ}*){address:#x}' for _,typ,address in fields)+', $d0'
cmd=['delete','set $auto_seen=0',f'break *{m["entry"]["sim"]+0x21b74:#x}','commands','silent','printf "COUNTDOWN %u\\n", $d0','continue','end',f'break *{at("time_auto_observe"):#x}','commands','silent',f'printf "{fmt}", {args}','set $auto_seen=$auto_seen+1',f'if $auto_seen < {a.services}','continue','end','end','continue','delete']
raw=r.command('gdb '+'\n'.join(cmd));(a.capture/'auto-log.txt').write_text(raw)
rows=[dict(zip([x[0] for x in fields]+['result'],map(int,line.split()[1:]))) for line in raw.splitlines() if line.startswith('AUTO ')]
assert len(rows)==a.services,(len(rows),raw[-1000:]);assert all(x['started']==x['completed'] and x['sampling']==0 and x['result']==4 and x['exit']==0 for x in rows)
for x,y in zip(rows,rows[1:]):
 assert y['calls']==x['calls']+1 and (y['services']-x['services'])&65535==1
 assert (y['cursor']-x['cursor']-(y['paused']-x['paused']))&0xffffffff in (2,3)
amounts=list(map(int,re.findall(r'^COUNTDOWN (\d+)$',raw,re.M)));assert all(x==128 for x in amounts)
result=dict(sha256=m['slave_sha256'],rows=rows,countdown_amounts=amounts,limitation='Observed native service calls; expiry/menu choices require separate coverage.')
(a.capture/'auto-result.json').write_text(json.dumps(result,indent=2)+'\n');print(dict(services=len(rows),countdown_calls=len(amounts),timer_range=[min(x['timer'] for x in rows),max(x['timer'] for x in rows)],started_range=[rows[0]['started'],rows[-1]['started']],passed=True))
