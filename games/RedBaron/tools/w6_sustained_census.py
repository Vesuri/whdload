"""Read-only, exact-field W6 census with raw RAM snapshots and publication events."""
import argparse,json,re,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path('tools').resolve()))
from presentation_state import symbol
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--windows',type=int,default=2);p.add_argument('--from-first-world',action='store_true');p.add_argument('--append',action='store_true');a=p.parse_args()
m=json.loads((a.capture/'entry.json').read_text());lines=(a.capture/'slave.lst').read_text(encoding='latin-1').splitlines();from runtime_buffers import live_address
base=m['entry']['game_anchor']-symbol(lines,'tape_game_anchor');at=lambda n:live_address(lines,base,n,r.command);state=at('time_loop_state');sim=m['entry']['sim'];h3=json.loads((a.capture/'entry-steps.json').read_text())['h3']
fields=[('compression','short',h3+0x45a6),('transaction','short',at('time_loop_transaction')),('field','long',at('pace_state')),('cia','long',sim+0x30006),('mask','long',at('perf_mask')),('active','long',state+40),('cursor','long',state+20),('due','short',state+24),('started','long',state+28),('completed','long',at('time_pose_header')+4),('draws','long',state+36),('paused','long',state+44),('divisor','short',at('time_rate_queue')+8)]+[(f'phase{i}','long',state+i*4) for i in range(4)]
def snap(name):
 fmt='CAP '+' '.join(['%u']*len(fields))+'\\n';args=', '.join(f'*(unsigned {typ}*){addr:#x}' for _,typ,addr in fields)
 raw=r.command(f'gdb printf "{fmt}", {args}');line=next(x for x in raw.splitlines() if x.startswith('CAP '));values=dict(zip([x[0] for x in fields],map(int,line.split()[1:])))
 for lo,hi in r.memory_regions():r.command(f'gdb dump binary memory {a.capture}/{name}-{lo:x}.bin {lo:#x} {hi:#x}')
 return values
options=int(re.search(r'CUSTOM5=(-?\d+)',m['whd_args'])[1]) & 0xffffffff
start=(f'break *{at("time_pose_captured"):#x} if *(unsigned long*){at("time_pose_header")+4:#x} >= 10'
       if options & (1<<30) else f'break *{at("time_render_restored"):#x}')
if a.from_first_world: start=f'break *{at("time_pose_captured"):#x}'
if not a.append: r.command(f'gdb delete\n{start}\ncontinue\ndelete\nbreak *{at("pace_vbl"):#x} if *(unsigned short*){at("time_loop_transaction"):#x} == 0\ncontinue\ndelete')
windows=json.loads((a.capture/'field-census.json').read_text())['windows'] if a.append else []
fmt='FIELD '+' '.join(['%u']*len(fields))+'\\n'
field_args=', '.join(f'*(unsigned {typ}*){addr:#x}' for _,typ,addr in fields)
for i in range(len(windows),len(windows)+a.windows):
 before=snap(f'census-{i}-before')
 if windows: assert before==windows[-1]['after'], 'Execution gap before continued window'
 cmd=['delete',f'break *{sim+0x3154a:#x}','commands','silent',f'printf "PUB %u %u\\n", *(unsigned long*){at("pace_state"):#x}, *(unsigned long*)0xdff004','continue','end']
 for off,label in [(0x3c06,'MESSAGE'),(0x3c7c,'SHORTEN'),(0x11c8,'WORLD_BODY_DONE')]:
  cmd += [f'break *{sim+off:#x}','commands','silent',f'printf "{label}\\n"','continue','end']
 if options & (1<<31):
  bitmap=at('time_keys_bitmap')
  u=lambda address:f'*(unsigned int*){address:#x}'
  args=[u(state+28),f'({u(state+20)}-{u(state+44)})',f'({u(sim+0x30006)}-{u(state+44)})',f'*(unsigned char*){bitmap+0x4e:#x}',f'*(unsigned char*){bitmap+0x40:#x}','*(unsigned char*)($a5-6)','*(short*)($a5-14)','*(unsigned int*)($a5-4)',u(at('time_keys_popped'))]
  cmd += [f'break *{sim+0x21d30:#x}','commands','silent','printf "KEY %u %u %u %u %u %u %d %u %u\\n", '+', '.join(args),'continue','end']
 cmd += ['set $fields=0',f'break *{at("pace_vbl"):#x}','commands','silent',f'printf "{fmt}", {field_args}','set $fields=$fields+1','if $fields < 250','continue','end','end','continue','delete']
 raw=r.command('gdb '+'\n'.join(cmd));(a.capture/f'census-{i}.log').write_text(raw)
 after=snap(f'census-{i}-after');assert (after['field']-before['field'])&0xffffffff==250
 swaps=[dict(field=int(x),beam=int(y)) for x,y in re.findall(r'^PUB (\d+) (\d+)$',raw,re.M)]
 events={label:len(re.findall('^'+label+'$',raw,re.M)) for label in ['MESSAGE','SHORTEN','WORLD_BODY_DONE']}
 samples=[dict(zip([x[0] for x in fields],map(int,x.split()))) for x in re.findall(r'^FIELD ([0-9 ]+)$',raw,re.M)]
 assert len(samples)==250,len(samples)
 windows.append(dict(before=before,after=after,publications=swaps,events=events,samples=samples))
 (a.capture/'field-census.json').write_text(json.dumps(dict(sha256=m['slave_sha256'],whd_args=m['whd_args'],windows=windows),indent=2)+'\n')
 print('Window',i,'fields',250,'completed world ticks',after['completed']-before['completed'],'publications',len(swaps),'events',events,flush=True)

if options & (1<<31):
 for name,size in [('time_input_observe_queue',4112),('time_input_replay_records',64),('time_input_replay_done',6),('time_keys_commands',516),('time_keys_consumed',8)]:
  addr=at(name);r.command(f'gdb dump binary memory {a.capture}/{name}.bin {addr:#x} {addr+size:#x}')
