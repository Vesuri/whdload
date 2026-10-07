#!/usr/bin/env python3
"""Read LoV world state at successive VBL counter increments; never write guest memory.
Used by fixed_window.sh STATE_FIELDS with the emulator stopped at the tape anchor.
"""
import argparse, json, os, shutil, socket, tempfile
from pathlib import Path
from lov import SOCK
from lov_report import regions
from lov_timing_state import decode

def command(s):
    with socket.socket(socket.AF_UNIX) as c:
        c.connect(SOCK);c.sendall(('gdb '+s).encode());chunks=[]
        while chunk:=c.recv(65536):chunks.append(chunk)
    reply=b''.join(chunks).decode()
    if 'ERROR' in reply:raise RuntimeError(reply)
    return reply

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('fields',type=int)
    p.add_argument('out',type=Path);p.add_argument('capture',type=Path)
    p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('--initial-point', default='VERIFY tape anchor after VBL counter increment')
    a=p.parse_args()
    if a.fields < 1:p.error('fields must be positive')
    os.environ['SLAVE']=str(a.capture/'slave.slave')
    rr={n:lo for lo,hi,n,o in regions((a.capture/'code.bin').read_bytes(),a.base)}
    h11,h12=rr['h11'],rr['h12'];a.out.mkdir(parents=True,exist_ok=True)
    spans=[('active-clock',h11+0x4d6,h11+0x4da),('clock',h11+0x6000,h11+0x6030),('player',h11+0x8c00,h11+0x8c44),
           ('animation',h11+0xdf0,h11+0xe00),('world',h12+0x9700,h12+0xdef0),
           ('periodic',h12+0x27ba,h12+0x27bc)]
    samples=[]
    with tempfile.TemporaryDirectory(prefix='lov-timing-') as temp:
        # The anchor is inside VBL, after its counter increment. Subsequent samples
        # stop immediately after the next increment, giving exactly N counter fields.
        lines=[f'break *{h12+0x640a:#x}'];lines+=['set $lov_sample = 0']
        lines+=[f'while $lov_sample <= {a.fields}']
        lines+=['if $lov_sample > 0','continue','end']
        for label,lo,hi in spans:
            lines.append(f'eval "dump binary memory {temp}/%04d-{label}.bin {lo:#x} {hi:#x}", $lov_sample')
        lines+=['set $lov_sample = $lov_sample + 1','end','delete $bpnum']
        (a.out/'gdb.txt').write_text(command('\n'.join(lines)))
        for i in range(a.fields+1):
            parts=[(lo,hi,Path(temp,f'{i:04d}-{label}.bin').read_bytes()) for label,lo,hi in spans]
            def read(at,n):
                for lo,hi,b in parts:
                    if lo<=at and at+n<=hi:return b[at-lo:at-lo+n]
                raise ValueError(f'unmapped state address {at:#x}')
            samples.append(decode(read,h11,h12))
        for f in Path(temp).glob('*.bin'):shutil.move(str(f),a.out/f.name)
    (a.out/'samples.json').write_text(json.dumps(samples,indent=2)+'\n')
    (a.out/'metadata.json').write_text(json.dumps(dict(h11=h11,h12=h12,fields=a.fields,
        initial_sample_point=a.initial_point,
        subsequent_sample_point='h12:0640a after VBL counter increment',
        elapsed_counter_fields=(samples[-1]['field']-samples[0]['field']) & 0xffffffff),indent=2)+'\n')
    print(f'{len(samples)} persistent-world samples retained in {a.out}')
if __name__=='__main__':main()
