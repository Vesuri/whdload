import collections,json,statistics
from pathlib import Path
import barto_mmap as barto
from window_metrics import Memory
from machine_profiles import banks
P=Path(__file__).resolve().parents[1]/'tmp/prof';allrows={}
for w in ['A','B','impact']:
 out=P/('s3-profile-a500-impact' if w=='impact' else 's2-profile-a500-'+w);m=json.loads((out/'metadata.json').read_text());code=m['layout']['code_base'];mem=Memory([(base,(out/('anchor-'+name+'.bin')).read_bytes()) for name,base,size in banks(m['configuration'])]);t=barto.load(out/'trace.bin');irq=False;act=None;ctrl=None;lastcontrol=None;rows=[];cs=[];clock_x=collections.Counter()
 for f in t.fields:
  for pc,c,r in t.instructions(f):
   off=pc-code if pc is not None else -1
   if off==0x2c72:clock_x[str(bool(r[16]&16))]+=1
   if pc==0x7fffffff or off==0x44:irq=True
   if off==0x7c32:ctrl=0
   if off==0xcda4:act=dict(field=f.index,cycles=0,controls=lastcontrol,markers=[])
   if not irq:
    if ctrl is not None:ctrl+=c
    if act is not None:
     act['cycles']+=c
     if off in [0xcdb2,0xb36a,0xbc62,0xbd40,0xbf80,0xbce0,0xbdbe,0xbf8c,0xcc54,0xcd82,0xcde2]:act['markers'].append(hex(off))
   if off==0x7dfa and ctrl is not None:cs.append(ctrl);lastcontrol=ctrl;ctrl=None
   if off==0xcdb0 and act is not None:
    act['combined']=act['cycles']+act['controls'] if act['controls'] is not None else None
    rows.append(act);act=None
   if pc is not None and pc!=0x7fffffff and mem.word(pc)==0x4e73:irq=False
 def stats(v):return dict(n=len(v),min=min(v),mean=statistics.mean(v),median=statistics.median(v),max=max(v)) if v else None
 for row in rows:
  ms=row['markers'];row['class']='recovery-skip' if '0xcdb2' not in ms else 'collision' if any(x in ms for x in ['0xbc62','0xbd40','0xbf80','0xcc54','0xcde2']) else 'crash-tail' if '0xb36a' not in ms else 'airborne' if '0xcd82' in ms else 'ordinary'
 summary={k:stats([r['combined'] for r in rows if r['class']==k and r['combined'] is not None]) for k in set(r['class'] for r in rows)}
 allrows[w]=dict(lap_clock_incoming_X=dict(clock_x),controls=stats(cs),physics=stats([r['cycles'] for r in rows]),classes=summary,rows=rows);print(w,json.dumps({k:v for k,v in allrows[w].items() if k!='rows'}),flush=True)
 del t
(P/'step3-costs.json').write_text(json.dumps(allrows,indent=2)+'\n')
