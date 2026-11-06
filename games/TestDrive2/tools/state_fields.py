#!/usr/bin/env python3
"""Read duel v1's data hunk at successive VBL entries; never write game memory.
Run while td2 is stopped at the race anchor. All dumps go through a space-free
private /tmp directory because the stub's gdb cannot quote dump file names.
  state_fields.py FIELDS OUTDIR CODE.bin BASE
The first snapshot precedes field 0; subsequent snapshots are at VBL-server entry.
"""
import argparse, json, os, shutil, socket, struct, tempfile
from pathlib import Path
from td2 import SOCK
from td2_report import regions

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
    rr={n:lo for lo,hi,n,o in regions(Path(a.dump).read_bytes(),a.base)}
    hb, db=rr['duel'],rr['duel-data']; end=db+0x7a70
    with tempfile.TemporaryDirectory(prefix='td2-state-') as temp:
        text=command(f"""dump binary memory {temp}/initial.bin {db:#x} {end:#x}
break *{hb+0x231c:#x}
set $td2_sample = 0
while $td2_sample < {a.fields}
continue
eval "dump binary memory {temp}/%04d.bin {db:#x} {end:#x}", $td2_sample
set $td2_sample = $td2_sample + 1
end
delete
""")
        (out/'gdb.txt').write_text(text)
        files=sorted(Path(temp).glob('*.bin'))
        if len(files)!=a.fields+1: raise RuntimeError(f'{len(files)} snapshots, expected {a.fields+1}')
        for f in files: shutil.move(str(f),out/f.name)
    (out/'metadata.json').write_text(json.dumps(dict(code_base=hb,data_base=db,a4=db+0x7ffe,fields=a.fields,anchor='duel:0231c entry'),indent=2)+'\n')
    print(f'{a.fields} field snapshots: {out}')
if __name__=='__main__': main()
