from pathlib import Path
import json,re,sys,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path(__file__).resolve().parents[1]
name=sys.argv[1];p=r/'tmp/step5'/name;j=json.loads((p/'result.json').read_text());probe=int(j['probe'],16)
lst=Path(j['slave']).with_name('fine.list').read_text();syms={n:probe+int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',lst,re.M)}
targets={syms[n]:n for n in ('FF1MultiplyS32x16_000','FF1MultiplyNative200')}
loops=[];cur=None;prev=None
trace=barto.load(p/'detail.bin')
for f in trace.fields:
 for pc,cost,regs in trace.instructions(f):
  if pc==0x65174:
   if cur is not None:loops.append(cur)
   cur=[]
  if pc in targets and cur is not None:cur.append((targets[pc],prev,regs[0],regs[1]))
  prev=pc
loops=loops[1:19];out={'complete_updates':len(loops),'helpers':{}}
signed=lambda x:x if x<0x80000000 else x-0x100000000
for n in targets.values():
 rows=[x for loop in loops for x in loop if x[0]==n];sites={}
 for _,site,a,b in rows:
  key=hex(site-probe) if probe<=site<probe+len(Path(j['slave']).read_bytes()) else hex(site)
  d=sites.setdefault(key,dict(calls=0,a_fits_s16=0,b_fits_s16=0,zero_coefficient=0,integer_q16=0,narrow_after_existing_shortcuts=0,general_calls=0,unsigned_word_pair=0,signed_word_pair=0,a_min=signed(a),a_max=signed(a)))
  d['unsigned_word_pair']+=a<=65535 and b<=65535;d['signed_word_pair']+=-32768<=signed(a)<=32767 and -32768<=signed(b)<=32767;d['general_calls']+=bool((a&65535) and (b&65535));d['narrow_after_existing_shortcuts']+=bool((a&65535) and (b&65535) and -32768<=signed(a)<=32767);d['calls']+=1;d['a_fits_s16']+=-32768<=signed(a)<=32767;d['b_fits_s16']+=-32768<=signed(b)<=32767;d['zero_coefficient']+=(b&65535)==0;d['integer_q16']+=(a&65535)==0;d['a_min']=min(d['a_min'],signed(a));d['a_max']=max(d['a_max'],signed(a))
 out['helpers'][n]={'calls':len(rows),'sites':sites}
(p/'multiply-operands.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
