"""Read-only 250-field W6 render-stage wall-clock capture on an existing boot."""
import argparse,json,re,sys
from pathlib import Path
import route_status as r,step_log
sys.path.insert(0,str(Path('tools').resolve()))
from presentation_state import symbol
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--stem',default='render-budget');a=p.parse_args()
m=json.loads((a.capture/'entry.json').read_text());lines=(a.capture/'slave.lst').read_text(encoding='latin-1').splitlines()
at=r.locate();state=r.read(at);obs,h=step_log.header();sim=state['sim'];base=m['entry']['game_anchor']-symbol(lines,'tape_game_anchor');label=lambda n:base+symbol(lines,n)
assert m['slave_sha256']=='ac1d47ba01210c496a98db199b79fa2c30b0f3b59c570a0bec8906dfa7a116f7'
# Reach a later native update, then align the observation to a known VBlank.
raw=r.command(f'gdb delete\nbreak *{state["game_anchor"]:#x} if *(unsigned long*){at+44:#x} >= 80\ncontinue\ndelete\nbreak *{sim+0x2d34e:#x}\ncontinue\ndelete')
(a.capture/(a.stem+'-start.log')).write_text(raw)
first=step_log.collect();before=int(re.search(r'COUNT (\d+)',r.command(f'gdb printf "COUNT %u\\n", *(unsigned long*){obs+36:#x}'))[1])
routines=[('native_draw',label('time_render_before_draw'),label('time_render_after_draw')-2),('world3d',sim+0x2c552,sim+0x2c806)]
routines += [('cockpit_a',sim+0x19ba6,sim+0x19e12),('cockpit_b',sim+0x15e96,sim+0x163a0)]
routines += [(n,sim+s,sim+e) for n,s,e in [('background',0x5fe,0x6bc),('scene',0x6bc,0x7c4),('cockpit',0x7c4,0x830),('messages',0x830,0xafe),('publication',0xafe,0xb10)]]
endpoints={}
for n,s,e in routines:
 endpoints.setdefault(s,[]).append((n,'enter'));endpoints.setdefault(e,[]).append((n,'return'))
commands=['delete','set $budget_fields=0']
for pc,tags in endpoints.items():
 commands += [f'break *{pc:#x}','commands','silent']
 for n,tag in tags:
  commands += [f'printf "RB_CLOCK {n} {tag} %u %u %u %u %u\\n", *(unsigned long*){at+44:#x}, *(unsigned long*){obs+36:#x}, *(unsigned long*)0xdff004, *(unsigned long*){sim+0x30006:#x}, $sp']
 commands += ['continue','end']
commands += [f'break *{sim+0x2d34e:#x}','commands','silent',f'printf "RB_VBL %u %u\\n", *(unsigned long*){obs+36:#x}, *(unsigned long*)0xdff004','set $budget_fields=$budget_fields+1','if $budget_fields < 250','continue','end','end','continue',f'printf "RB_BUDGET_STOP %u %u\\n", $pc, *(unsigned long*){obs+36:#x}','delete']
raw=r.command('gdb '+'\n'.join(commands));(a.capture/(a.stem+'.log')).write_text(raw)
stop=re.search(r'RB_BUDGET_STOP (\d+) (\d+)',raw);assert stop and int(stop[1])==sim+0x2d34e and int(stop[2])-before==250
rows=[];active={};calls=[];unmatched=[]
for n,tag,step,vbl,beam,ticks,sp in re.findall(r'RB_CLOCK (\w+) (\w+) (\d+) (\d+) (\d+) (\d+) (\d+)',raw):
 row=dict(routine=n,kind=tag,step=int(step),vbl=int(vbl),beam=int(beam),ticks=int(ticks),sp=int(sp));row['line']=(row['beam']>>8)&511;row['hpos']=row['beam']&255;rows.append(row)
 if tag=='enter':
  assert n not in active,(n,active[n]);active[n]=row
 elif n in active:
  old=active.pop(n);assert old['sp']==row['sp'],(n,old,row)
  calls.append(dict(routine=n,entry=old,return_record=row))
 else:unmatched.append(row)
phase=[dict(vbl=int(v),beam=int(b),line=(int(b)>>8)&511) for v,b in re.findall(r'RB_VBL (\d+) (\d+)',raw)]
assert len(phase)==250 and all(y['vbl']==x['vbl']+1 for x,y in zip(phase,phase[1:]))
result=dict(sha256=m['slave_sha256'],complete=True,fields=250,first_step=first['count'],steps=step_log.collect(),vblank_phase=phase,routines=routines,rows=rows,calls=calls,open_calls=list(active.values()),unmatched_returns=unmatched,scope='Read-only full-stage wall time including IRQ execution; phase filtering required. Same-stage endpoints balance the stack. Not CPU-only cycles, call-inclusive sums or an FPS measurement.')
(a.capture/(a.stem+'.json')).write_text(json.dumps(result,indent=2)+'\n');print('Complete 250 fields;',len(calls),'complete stage spans;',len(active),'open spans')
