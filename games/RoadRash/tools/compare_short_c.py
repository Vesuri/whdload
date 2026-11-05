import json,sys
from pathlib import Path
ref,run=map(Path,sys.argv[1:3]);a=json.loads((ref/'step.json').read_text());b=json.loads((run/'step.json').read_text());n=min(a['steps'],b['steps'])-1
assert (ref/'hashes.bin').read_bytes()[4:(n+1)*4]==(run/'hashes.bin').read_bytes()[4:(n+1)*4]
assert a['sound_events']==b['sound_events']
x=(ref/'step1457.bin').read_bytes();y=(run/'step1457.bin').read_bytes()
for addr,size in [(0xa5d60,0x1180),(0xa5d50,16),(0xa5d1e,4),(0xa5d22,4),(0xa7220,8),(0xa59f4,2)]:assert x[addr-0xa5900:addr-0xa5900+size]==y[addr-0xa5900:addr-0xa5900+size],hex(addr)
r=dict(reference=str(ref),common_hashes=n,sounds_equal=True,six_regions_equal=True)
(run/'comparison.json').write_text(json.dumps(r,indent=2));print(r)
