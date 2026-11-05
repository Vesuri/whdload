"""Retain 250 traced PAL fields plus exact live W6 boundary accounting."""
import argparse,json,re,subprocess,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path('tools').resolve()))
from presentation_state import symbol
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--start-current',action='store_true');p.add_argument('--prefix',default='capacity');a=p.parse_args()
m=json.loads((a.capture/'entry.json').read_text());lines=(a.capture/'slave.lst').read_text(encoding='latin-1').splitlines();base=m['entry']['game_anchor']-symbol(lines,'tape_game_anchor');at=lambda n:base+symbol(lines,n);state=at('time_loop_state');sim=m['entry']['sim']
fields=[('transaction','short',at('time_loop_transaction')),('pc',None,None),('field','long',at('pace_state')),('cia','long',sim+0x30006),('mask','long',at('perf_mask')),('active','long',state+40),('cursor','long',state+20),('due','short',state+24),('started','long',state+28),('completed','long',at('time_pose_header')+4),('draws','long',state+36),('paused','long',state+44),('divisor','short',at('time_rate_queue')+8)]+[(f'phase{i}','long',state+i*4) for i in range(4)]
settlements=[]
def raw_snapshot():
 fmt='CAP '+' '.join(['%u']*len(fields))+'\\n';args=', '.join('$pc' if typ is None else f'*(unsigned {typ}*){addr:#x}' for _,typ,addr in fields)
 raw=r.command(f'gdb maintenance flush register-cache\nprintf "{fmt}", {args}')
 line=next(x for x in raw.splitlines() if x.startswith('CAP '));return dict(zip([x[0] for x in fields],map(int,line.split()[1:])))
def snap():
 raw=raw_snapshot()
 transaction=raw['transaction']
 if not transaction:return raw
 if transaction not in (1,2):raise ValueError('Unknown clock transaction')
 label={1:'time_loop_credit_committed',2:'time_loop_world_committed'}[transaction]
 r.command(f'gdb delete\nbreak *{at(label):#x}\ncontinue\ndelete')
 settled=raw_snapshot()
 if settled['transaction'] or settled['pc']!=at(label):
  raise ValueError('Clock transaction did not reach its commit boundary')
 settlements.append(dict(transaction=transaction,raw=raw,settled=settled))
 return settled

if not a.start_current:
 r.command(f'gdb delete\nbreak *{at("time_render_restored"):#x}\nbreak *{at("time_exp_bad"):#x}\ncontinue\ndelete')
 reached=raw_snapshot()
 if reached['pc']!=at('time_render_restored'):
  raise ValueError(f"Did not reach completed-render boundary: {reached}")
chunks=[]
for i,n in enumerate((100,100,50)):
 before=snap();out=a.capture/f'{a.prefix}-{i}'
 subprocess.run([sys.executable,'tools/capture_current.py','--out',str(out),'--fields',str(n)],check=True)
 after=snap();chunks.append(dict(recorded_fields=n,path=out.name,before=before,after=after))
 (a.capture/f'{a.prefix}.json').write_text(json.dumps(dict(sha256=m['slave_sha256'],whd_args=m['whd_args'],chunks=chunks,settlements=settlements),indent=2)+'\n')
 print('Capacity chunk',i,'fields',n,'completed',after['completed']-before['completed'],'draws',after['draws']-before['draws'],flush=True)
