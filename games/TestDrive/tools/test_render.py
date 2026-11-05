#!/usr/bin/env python3
"""Negative controls for phase-10 evidence readers; retained captures stay intact."""
import json
from pathlib import Path
from unittest.mock import patch
from harness import ROOT
from check_render_units import check
from subunit_geometry import validate,A
from zero_render import compare
base=ROOT/'tmp/phase10';original=Path.read_bytes
results=[]
def reject(name,target,offset,fn):
 def changed(path):
  raw=original(path)
  if path==target:
   raw=bytearray(raw);raw[offset]^=1;raw=bytes(raw)
  return raw
 with patch.object(Path,'read_bytes',changed):
  try:fn()
  except AssertionError:results.append(name);return
 raise AssertionError('undetected '+name)
p=base/'zero-final-on/end/code.bin';raw=p.read_bytes();at=(raw.index(b'TDRENDER10\0')+12)&~1
reject('native assertion count',p,at+7,lambda:check(p))
f=base/'crossing-before-fixed/view-0'
reject('road coordinate',f/'main-03.bin',A-29844,lambda:validate(f))
a=base/'zero-final-off/view-0';b=base/'zero-final-on/view-0'
reject('zero scanline',b/'main-after.bin',A-29208,lambda:compare(a,b))
# Quotient terms cancel: only low four bits can affect the main split shift.
# Exhaust both fractional residues and signed integer-product residues.
maximum=max(abs(((i+f)//4-(i+f)//16)-(i//4-i//16+f//4-f//16)) for i in range(-16,16) for f in range(65536))
assert maximum<=1,maximum
print(json.dumps(dict(status='PASS',rejected=results,lateral_rounding_max_lsb=maximum),indent=2))
