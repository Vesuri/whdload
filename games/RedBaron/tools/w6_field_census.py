"""Read-only, exact-field W6 census with raw RAM snapshots and publication events."""
import argparse,json,re,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path('tools').resolve()))
from presentation_state import symbol
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--windows',type=int,default=2);a=p.parse_args()
m=json.loads((a.capture/'entry.json').read_text());lines=(a.capture/'slave.lst').read_text(encoding='latin-1').splitlines();base=m['entry']['game_anchor']-symbol(lines,'tape_game_anchor');at=lambda n:base+symbol(lines,n);state=at('time_loop_state');sim=m['entry']['sim']
fields=[('transaction','short',at('time_loop_transaction')),('field','long',at('pace_state')),('cia','long',sim+0x30006),('mask','long',at('perf_mask')),('active','long',state+40),('cursor','long',state+20),('due','short',state+24),('started','long',state+28),('completed','long',at('time_pose_header')+4),('draws','long',state+36),('paused','long',state+44),('divisor','short',at('time_rate_queue')+8)]+[(f'phase{i}','long',state+i*4) for i in range(4)]
def snap(name):
 fmt='CAP '+' '.join(['%u']*len(fields))+'\\n';args=', '.join(f'*(unsigned {typ}*){addr:#x}' for _,typ,addr in fields)
 raw=r.command(f'gdb printf "{fmt}", {args}');line=next(x for x in raw.splitlines() if x.startswith('CAP '));values=dict(zip([x[0] for x in fields],map(int,line.split()[1:])))
 for lo,hi in r.memory_regions():r.command(f'gdb dump binary memory {a.capture}/{name}-{lo:x}.bin {lo:#x} {hi:#x}')
 return values
r.command(f'gdb delete\nbreak *{at("time_render_restored"):#x}\ncontinue\ndelete\nbreak *{at("pace_vbl"):#x}\ncontinue\ndelete')
windows=[]
for i in range(a.windows):
 before=snap(f'census-{i}-before')
 cmd=['delete',f'break *{sim+0x3154a:#x}','commands','silent',f'printf "PUB %u %u\\n", *(unsigned long*){at("pace_state"):#x}, *(unsigned long*)0xdff004','continue','end']
 for off,label in [(0x3c06,'MESSAGE'),(0x3c7c,'SHORTEN'),(0x11c8,'WORLD_BODY_DONE')]:
  cmd += [f'break *{sim+off:#x}','commands','silent',f'printf "{label}\\n"','continue','end']
 cmd += [f'break *{at("pace_vbl"):#x}','ignore $bpnum 249','continue','delete']
 raw=r.command('gdb '+'\n'.join(cmd));(a.capture/f'census-{i}.log').write_text(raw)
 after=snap(f'census-{i}-after');assert (after['field']-before['field'])&0xffffffff==250
 swaps=[dict(field=int(x),beam=int(y)) for x,y in re.findall(r'^PUB (\d+) (\d+)$',raw,re.M)]
 events={label:len(re.findall('^'+label+'$',raw,re.M)) for label in ['MESSAGE','SHORTEN','WORLD_BODY_DONE']}
 windows.append(dict(before=before,after=after,publications=swaps,events=events))
 (a.capture/'field-census.json').write_text(json.dumps(dict(sha256=m['slave_sha256'],whd_args=m['whd_args'],windows=windows),indent=2)+'\n')
 print('Window',i,'fields',250,'completed world ticks',after['completed']-before['completed'],'publications',len(swaps),'events',events,flush=True)
