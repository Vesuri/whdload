#!/usr/bin/env python3
"""Native funeral redraw isolation and intermediate background motion."""
import argparse,json,struct
from pathlib import Path
from field_objects_check import machine
from ocs_display_check import CODE,DATA,word,long
from ocs_clock_check import SLAVE
from ocs_reconstruct import ROOT,new_output
from variants import get


def check(build,variant,model,respawn=False):
 c,sy=machine(build,variant,model);v=get(variant);ocs=variant=='ocs';a4=DATA+v.A4_BASE
 start=0x1df12 if ocs else 0x1ec4c
 region=a4+(0x40aa if ocs else 0x48ba);moving=region+0x74
 field=a4+v.A4['field_clock'];countdown=a4+(-32592 if ocs else -32624)
 surface=0x180000;image=0x181000;calls=[];salutes=[];state={}
 def noop():c.return_call()
 def bitmap():
  sp=c.reg(8)
  if c.get(sp+12,4)==image:calls.append(c.get(sp+8))
  c.return_call()
 def scaled():
  sp=c.reg(8)
  if c.get(sp+16)==9:salutes.append((c.get(sp+8),c.get(sp+10)))
  c.return_call()
 def clock(*args):
  c.write(field,long((c.get(field,4)+state['gap'])&0xffffffff))
 try:
  for off in ((0x322e0,0x2de,0x13cc6) if ocs else (0x31cd6,0x2dc,0x13f50)):c.intercept(CODE+off,noop)
  c.intercept(CODE+(0x2f9a6 if ocs else 0x2efe8),bitmap)
  c.intercept(CODE+(0x2f3a0 if ocs else 0x2ec98),scaled)
  c.intercept(SLAVE+sy['funeral_rate'],lambda:c.return_call(state['hz']))
  c.run(SLAVE-CODE+sy['funeral_install'],registers={1:CODE})
  # Native bounded fixture: one moving star, a static ceremony, no salute yet.
  c.write(region,bytes(628));c.write(region+8,word(256));c.write(region+16,word(16))
  c.write(region+0x36,word(1))
  c.write(moving,struct.pack('>hhhh',-1 if respawn else 100,50,-10,12))
  c.write(a4+(-754 if ocs else 1530),long(surface))
  c.write(a4+(-756 if ocs else 1528),word(-1))
  c.write(a4+(-0x2d70 if ocs else -0x2df2),long(image))
  c.write(surface+24,struct.pack('>hhhh',0,0,319,127))
  c.write(region+20,word(100)+word(80)) # live salute: replay must not step it again
  c.write(countdown,word(1));initial=c.read(DATA,v.HUNKS[1][2])
  c.run(SLAVE-CODE+sy['funeral_native'])
  expected=c.read(DATA,v.HUNKS[1][2]);assert calls==[65535 if respawn else 100],calls
  rows=[]
  # Advance only the wall-clock wait: native graphics retain their real logic
  # above the bitmap backend. The native mutation and full H1 must match once.
  wait=SLAVE+sy['funeral_wait']
  c.intercept(wait,clock)
  for hz in (50,60):
   for gap in (1,3):
    state.update(hz=hz,gap=gap);c.write(DATA,initial);calls.clear();salutes.clear()
    c.write(SLAVE+sy['funeral_fraction'],word(0))
    c.write(field,long(0xfffffffc))
    c.run(start)
    final=bytearray(c.read(DATA,v.HUNKS[1][2]));reference=bytearray(expected)
    at=field-DATA;final[at:at+4]=reference[at:at+4]
    assert final==reference,('state leak',[(hex(i),a,b) for i,(a,b) in enumerate(zip(final,reference)) if a!=b][:20])
    x=-1 if respawn else 100
    want=[x&65535]+[(x-int(10*f/((hz*3//50))))&65535 for f in range(gap,(hz*3//50),gap)]
    assert calls==want,(hz,gap,calls,want)
    want_salutes=[(100,80)]+[(100-int(6*f/(hz*3//50)),80-int(6*f/(hz*3//50))) for f in range(gap,hz*3//50,gap)]
    assert salutes==want_salutes,(salutes,want_salutes)
    rows.append(dict(hz=hz,gap=gap,positions=calls[:],state_restored=True))
  return dict(model=model,respawn=respawn,rows=rows)
 finally:c.close()


def main():
 p=argparse.ArgumentParser();p.add_argument('variant',choices=('cd32','ocs'));p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 rows=[check(a.build,a.variant,m,r) for m in ((1,2) if a.variant=='ocs' else (2,4)) for r in (False,True)]
 (out/'report.json').write_text(json.dumps(rows,indent=2)+'\n');print('PASS',a.variant,rows)
if __name__=='__main__':main()
