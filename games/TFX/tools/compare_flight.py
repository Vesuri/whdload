#!/usr/bin/env python3
"""Compare replay bytes; additionally test a translation of the absolute clock origin.

No bytes are excluded. Five identified 32-bit timer values are translated by the
first checkpoint's vblank clock; all bytes of the resulting hunks are compared.
Raw hashes, differences and clock-origin translation remain explicit in the report.
"""
import argparse, hashlib, json, struct
from pathlib import Path
TIMERS={
 '020': {0:[0x4bba6,0x4bbd0],5:[0x57bc,0x9a74,0xbefe]},
 'fpu': {0:[0x4d85a,0x4d884],1:[0x10678,0x13de0,0x17012]},
}
def compare(a,b):
 a,b=Path(a),Path(b)
 ma=json.loads((a/'manifest.json').read_text());mb=json.loads((b/'manifest.json').read_text())
 assert ma['machine']==mb['machine'];m=ma['machine'];timers=TIMERS['020' if m=='020' else 'fpu']
 clock=timers[0][1]
 epochs=[struct.unpack_from('>I',(p/'swap-001-hunk0.bin').read_bytes(),clock)[0] for p in [a,b]]
 report={'machine':m,'raw_identical':True,'clock_relative_identical':True,'screenshots_identical':True,'first_swap_clocks':epochs,'clock_origin_delta':epochs[1]-epochs[0],'checkpoints':{}}
 assert ma['checkpoints'].keys()==mb['checkpoints'].keys()
 for frame,files in ma['checkpoints'].items():
  rows={}
  assert files.keys()==mb['checkpoints'][frame].keys()
  for name,expected in files.items():
   x=(a/name).read_bytes();y=(b/name).read_bytes()
   assert hashlib.sha256(x).hexdigest()==expected
   assert hashlib.sha256(y).hexdigest()==mb['checkpoints'][frame][name]
   raw=x==y;report['raw_identical'] &= raw
   if name.endswith('.png'):
    report['screenshots_identical'] &= raw;relative=raw
   else:
    h=int(name.split('-hunk')[1].split('.')[0]);u,v=bytearray(x),bytearray(y)
    for data,epoch in [(u,epochs[0]),(v,epochs[1])]:
     for off in timers.get(h,[]):
      value=struct.unpack_from('>I',data,off)[0]
      struct.pack_into('>I',data,off,(value-epoch)&0xffffffff)
    relative=u==v
   report['clock_relative_identical'] &= relative
   rows[name]={'raw_identical':raw,'clock_relative_identical':relative}
   if not raw:rows[name]['differing_byte_offsets']=[hex(i) for i,(u,v) in enumerate(zip(x,y)) if u!=v]
  report['checkpoints'][frame]=rows
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('run_a');p.add_argument('run_b');p.add_argument('--output');a=p.parse_args()
 r=compare(a.run_a,a.run_b);text=json.dumps(r,indent=2)
 if a.output:Path(a.output).write_text(text+'\n')
 print(json.dumps({k:v for k,v in r.items() if k!='checkpoints'},indent=2))
 raise SystemExit(0 if r['clock_relative_identical'] else 1)
