"""Thirty emulated minutes of uninterrupted flight; no guest instrumentation."""
import json,re,sys
from pathlib import Path
import route_status as r
out=Path(sys.argv[1]);sim=json.loads((out/'sim.json').read_text())['sim'];fields=90000
cmd=['delete','set $field=0',f'break *{sim+0x21f4a:#x}','commands','silent','printf "FLIGHT_EXIT %u\\n", $field','end',f'break *{sim+0x2d34e:#x}','commands','silent','set $field=$field+1',f'if $field < {fields}','continue','end','end','continue','printf "SOAK %u\\n", $field','delete']
raw=r.command('gdb '+'\n'.join(cmd));(out/'soak.log').write_text(raw)
assert 'FLIGHT_EXIT' not in raw and re.search(r'SOAK 90000\b',raw),raw[-2000:]
(out/'soak.json').write_text(json.dumps(dict(fields=fields,seconds=fields/49.92041,scope='Uninterrupted protected flight at maximum detail; emulated PAL duration, not host wall time'),indent=2)+'\n')
print('30-MINUTE SOAK PASS',flush=True)
