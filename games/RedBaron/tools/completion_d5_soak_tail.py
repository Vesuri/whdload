"""Finish the same D5 soak after the debugger response deadline, without reboot."""
import json,re,sys
from pathlib import Path
sys.path.insert(0,'tools')
import route_status as r
out=Path('tmp/prof/completion-d5-060-input-soak')
sim=json.loads((out/'sim.json').read_text())['sim']
first=(out/'soak.log').read_text();match=re.search(r'SOAK (\d+)',first);assert match
already=int(match[1]);remaining=90000-already;assert 0<remaining<90000
cmd=['delete',f'break *{sim+0x21f4a:#x}','commands','silent','printf "FLIGHT_EXIT\\n"','end',f'break *{sim+0x2d34e:#x}',f'ignore $bpnum {remaining-1}','continue','printf "SOAK_TAIL_COMPLETE\\n"','delete']
# The timed-out response left one prior sentinel in the server buffer.
old=r.command('gdb '+'\n'.join(cmd));assert 'D5_SOAK_DRAIN' in old,old
raw=r.command('gdb echo D5_SOAK_FINISHED\\n');(out/'soak-tail.log').write_text(raw)
assert 'FLIGHT_EXIT' not in raw and 'SOAK_TAIL_COMPLETE' in raw,raw
# Confirm the stop was the requested native VBL, not a fault or other anchor.
assert f'{sim+0x2d34e:x}' in raw.lower(),raw
(out/'soak.json').write_text(json.dumps(dict(fields=90000,seconds=90000/49.92041,segments=[already,remaining],scope='Same protected max-detail flight; debugger timeout interrupted the host after the first segment; no guest reset or input between segments'),indent=2)+'\n')
print('30-MINUTE SOAK PASS',flush=True)
