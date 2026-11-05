"""Check instruction spans and all four-channel stale-snapshot request cases."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1];data=root/'tmp/game/GrandPrixCircuit_v1.0_0008/GrandPrixCircuit/data'
codes=[(data/('song'+str(n))).read_bytes()[40:40+0xb80] for n in (1,2,3)]
assert codes[0]==codes[1]==codes[2]
g=codes[0]
assert g[0x8c6:0x8ca]==bytes.fromhex('0300675c')
assert g[0x926:0x92e]==bytes.fromhex('33c300dff09c4e75')
assert 0x8ca+0x62==0x92c
# Every request missing from the entry snapshot must survive a handler pass,
# regardless of which channel is currently being serviced when it arrives.
cases=lost=0
for snapshot in range(16):
 for arrived in range(16):
  for arrival_before_channel in range(4):
   native=snapshot;fixed=snapshot
   for channel in range(4):
    if channel==arrival_before_channel:native|=arrived;fixed|=arrived
    bit=1<<channel
    native &= ~bit
    if snapshot&bit:fixed &= ~bit
   required=arrived&~snapshot
   assert fixed&required==required
   lost+=bool((native&required)!=required);cases+=1
report=dict(driver_sha256=hashlib.sha256(g).hexdigest(),identical_drivers=['song1','song2','song3'],branch_target='song:$92c RTS',cases=cases,native_loses_unsampled_request_cases=lost,fixed_preserves_all_unsampled_requests=True,scope='Instruction-span and interrupt-mask model; physical missing-note resolution still needs confirmation.')
(root/'tmp/phase8/music-model.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
