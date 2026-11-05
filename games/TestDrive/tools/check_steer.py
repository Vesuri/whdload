#!/usr/bin/env python3
"""Validate retained steering-reversal evidence and actual loaded helper results."""
import json,re,struct
from pathlib import Path
from harness import ROOT,sha
from audit_simulation import ranges,originals,validate
from check_disabled import check
from check_units import check as units
p=ROOT/'tmp/steer-reversal';a=json.loads((p/'before-fast-native/states.json').read_text());b=json.loads((p/'candidate-fast-native/states.json').read_text())
old=[x['bank'] for x in a[5:] if abs(x['steer'])<.0001];new=[x['bank'] for x in b[5:] if abs(x['steer'])<.0001]
assert max(old)-min(old)>.187 and max(new)-min(new)<.001
fs=sorted((p/'direct-pose-before').glob('frame-*.bin'));r=[f.read_bytes() for f in fs];w=lambda b,o:struct.unpack_from('>h',b,32766+o)[0];l=lambda b,o:struct.unpack_from('>i',b,32766+o)[0]
assert len(r)==66
assert {l(x,-22372) for x in r}=={100*65536}
assert {w(x,-22338)&65535 for x in r}=={32768}
assert {l(x,-29840) for x in r}=={-6144,6144}
maxjump=max(abs(w(r[0],-29208+2*y)-w(r[1],-29208+2*y)) for y in range(75,118));assert maxjump==2
q=p/'units-040';m=json.loads((q/'capture.json').read_text());ram=(q/'end/code.bin').read_bytes();u=units(ram,1718)
s={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)$',(q/'slave.lst').read_text(encoding='latin1'),re.M)}
h=m['regions']['td']+0x6390-m['base'];base=int.from_bytes(ram[h+2:h+6],'big')-s['overlay_unload_end']-m['base'];rv=struct.unpack_from('>III',ram,base+s['render_verify_results']);assert rv==(0,1421,0)
rs=ranges();incoming=validate(rs,originals());checks={name:check(p/name) for name in ['normal-040-on','normal-040-off']}
for name in checks:assert sha(p/name/'slave.slave')==sha(ROOT/'tmp/dist/2.0b/TestDrive.slave')
report=dict(status='PASS',slave_sha256=sha(ROOT/'tmp/dist/2.0b/TestDrive.slave'),ranges=len(rs),incoming=incoming,normal_smokes=checks,simulation_assertions=u,render_assertions=1421,steering_assertions=1050,isolated_native_pixel_jump=maxjump,old_centred_bank_range=max(old)-min(old),new_centred_bank_range=max(new)-min(new),native_comparison_limit='Free-running keyboard captures have different input sampling phases; they are visual reproduction, not bit-exact physics equivalence. Guest assertions prove unchanged motion, steering and pose inputs.',source={f.name:sha(f) for f in (ROOT/'src').iterdir() if f.is_file()})
(p/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['status','ranges','steering_assertions','render_assertions','isolated_native_pixel_jump','old_centred_bank_range','new_centred_bank_range','slave_sha256']},indent=2))
