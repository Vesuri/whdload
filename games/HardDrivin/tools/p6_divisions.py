"""Per-frame CPU budget of a 500-field solver trace.

Every main-context instruction is assigned to the gameplay-loop call site that
was executed last (`$10ec8..$10f5e`), so slave hooks patched into the loop and
all their callees stay attributed to that loop phase. Cycles are further split
by owner (game, data-hunk trampolines, slave module, ROM). Interrupt-context
cycles and STOP are separate. Inclusive cost and call counts of selected native
routines come from a main-context call stack. Only complete swap intervals are
averaged. Usage:
  frame_budget.py RUN [RUN...]   (run names below tmp/prof)
"""
import bisect,collections,json,re,struct,sys
from pathlib import Path
import barto_mmap as barto
from harddrivin_report import contexts
from machine_profiles import banks

PHASES={0x10ed4:'hook10ed4',0x10f0c:'07c32 controls',0x10f10:'108a2',0x10f14:'0d960 camera+record',
 0x10f18:'0d40e traffic',0x10f1c:'0e49a scene prep',0x10f20:'0b0d6 scene xform',0x10f24:'0cda4 physics',
 0x10f28:'10f28 wait+background(+substeps)',0x10f2c:'0e706 background',0x10f30:'10008 scene draw',0x10f3a:'0f894',
 0x10f3e:'1046e',0x10f42:'1058e',0x10f46:'10238',0x10f4a:'0eb22 cockpit',0x10f4e:'10020',0x10f52:'10f52 replay/hook',
 0x10f56:'00750 submit'}
WATCH={0x0cda4:'physics',0x0b662:'engine',0x0b500:'position',0x0d40e:'traffic',0x0d960:'camera',0x089d8:'record',
 0x0e49a:'scene prep',0x0b0d6:'scene xform',0x0e706:'background',0x10008:'scene draw',0x0329a:'polyfill',
 0x02a2e:'rotate',0x03736:'clip',0x02da2:'edge setup',0x03a28:'bgfill',0x00740:'wait',0x0eb22:'cockpit'}
MODULES=['_drivetrain','_phase','_projection','_motion','_time','_record','_sweep','_traffic','_scalar','_contact',
 '_audio','_dispatch','_scene','_replay','_presentation','_timeline','_decay','_dissipation','_events','_smc','_blitwait']
