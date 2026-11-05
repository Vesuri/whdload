import json,sys
from harness_a import *
s=Session(sys.argv[1])
try:
 s.cmd('monitor fields 999',timeout=60);s.input('JOY2_FIRE_BUTTON',1)
 s.cmd('break *0x4936');print(s.cmd('continue',timeout=60),flush=True)
 base=rd(s,0x4c98);data=read_bytes(s,base,0x414f4)
 assert data[:4]==bytes.fromhex('000003f3'),data[:32].hex()
 (s.out/'main.hunk').write_bytes(data)
 (s.out/'capture.json').write_text(json.dumps(dict(base=hex(base),registers=s.cmd('info registers'),provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n')
 print('captured original unpacked hunk',hex(base),len(data),flush=True)
finally:s.quit()
