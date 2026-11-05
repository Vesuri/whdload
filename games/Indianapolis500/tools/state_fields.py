#!/usr/bin/env python3
"""Read hunk 0 at VBL or SOFT entry; never write game memory.
The game keeps its variables at absolute addresses inside hunk 0 itself (code and data
share the hunk), so a snapshot is a dump of hunk 0; offsets are game: hunk-0 offsets.
Run while i500 is stopped at the anchor. All dumps go through a space-free private /tmp
directory because the stub's gdb cannot quote dump file names.
  state_fields.py FIELDS OUTDIR CODE.bin BASE
STATE_AT=soft samples game:007ee and also dumps BSS hunks 1, 2, 5.
The initial dump is the frame anchor, not a SOFT sample.
"""
import argparse, json, os, shutil, socket, tempfile
from pathlib import Path
from i500 import SOCK
from i500_report import regions
from hunk_state import bss_regions

def command(s):
    with socket.socket(socket.AF_UNIX) as c:
        c.connect(SOCK); c.sendall(('gdb '+s).encode()); out = b''
        while chunk := c.recv(65536): out += chunk
    reply = out.decode()
    if 'ERROR' in reply: raise RuntimeError(reply)
    return reply

def main():
    p = argparse.ArgumentParser(); p.add_argument('fields', type=int)
    p.add_argument('out'); p.add_argument('dump'); p.add_argument('base', type=lambda x:int(x,0))
    a = p.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    rr={n:(lo,hi) for lo,hi,n,o in regions(Path(a.dump).read_bytes(),a.base)}
    hb, end=rr['game']
    mode=os.environ.get('STATE_AT','vbl')
    if mode not in ('vbl','soft'): p.error('STATE_AT must be vbl or soft')
    offset=0x7ee if mode=='soft' else 0xb29c
    blob=Path(a.dump).read_bytes()
    spans=bss_regions(blob,a.base,hb) if mode=='soft' else {}
    samples={'game':(hb,end), **spans}
    commands_initial='\n'.join(f'dump binary memory {{temp}}/initial{suffix}.bin {lo:#x} {hi:#x}' for name,(lo,hi) in samples.items() for suffix in ['' if name=='game' else '-'+name])
    commands_sample='\n'.join(f'eval "dump binary memory {{temp}}/%04d{suffix}.bin {lo:#x} {hi:#x}", $i500_sample' for name,(lo,hi) in samples.items() for suffix in ['' if name=='game' else '-'+name])
    with tempfile.TemporaryDirectory(prefix='i500-state-') as temp:
        text=command(f"""{commands_initial.format(temp=temp)}
break *{hb+offset:#x}
set $i500_sample = 0
while $i500_sample < {a.fields}
continue
{commands_sample.format(temp=temp)}
set $i500_sample = $i500_sample + 1
end
delete
""")
        (out/'gdb.txt').write_text(text)
        files=sorted(Path(temp).glob('*.bin'))
        expected=(a.fields+1)*len(samples)
        if len(files)!=expected: raise RuntimeError(f'{len(files)} dump files, expected {expected}')
        for f in files: shutil.move(str(f),out/f.name)
    (out/'metadata.json').write_text(json.dumps(dict(code_base=hb,fields=a.fields,sample_at=mode,anchor=f'game:{offset:05x} entry',regions={n:[lo,hi] for n,(lo,hi) in samples.items()}),indent=2)+'\n')
    print(f'{a.fields} {mode} snapshots (hunk 0 plus {len(spans)} BSS hunks): {out}')
if __name__=='__main__': main()
