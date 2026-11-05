#!/usr/bin/env python3
"""Verify optional patch ranges against local Disk.1, accounting for relocation."""
import argparse,re,struct
from pathlib import Path
from i500_report import regions,game_hunks,DISK
from hunk_state import hunk0_relocations,bss_regions
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('capture',type=Path)
p.add_argument('--base',type=lambda s:int(s,0),default=0xc00000)
a=p.parse_args()
mem=(a.capture/'code.bin').read_bytes()
g=next(lo for lo,hi,name,o in regions(mem,a.base) if name=='game')
disk=Path(DISK).read_bytes(); start,relocs=hunk0_relocations(disk)
expected=bytearray(disk[start:start+game_hunks(disk)[0][3]])
targets={0:g}
targets.update({int(name[4:]):lo for name,(lo,hi) in bss_regions(mem,a.base,g).items()})
for lo,hi,name,o in regions(mem,a.base):
    if name.startswith('hunk'):targets[int(name[4:])]=lo
for off,target in relocs:
    # Chip DATA hunks may not be in code.bin; a disabled range referencing one
    # must fail explicitly rather than silently comparing unrelocated bytes.
    if target in targets:
        value=struct.unpack_from('>I',expected,off)[0]
        struct.pack_into('>I',expected,off,(value+targets[target])&0xffffffff)
source=(Path(__file__).resolve().parents[1]/'src/Indianapolis500_WHD.s').read_bytes().decode('latin1')
active=False;cases=0
for line in source.splitlines():
    if re.match(r'PL_(MOTION|SPANS)\s+PL_START',line.strip()): active=True
    if re.fullmatch(r'PL_END',line.strip()): active=False
    if not active: continue
    m=re.search(r'PL_(W|L|PSS|PS|P|NOP)\s+\$([0-9a-f]+),([^;]+)',line,re.I)
    if not m: continue
    kind,off,args=m.groups();off=int(off,16)
    size={'W':2,'L':4,'PS':6,'P':6}.get(kind)
    if kind=='PSS':size=6+int(args.split(',')[1],0)
    if kind=='NOP':size=int(args.strip(),0)
    assert not any(target not in targets and off<=ref<off+size for ref,target in relocs),'range references an uncaptured hunk'
    assert mem[g-a.base+off:g-a.base+off+size]==expected[off:off+size],f'optional patch active at game:{off:05x}'
    cases+=1
assert cases,'no optional ranges found'
assert bss_regions(mem,a.base,g)['hunk2'][1] == 0x80000, 'optional chip cache reservation active'
print(f'{cases} disabled optional patch ranges retain original bytes; original chip-pool limit retained')
