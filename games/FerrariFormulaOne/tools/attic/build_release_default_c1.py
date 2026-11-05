from pathlib import Path
import struct,json,hashlib
r=Path(__file__).resolve().parents[1];out=r/'tmp/build/release-default-c1-control';out.mkdir(exist_ok=True);report={}
for src in (r/'tmp/build/production-default-control').glob('*.slave'):
 b=bytearray(src.read_bytes());sites=[i for i in range(len(b)) if b.startswith(bytes.fromhex('337c4eb9589c'),i)]
 assert len(sites)==2
 for i in sites:
  assert b[i-2:i]==bytes.fromhex('660e');b[i-2:i]=bytes.fromhex('4e71')
  assert b[i+6:i+8]==bytes.fromhex('487a')
  timing=i+8+struct.unpack_from('>h',b,i+8)[0]
  assert b[timing:timing+2]==bytes.fromhex('6100') and b[timing+4:timing+6]==bytes.fromhex('4e71')
  # Only the fixture's original six instructions run, then return immediately.
  # No native timing wait: CUSTOM1=1 semantics, with controlled first RNG state.
  b[timing+6:timing+8]=bytes.fromhex('4e75')
 (out/src.name).write_bytes(b);report[src.name]={'sha256':hashlib.sha256(b).hexdigest(),'timing_install_sites':sites}
(out/'fixture.json').write_text(json.dumps(report,indent=2))
p=r/'tools/test_release_default_c1.py';s=p.read_text().replace("r/'tmp/build/production-default-control'","r/'tmp/build/release-default-c1-control'");p.write_text(s)