root=Path(__file__).resolve().parents[1]/'tmp/prof'
for name in sys.argv[1:]:
 out=root/name;meta=json.loads((out/'metadata.json').read_text());lay=meta['layout'];code=lay['code_base']
 data=next(r for r in lay['regions'] if r['name']=='data')
 symbols={n:int(v,16) for n,v in re.findall(r'^(_\w+)\s+00:([0-9a-fA-F]+)',(out/'slave.lst').read_text(encoding='latin1'),re.M)}
 slave=lay['published']-symbols['_code_start'];ordered=sorted((v,n) for n,v in symbols.items());addrs=[x[0] for x in ordered]
 size=(out/'slave.slave').stat().st_size
 images=[(base,(out/('anchor-'+n+'.bin')).read_bytes()) for n,base,_ in banks(meta['configuration'])]
 def word(pc):
  for base,b in images:
   if base<=pc<base+len(b)-1:return struct.unpack_from('>H',b,pc-base)[0]
 def long(a):
  h=word(a);l=word(a+2);return None if h is None or l is None else h<<16|l
 t=barto.load(out/'trace.bin');ranges=contexts(t,t.fields)
 entry_sp=next(r[15] for f in t.fields for pc,c,r in t.instructions(f) if pc==code+0xcda4)
 main=next((lo,hi) for lo,hi in ranges if lo<=entry_sp<hi)
 lo_loop,hi_loop=code+0x10ec8,code+0x10f5e
 symcache={}
 def owner(pc):
  if pc in symcache:return symcache[pc]
  if code<=pc<code+0x11a4e:o='game'
  elif data['base']<=pc<data['base']+data['size']:o='data-hunk'
  elif slave<=pc<slave+size:
   i=bisect.bisect_right(addrs,pc-slave)-1;n=ordered[i][1] if i>=0 else '_header'
   o='slave'+next((m for m in MODULES if n.startswith(m)),':'+n)+'|'+n
  elif pc>=0xf80000:o='rom'
  else:o='other'
  symcache[pc]=o;return o
 divisions=[]
 frames=[];cur=collections.Counter();key='pre-loop';stack=[];pending=None
 for f in t.fields:
  for pc,c,r in t.instructions(f):
   if pc is None:cur['[stopped]']+=c;pending=None;continue
   sp=r[15]
   if pc==code+0x122e8:divisions.append([r[0],((r[1]&65535)<<16)|(r[1]>>16)])
   if pc==0x7fffffff or not(main[0]<=sp<main[1]):
    cur['[irq]']+=c
    if pc==code+0xb4:frames.append(cur);cur=collections.Counter()
    continue
   if pending is not None:
    if sp==pending-4:
     target=pc
     if word(pc)==0x4ef9:target=long(pc+2)
     stack.append((pending,target))
     if target is not None and target-code in WATCH:cur['calls:'+WATCH[target-code]]+=1
    pending=None
   while stack and sp>=stack[-1][0]:stack.pop()
   if pc-code in WATCH:cur['entries:'+WATCH[pc-code]]+=1
   if lo_loop<=pc<hi_loop:key=PHASES.get(pc-code,'loop-body')
   o=owner(pc);mod,_,sym=o.partition('|')
   
   if key=='0cda4 physics':
    cur['pc:'+hex(pc)]+=c
    if pc is not None and word(pc)==0x4e56:cur['func:'+hex(pc)]+=1
   cur[key]+=c;cur['own:'+key+' | '+mod]+=c;cur['mod:'+mod]+=c
   if sym:cur['sym:'+sym]+=c
   seen=set()
   for _,tg in stack:
    if tg is not None and tg-code in WATCH and tg not in seen:seen.add(tg);cur['incl:'+WATCH[tg-code]]+=c
   op=word(pc)
   if op is not None and ((op&0xff00)==0x6100 or (op&0xffc0)==0x4e80):pending=sp
   if pc==code+0xb4:frames.append(cur);cur=collections.Counter()
 o=8+4*len(t.sections)+16
 for _ in range(3):o+=4+struct.unpack_from('<I',t.data,o)[0]
 clock,unit=struct.unpack_from('<II',t.data,o);ms=lambda v:v*unit/(clock*64)*1000
 full=frames[1:];nf=len(full)
 agg=collections.Counter()
 for fr in full:agg.update(fr)
 total=sum(v for k,v in agg.items() if ':' not in k)
 res=dict(divisions=divisions,fields=len(t.fields),swaps=len(frames),complete_frames=nf,mean_frame_ms=ms(total)/nf,
  physics_slave_ms=ms(sum(v for k,v in agg.items() if k.startswith('own:0cda4 physics | slave')))/nf,
  physics_native_ms=ms(sum(v for k,v in agg.items() if k.startswith('own:0cda4 physics | ') and not k.startswith('own:0cda4 physics | slave')))/nf,
  phases={k:ms(v)/nf for k,v in agg.most_common() if ':' not in k},
  owners={k[4:]:ms(v)/nf for k,v in agg.most_common() if k.startswith('own:') and ms(v)/nf>=0.02},
  owners_all={k[4:]:ms(v)/nf for k,v in agg.most_common() if k.startswith('own:')},
  modules={k[4:]:ms(v)/nf for k,v in agg.most_common() if k.startswith('mod:')},
  inclusive={k[5:]:dict(ms_per_frame=ms(v)/nf,calls_per_frame=agg['calls:'+k[5:]]/nf) for k,v in agg.most_common() if k.startswith('incl:')},
  entries_per_frame={k[8:]:v/nf for k,v in agg.most_common() if k.startswith('entries:')},
  slave_symbols={k[4:]:ms(v)/nf for k,v in agg.most_common(400) if k.startswith('sym:') and ms(v)/nf>=0.02},
  physics_pc={k[3:]:ms(v)/nf for k,v in agg.most_common() if k.startswith('pc:')},
  physics_entries={k[5:]:v/nf for k,v in agg.most_common() if k.startswith('func:')},
  frames=[dict(ms=ms(sum(v for k,v in fr.items() if ':' not in k)),polys=fr['entries:polyfill'],engine=fr['entries:engine']) for fr in full])
 (out/'division-detail.json').write_text(json.dumps(res,indent=1)+'\n')
 print(f'== {name}: {len(frames)} swaps, {nf} complete frames, {res["mean_frame_ms"]:.2f} ms/frame')
 print('  entries/frame',{k:round(v,2) for k,v in res['entries_per_frame'].items()})
 for sec in ['phases','modules','inclusive']:
  print(' ',sec)
  for k,v in res[sec].items():print(f'    {k:40s} {v if isinstance(v,float) else v["ms_per_frame"]:8.2f}'+('' if isinstance(v,float) else f'  calls/frame {v["calls_per_frame"]:.2f}'))
