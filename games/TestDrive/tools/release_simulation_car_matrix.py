#!/usr/bin/env python3
"""Capture the explicit five-car p=2/p=5 straight/route phase-8 checkpoint.
No renderer/hardware acceptance is inferred from this handling matrix.
"""
import argparse,json,subprocess,sys
from harness import ROOT,sha
from check_disabled import check as byte_check
from check_timing import check as timing_check
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('prefix');p.add_argument('--cars',nargs='+',type=int,default=list(range(5)))
p.add_argument('--periods',nargs='+',type=int,choices=[2,5],default=[2,5])
p.add_argument('--tapes',nargs='+',choices=['straight','route'],default=['straight','route'])
a=p.parse_args();assert all(0<=c<5 for c in a.cars)
build=ROOT/'tmp/build/verify/TestDrive.Slave';digest=sha(build)
report=ROOT/'tmp/phase11'/(a.prefix+'-matrix.json');assert not report.exists(),'fresh matrix prefix required'
result={'slave_sha256':digest,'scope':'Five-car handling checkpoint; events, cross-CPU and native original-rate equivalence checked separately','captures':[]}
for car in a.cars:
 for period in a.periods:
  for tape in a.tapes:
   assert sha(build)==digest,'build changed during matrix'
   name=f'{a.prefix}-car{car}-p{period}-{tape}'
   c5=(car<<8)|(17 if tape=='straight' else 1)
   subprocess.run([sys.executable,str(ROOT/'tools/release_simulation_capture.py'),name,'--preset','a1200','--fields','1300','--c1',str(4 if period==5 else 0),'--c5',str(c5)],check=True)
   path=ROOT/'tmp/phase11'/name
   assert sha(path/'slave.slave')==digest
   b=byte_check(path);t=timing_check(path)
   s=json.loads((path/'states/samples.json').read_text())
   assert {x['period'] for x in s}=={period}
   frame=(path/'states/frame-0000.bin').read_bytes()
   assert int.from_bytes(frame[60:62],'big')==car,'wrong selected car'
   metrics={'car':car,'period':period,'tape':tape,'peak_mph':max(x['speed'] for x in s)/65536,'end_position':s[-1]['pos'],'end_x':s[-1]['x'],'x_range':[min(x['x'] for x in s),max(x['x'] for x in s)],'gears':sorted({x['gear'] for x in s}),'units':json.loads((path/'units.json').read_text()),'timing':t,'byte_ranges':len(b['ranges'])}
   (path/'byte-check.json').write_text(json.dumps(b,indent=2)+'\n')
   (path/'handling.json').write_text(json.dumps(metrics,indent=2)+'\n')
   result['captures'].append(dict(name=name,**metrics));report.write_text(json.dumps(result,indent=2)+'\n')
   print(json.dumps(dict(completed=name,peak_mph=metrics['peak_mph'],position=metrics['end_position'])),flush=True)
result['status']='PASS';report.write_text(json.dumps(result,indent=2)+'\n')
