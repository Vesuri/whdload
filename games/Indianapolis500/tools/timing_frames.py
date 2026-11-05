#!/usr/bin/env python3
"""Read private TIMING-build elapsed intervals; no game state is modified."""
import argparse,json,struct,statistics
from pathlib import Path
from state_fields import command
from i500_report import regions
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('frames',type=int);p.add_argument('out',type=Path)
p.add_argument('dump',type=Path);p.add_argument('base',type=lambda s:int(s,0));a=p.parse_args()
assert 1<=a.frames<=64
b=a.dump.read_bytes();rr={n:(lo,hi) for lo,hi,n,o in regions(b,a.base)}
lo,hi=rr['slave'];offset=b.find(b'I5TM',lo-a.base,hi-a.base);assert offset>=0,'TIMING build required'
magic=a.base+offset;g=rr['game'][0];a.out.mkdir(parents=True,exist_ok=True)
# Dump inside the same debugger command so no resumed frames enter the sample.
import tempfile,shutil
with tempfile.TemporaryDirectory(prefix='i500-timing-') as temporary:
 f=Path(temporary)/'timing.bin'
 reply=command(f'''printf "I500TIME before %u\\n", *(unsigned int *){magic+4:#x}
break *{g+0xb57e:#x}
while *(unsigned int *){magic+4:#x} < {a.frames}
continue
end
delete
dump binary memory {f} {magic:#x} {magic+392:#x}
''')
 (a.out/'timing-gdb.txt').write_text(reply)
 data=f.read_bytes();shutil.move(str(f),a.out/'timing.bin')
count=struct.unpack_from('>I',data,4)[0];assert count==a.frames, 'capture passed the requested endpoint'
units=list(struct.unpack_from(f'>{count}I',data,8))
directors=list(struct.unpack_from(f'>{count}H',data,264))
assert all(200<=x<300 for x in directors), 'timing includes another demo view'
assert all(0<x<709379 for x in units),'invalid elapsed CIA time'
ms=[x*1000/709379 for x in units]
result=dict(frames=count,directors=directors,milliseconds=ms,median=statistics.median(ms),minimum=min(ms),maximum=max(ms),under_40ms=sum(x<=40 for x in ms))
(a.out/'timing.json').write_text(json.dumps(result,indent=2)+'\n')
print(f'{count} instrumented active intervals: {min(ms):.2f}–{max(ms):.2f} ms, median {statistics.median(ms):.2f} ms')
