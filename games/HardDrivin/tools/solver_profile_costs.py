import bisect,collections,json,re,struct,sys
from functools import lru_cache
from pathlib import Path
import barto_mmap as barto
from harddrivin_report import contexts
from machine_profiles import banks
for name in sys.argv[1:]:
 out=Path('tmp/prof')/name;meta=json.loads((out/'metadata.json').read_text());code=meta['layout']['code_base'];symbols={n:int(v,16) for n,v in re.findall(r'^(_\w+)\s+00:([0-9a-fA-F]+)',(out/'slave.lst').read_text(encoding='latin1'),re.M)};slave=meta['layout']['published']-symbols['_code_start'];ordered=sorted((v,n) for n,v in symbols.items());addresses=[x[0] for x in ordered];size=(out/'slave.slave').stat().st_size
 images=[(base,(out/('anchor-'+n+'.bin')).read_bytes()) for n,base,_ in banks(meta['configuration'])]
 @lru_cache(maxsize=131072)
 def word(pc):
  for base,b in images:
   if base<=pc<base+len(b)-1:return struct.unpack_from('>H',b,pc-base)[0]
  return None
 t=barto.load(out/'trace.bin');total=sum(f.cycles for f in t.fields);self_cost=collections.Counter();groups=collections.Counter();active={};complete=collections.defaultdict(list);irq=False;swaps=[];attributed=0
 starts={code+0xcda4:'full_physics',code+0xb662:'native_engine',code+0xb500:'native_position'}
 ends={code+0xcdb0:'full_physics',code+0xb676:'native_engine'}
 # Native B500 ends before B662; find its final RTS from retained code.
 from capstone import Cs,CS_ARCH_M68K,CS_MODE_BIG_ENDIAN,CS_MODE_M68K_000
 dis=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000);game=(out/'game-code.bin').read_bytes()
 for ins in dis.disasm(game[0xb500:0xb662],code+0xb500):
  if ins.mnemonic=='rts':ends[ins.address]='native_position'
 # Record complete nested recording helpers, excluding interrupt-stack cycles.
 for begin,following,label in [('_sweep_world','_sweep_world_near','sweep_world'),('_record_step','_record_emit','record_transaction'),('_record_interpolate','_record_unsigned_word','record_interpolation'),('_record_angle_word','_record_lerp_unsigned','record_angle'),('_record_lerp_unsigned','_record_lerp_signed','record_unsigned')]:
  if begin not in symbols or following not in symbols:continue
  addr=slave+symbols[begin];stop=slave+symbols[following];starts[addr]=label
  blob=next(b[addr-bank:stop-bank] for bank,b in images if bank<=addr and stop<=bank+len(b))
  for ins in dis.disasm(blob,addr):
   if ins.mnemonic=='rts':ends[ins.address]=label
 if '_drivetrain_position_tick' in symbols:
  starts[slave+symbols['_drivetrain_position_tick']]='inner_position'
  ends[slave+symbols['_drivetrain_tick_after']+4]='inner_position'
 ranges=contexts(t,t.fields);entry_sp=next(regs[15] for f in t.fields for pc,c,regs in t.instructions(f) if pc==code+0xcda4);main=next((lo,hi) for lo,hi in ranges if lo<=entry_sp<hi)
 for f in t.fields:
  fswaps=0
  for pc,c,regs in t.instructions(f):
   attributed+=c
   if pc==0x7fffffff or pc==code+0x44:irq=True
   in_main=main[0]<=regs[15]<main[1] and pc!=0x7fffffff
   if pc in starts and in_main:active[starts[pc]]=0
   if in_main:
    for k in active:active[k]+=c
   if pc in ends and in_main:
    k=ends[pc]
    if k in active:complete[k].append(active.pop(k))
   if pc is not None and pc!=0x7fffffff:
    if word(pc)==0x4e73:irq=False
    if slave<=pc<slave+size:
     index=bisect.bisect_right(addresses,pc-slave)-1;n=ordered[index][1] if index>=0 else 'slave_header';self_cost[n]+=c
     group=next((x for x in ['_drivetrain','_phase','_projection','_motion','_time','_record','_sweep'] if n.startswith(x)),'other_slave');groups[group]+=c
   fswaps+=pc==code+0xb4
  swaps.append(fswaps)
 assert len(t.fields)==500 and .99<=attributed/total<=1.01
 o=8+4*len(t.sections)+16
 for _ in range(3):o+=4+struct.unpack_from('<I',t.data,o)[0]
 clock,unit=struct.unpack_from('<II',t.data,o);seconds=total*unit/(clock*64);assert abs(seconds-500*142102/7093790)<1e-6
 result=dict(fields=500,seconds=seconds,swaps=sum(swaps),per_field_swaps=swaps,cycle_unit=unit,clock=clock,coverage=attributed/total,groups={k:dict(share=v/total,milliseconds=v*unit/(clock*64)*1000) for k,v in groups.items()},completed={k:dict(calls=len(v),share=sum(v)/total,milliseconds=sum(v)*unit/(clock*64)*1000,mean_cpu_cycles=sum(v)/len(v)*unit/256) for k,v in complete.items()},slave_self=[dict(symbol=k,share=v/total,milliseconds=v*unit/(clock*64)*1000) for k,v in self_cost.most_common(20)])
 (out/'solver-costs.json').write_text(json.dumps(result,indent=2)+'\n');print(name,json.dumps({k:v for k,v in result.items() if k!='per_field_swaps'},indent=2),flush=True)
