#!/usr/bin/env python3
"""D4 credit-cycle, visible asteroid, world cadence and publication evidence."""
import argparse,json,re
from pathlib import Path
from PIL import Image
from ocs_baseline_report import parse
from ocs_publication_report import window
from ocs_reconstruct import new_output,require

def grey_component(path):
 im=Image.open(path).convert('RGB')
 points={(i%im.width,i//im.width) for i,(r,g,b) in enumerate(im.get_flattened_data() if hasattr(im,'get_flattened_data') else im.getdata())
         if r>=32 and max(r,g,b)-min(r,g,b)<10}
 largest=0
 while points:
  todo=[points.pop()];n=0
  while todo:
   x,y=todo.pop();n+=1
   for q in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
    if q in points:points.remove(q);todo.append(q)
  largest=max(largest,n)
 return largest

def report(root,build):
 b=json.loads((build/'build.json').read_text());m=json.loads((root/'result.json').read_text());sy=b['symbols']
 require(b.get('intro') and m['slave_sha256']==b['sha256'],'not the D4 build')
 def own(label,name,size=4):
  raw=(root/f'{label}-fast.bin').read_bytes();off=m['slave']-0x200000+sy[name]
  return int.from_bytes(raw[off:off+size],'big')
 for label in ('menu','simulator','name'):
  require(own(label,'intro_active',2)==0,'intro leaked into '+label)
 require(own('credits','ocs_intro_completed')==296,'title did not execute 296 updates')
 require(own('title','ocs_clock_active',2)==0,'flight controls enabled in title')
 rows=parse(root/'asteroids-events.txt');pixels=window(rows,250)
 start=rows[0];end=next(r for r in rows if r[0]=='E')
 require(start[2:5]==[28375160,512,256 if m['effective']['cpu_model']=='68000' else 128],'uncalibrated clock')
 fields=[r for r in rows if r[0]=='F']
 require(set(y[1]-x[1] for x,y in zip(fields,fields[1:]))<={227*312*512,227*313*512},'field clock')
 ticks=len([r for r in rows if r[0]=='P' and r[2]==0x2dc])
 require(ticks==((fields[-1][3]-start[5])&65535),'world counter mismatch')
 seconds=(end[1]-start[1])/(start[2]/8*start[3])
 # Report overload honestly, rather than calling native-field credit deadlines
 # proof of sustained world cadence.
 predictions=[r for r in rows if r[0]=='G' and r[5]]
 for _,_,estimate,target,ready,_ in predictions:
  delta=lambda x,y:((x-y+0x80000000)&0xffffffff)-0x80000000
  require(target==(estimate if delta(estimate,ready)>0 else ready),'early forecast')
 labels=[f'page{i}' for i in range(15)] if (root/'intro-pages.json').exists() else ['asteroids']
 visible=[]
 for label in labels:
  raw=(root/f'{label}-h1.bin').read_bytes()
  slots=[i for i in raw[0x5294:0x52a8] if i<61 and int.from_bytes(raw[0x8e8c+2*i:0x8e8e+2*i],'big')==9]
  component=grey_component(root/f'{label}.png')
  require(slots and component>=32,'no visible asteroid evidence: '+label)
  visible.append(dict(checkpoint=label,asteroid_slots=slots,largest_grey_component=component))
 cycle=None
 if (root/'intro-pages.json').exists():
  pages=json.loads((root/'intro-pages.json').read_text());require([p['page'] for p in pages]==list(range(15)),'credit coverage')
  starts=[int(re.search(r'd4\s+0x([0-9a-f]+)',p['registers'])[1],16) for p in pages]
  repeated=(root/'repeat-h1.bin').read_bytes()
  repeat_field=int.from_bytes(repeated[0x77fe:0x7802],'big')
  lengths=[(z-a)&0xffffffff for a,z in zip(starts,starts[1:]+[repeat_field])]
  require(all(320<=n<400 for n in lengths),'native page deadlines not respected')
  require(own('repeat','intro_active',2)==0 and own('repeat-title','intro_active',2)==1,'repeat rebase')
  require(own('repeat-credits','ocs_intro_completed')-own('repeat','ocs_intro_completed')==296,'repeat title ticks')
  cycle=dict(pages=15,page_intervals_fields=lengths,repeat_title_ticks=296,repeat_credits_reached=True)
 return dict(passed=True,world_ticks=ticks,seconds=seconds,world_hz=ticks/seconds,
  displayed_pictures=pixels['display_changes'],displayed_hz=pixels['display_changes']/seconds,
  predicted_queues=len(predictions),pixels=pixels,visible_asteroids=visible,cycle=cycle,
  scene_exit_clean=True,scope='PAL calibrated emulator; music code/deadlines retained, no independent audio/hardware timing claim')

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--build',required=True,type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();r=report(a.run,a.build)
 # Pixels use the existing C5 negative controls in ocs_publication_report.py.
 out=new_output(a.output);out.mkdir(parents=True);(out/'report.json').write_text(json.dumps(r,indent=2)+'\n');print({k:v for k,v in r.items() if k!='visible_asteroids'})
if __name__=='__main__':main()
