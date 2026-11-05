#!/usr/bin/env python3
"""Check paired fixed-window frame gains and unchanged endpoint gameplay state."""
import json,re,hashlib
from pathlib import Path
from harness import ROOT
from check_disabled import check as bytes_check
from compare_simulation_demo import KEYS
from timing_map import decode
OUT=ROOT/'tmp/phase9'
def read(p):return json.loads(p.read_text())
def state(p,m):
 raw=(p/'code.bin').read_bytes();offset=m['regions']['td-data']-m['base'];s=decode(raw[offset:offset+0x32a4])
 frame=m['frame']-m['base']
 for n,o in [('samples',-36),('sum_speed',-44)]:s[n]=int.from_bytes(raw[frame+o:frame+o+4],'big',signed=True)
 return {k:s[k] for k in KEYS}
def check():
 report={'status':'PASS','scope':'Two fixed 1000-field windows per arm, nominal PAL 50 Hz; C2 simulation enabled in both','machines':{}}
 for preset in ['a500','a1200','a1200-030']:
  names=['candidate-'+preset+'-off'+('-retry' if preset=='a1200' else ''),'candidate-'+preset+'-on'];paths=[OUT/n for n in names];m=[read(p/'capture.json') for p in paths]
  assert m[0]['slave_sha256']==m[1]['slave_sha256']
  assert m[0]['options']==dict(C1=8,C2=1,C3=1,C4=0,C5=17) and m[1]['options']==dict(C1=0,C2=1,C3=1,C4=0,C5=17)
  for p in paths:
   assert bytes_check(p)['status']=='PASS';assert read(p/'units.json')['assertions']==668
  for checkpoint in ['','window-0/end','window-1/end']:
   assert state(paths[0]/checkpoint,m[0])==state(paths[1]/checkpoint,m[1]),(preset,checkpoint,'gameplay differs')
  windows=[]
  for w in range(2):
   r=[read(p/('window-'+str(w))/'swaps.json') for p in paths]
   assert all(x['fields']==1000 and x['presentations']==sum(x['marker_counts']) and x['window_fps']==50*x['presentations']/1000 for x in r)
   gain=r[1]['window_fps']-r[0]['window_fps'];assert gain>0.15,(preset,w,gain)
   windows.append({'off_fps':r[0]['window_fps'],'on_fps':r[1]['window_fps'],'gain_fps':round(gain,3)})
  for p,enabled in zip(paths,[False,True]):
   for name in ['hardware-start.txt','hardware-end.txt']:
    hw=[int(x,16) for x in re.findall(r':\s+(0x[0-9a-f]+)',(p/name).read_text())]
    assert hw[0]&0x400 and bool(hw[1]&0x40)!=enabled,(p,name,hw)
  report['machines'][preset]={'windows':windows,'core_endpoints_equal':True,'hardware_masks_correct':True}
 return report

if __name__=='__main__':
 report=check();print(json.dumps(report,indent=2))
 (OUT/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
