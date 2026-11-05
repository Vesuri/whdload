#!/usr/bin/env python3
"""Check paired fixed-window frame rates and unchanged endpoint gameplay state."""
import json,re,hashlib
from pathlib import Path
from harness import ROOT
from check_disabled import check as bytes_check
from compare_simulation_demo import KEYS
from timing_map import decode
OUT=ROOT/'tmp/phase11'
def read(p):return json.loads(p.read_text())
def state(p,m):
 raw=(p/'code.bin').read_bytes();offset=m['regions']['td-data']-m['base'];s=decode(raw[offset:offset+0x32a4])
 frame=m['frame']-m['base']
 for n,o in [('samples',-36),('sum_speed',-44)]:s[n]=int.from_bytes(raw[frame+o:frame+o+4],'big',signed=True)
 return {k:s[k] for k in KEYS}
def check(prefix='fps-'):
 report={'status':'PASS','scope':'Two fixed 1000-field windows per arm, nominal PAL 50 Hz; C2 simulation enabled in both','machines':{}}
 for preset in ['a500','a1200','a1200-030']:
  names=[prefix+preset+'-off',prefix+preset+'-on'];paths=[OUT/n for n in names];m=[read(p/'capture.json') for p in paths]
  assert m[0]['slave_sha256']==m[1]['slave_sha256']
  assert m[0]['options']==dict(C1=16,C2=1,C3=1,C4=0,C5=17) and m[1]['options']==dict(C1=0,C2=1,C3=1,C4=0,C5=17)
  for p in paths:
   assert bytes_check(p)['status']=='PASS';assert read(p/'units.json')['assertions']==668
  for checkpoint in ['','window-0/end','window-1/end']:
   assert state(paths[0]/checkpoint,m[0])==state(paths[1]/checkpoint,m[1]),(preset,checkpoint,'gameplay differs')
  windows=[]
  for w in range(2):
   r=[read(p/('window-'+str(w))/'swaps.json') for p in paths]
   assert all(x['fields']==1000 and x['presentations']==sum(x['marker_counts']) and x['window_fps']==50*x['presentations']/1000 for x in r)
   gain=r[1]['window_fps']-r[0]['window_fps'];assert gain>=0,(preset,w,gain)
   windows.append({'off_fps':r[0]['window_fps'],'on_fps':r[1]['window_fps'],'gain_fps':round(gain,3)})
  report['machines'][preset]={'windows':windows,'core_endpoints_equal':True}
 return report

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prefix',default='fps-');args=parser.parse_args()
 report=check(args.prefix);print(json.dumps(report,indent=2))
 (OUT/'fps-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
