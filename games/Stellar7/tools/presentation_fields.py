#!/usr/bin/env python3
"""Read-only beam timestamps for native rendering and presentation scopes.

Uses breakpoints on an exact retained SIM60 build. Durations include interrupts;
scopes overlap and cannot be added. Partial calls are excluded. VBL epochs and
raw beam positions are retained; this is emulator timing, not hardware timing.
"""
import argparse
import json
import re
import socket
import struct
from pathlib import Path
import audit_hooks
from stellar7 import SOCK
from stellar7_report import regions

# Guard the first instruction at every native site before observing it.
SITES = {
    0x2bb4: ('draw_start', '33f9'), 0x6a0a: ('present_start', '4ef9'),
    0x2c1a: ('present_end', '2b79'), 0x2bec: ('actors_start', '4eba'),
    0x2bf0: ('actors_end', '4eba'), 0x1c8c0: ('copper_start', '4879'),
    0x1c8da: ('copper_end', '3039'), 0x1c976: ('loadview_start', '4879'),
    0x1c982: ('loadview_end', '4a47'), 0x1c986: ('handoff_start', '33fc'),
    0x1c996: ('handoff_end', '4eba'), 0x2510c: ('waitblit_start', '2f0e'),
    0x2511a: ('waitblit_end', '4e75'), 0x1db8c: ('polygon_wait_start', '0839'),
    0x1dbb2: ('polygon_wait_end', '4e75'),
}
SCOPES = {
    'draw_before_presentation': ('draw_start', 'present_start'),
    'presentation': ('present_start', 'present_end'),
    'actors': ('actors_start', 'actors_end'),
    'before_actors': ('draw_start', 'actors_start'),
    'after_actors': ('actors_end', 'present_start'),
    'copper_build': ('copper_start', 'copper_end'),
    'loadview': ('loadview_start', 'loadview_end'),
    'vbl_handoff': ('handoff_start', 'handoff_end'),
    'graphics_waitblit': ('waitblit_start', 'waitblit_end'),
    'polygon_wait': ('polygon_wait_start', 'polygon_wait_end'),
}


def command(script):
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(1800)
        connection.connect(SOCK)
        connection.sendall(('gdb '+script).encode())
        chunks=[]
        while chunk:=connection.recv(65536):chunks.append(chunk)
    result=b''.join(chunks).decode()
    if 'ERROR' in result:raise RuntimeError(result)
    return result


def capture(folder, listing, fields):
    folder,listing=Path(folder),Path(listing)
    meta=json.loads((folder/'metadata.json').read_text())
    memory=(folder/'code.bin').read_bytes();chip=(folder/'chip.bin').read_bytes()
    h,base,data=meta['code_base'],meta['base'],meta['data_base']
    audit_hooks.installed(folder,listing)
    known={name:origin for lo,hi,name,origin in regions(memory,base,chip)}
    vbl=known['kick']+0xfc0d4a
    for off,(name,expected) in SITES.items():
        assert memory[h-base+off:h-base+off+2]==bytes.fromhex(expected),name
    assert struct.unpack_from('>I',memory,data-base+0x6690)[0]==h+0x1c84c,'unexpected presentation callback'
    breaks='\n'.join(f'break *{h+off:#x}' for off in SITES)
    # Only debugger convenience variables change. Reading the beam does not
    # execute guest instructions or write custom registers.
    script=f'''break *{vbl:#x}
{breaks}
set $s7_epoch = -1
while $s7_epoch < {fields}
continue
if $pc == {vbl:#x}
set $s7_epoch = $s7_epoch + 1
end
printf "S7PHASE %d %u %u %u %u %u %u\\n", $s7_epoch, (unsigned int)$pc, *(unsigned int*)0xdff004, *(unsigned int*){data+0x24a8:#x}, *(unsigned short*){data+0x292a:#x}, *(unsigned short*){data+0x292c:#x}, *(unsigned short*){data+0x2946:#x}
end
delete
'''
    (folder/'presentation-observer.gdb').write_text(script)
    reply=command(script);(folder/'presentation-gdb.txt').write_text(reply)
    events=[]
    for row in re.findall(r'^S7PHASE (-?\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)$',reply,re.M):
        epoch,pc,beam,clock,back,front,request=map(int,row)
        if epoch<0 or epoch>=fields:continue
        events.append(dict(epoch=epoch,site='vbl' if pc==vbl else SITES[pc-h][0],
                           beam=beam,clock=clock,back=back,front=front,request=request))
    assert sum(e['site']=='vbl' for e in events)==fields,'incomplete field window'
    result=dict(fields=fields,field_hz=meta['field_hz'],events=events)
    (folder/'presentation-events.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture',type=Path);p.add_argument('--listing',type=Path,required=True)
    p.add_argument('--fields',type=int,default=100)
    a=p.parse_args();capture(a.capture,a.listing,a.fields)
