#!/usr/bin/env python3
"""Read the slave's assembly rate-check results from a captured memory dump.
  check_units.py OUT --base 0xc00000   (68000)
  check_units.py OUT --base 0x200000   (fast RAM)
Requires a VERIFY capture with CUSTOM5 set (the checks run before PatchSeg).
59 checks use the one-field default period; 48 cover both shipping periods.
Sub-unit builds add 12 viewport-edge/fraction assertions; curve builds add
2 straight-segment seed assertions. Horizontal builds add 6 tangent-cache
assertions (empty keys, collisions, negative fractions, bounds and rebinding);
slope builds add 2 (walker hook: interpolated heading result and height).
"""
import argparse, os, struct
from pathlib import Path
from td2_report import regions
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('capture',type=Path)
p.add_argument('--base',type=lambda s:int(s,0),default=0xc00000)
a=p.parse_args()
os.environ['SLAVE']=str((a.capture/'slave.slave').resolve())
b=(a.capture/'code.bin').read_bytes()
lo,hi,_=next((lo,hi,origin) for lo,hi,name,origin in regions(b,a.base) if name=='slave')
marker=b'TD2RATECHECK\0'
start=b.find(marker,lo-a.base,hi-a.base)
assert start>=0, 'no assembly rate-check results in this slave'
failures,cases=struct.unpack_from('>II',b,(start+len(marker)+1)&~1)
print(f'Assembly rate invariants: {cases} cases, {failures} failures')
loaded=b[lo-a.base:hi-a.base]
expected=129 if b'TD2SLOPECHECK\0' in loaded else 127 if b'TD2HORIZCHECK\0' in loaded else (121 if b'TD2SEEDCHECK\0' in loaded else (119 if b'TD2RENDERCHECK\0' in loaded else 107))
assert cases==expected and failures==0, 'assembly rate checks did not pass'
