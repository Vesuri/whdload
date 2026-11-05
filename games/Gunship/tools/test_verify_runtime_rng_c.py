from pathlib import Path
import unicorn_b as u
from amitools.binfmt.BinFmt import BinFmt
u.blob=bytes(BinFmt().load_image(str(u.build/'verify/Gunship.Slave')).get_segments()[0].get_data())
u.listing=(u.build/'verify/Gunship.lst').read_text(encoding='latin1')
policy=(Path(__file__).with_name('test_verify_policy.py')).read_text()
for pointer,ready in [(0,0),(0x600000,0),(0x600000,1)]:
 setup=f'''
c.put(base+symbol('timing_runtime_arena'),struct.pack('>I',{pointer}))
c.put(0x600000+symbol('RT_READY'),struct.pack('>I',{ready}))
rng=0x600000+symbol('RT_RNG');original=bytes(range(108));c.put(rng,original)
'''
 check=f'''
expected_rng=bytearray(original)
if {pointer} and {ready}:
 for offset in (0x20,0x32):expected_rng[offset:offset+8]=bytes.fromhex('4e71')*4
assert c.get(rng,108)==expected_rng
'''
 exec(policy.replace('expected={r:',setup+'\nexpected={r:').replace('c.close();print',check+'\nc.close();print'),{})
print('PASS: private RNG policy, null/unready guards, and verifier register ABI')
