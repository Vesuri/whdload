#!/usr/bin/env python3
"""Read completed main/mirror row and scanline records and drawn car coordinates.
Used by fixed_window.sh via RENDER_FRAMES; debugger writes only convenience values.
"""
import argparse, json, shutil, tempfile
from pathlib import Path
from state_fields import command
from td2_report import regions

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('frames',type=int);p.add_argument('out',type=Path)
p.add_argument('dump',type=Path);p.add_argument('base',type=lambda x:int(x,0))
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
rr={n:lo for lo,hi,n,o in regions(a.dump.read_bytes(),a.base)}
hb,db=rr['duel'],rr['duel-data'];av=db+0x7ffe
mem=a.dump.read_bytes();slo=rr['slave']-a.base
latch=mem.find(bytes.fromhex('296ccbfacbca48e78080'),slo)
assert latch>=0,'sub-unit latch not found'
lea=latch+10
assert mem[lea:lea+2]==bytes.fromhex('41fa')
fractions=a.base+lea+2+int.from_bytes(mem[lea+2:lea+4],'big',signed=True)
traffic_fractions=(fractions,fractions+2) if mem[hb-a.base+0x6474:hb-a.base+0x647a]!=bytes.fromhex('296ccbfacbca') else (av-13468,av-13464)
with tempfile.TemporaryDirectory(prefix='td2-render-') as temp:
    lines=['set $td2_main = 0','set $td2_mirror = 0',f'set $td2_epoch = *(unsigned int*){av-17216:#x}']
    for off in (0x6c74,0x6dbc,0x7a3a,0x7a7e,0x8020,0x8058):lines.append(f'break *{hb+off:#x}')
    lines += [f'while $td2_mirror < {a.frames}','continue',f'if $pc == {hb+0x6c74:#x} && $td2_main == 0',f'dump binary memory {temp}/assets.bin {a.base:#x} {a.base+len(mem):#x}','end']
    for off,view in ((0x6c74,'main'),(0x6dbc,'mirror')):
        lines += [f'if $pc == {hb+off:#x}',f'eval "dump binary memory {temp}/{view}-%04d.bin {db:#x} {db+0x7a70:#x}", $td2_{view}',f'printf "TD2ROW {view} %d %u\\n", $td2_{view}, *(unsigned int*){av-17216:#x}-$td2_epoch',f'set $td2_{view} = $td2_{view} + 1','end']
    for off,kind,frac in ((0x7a3a,'forward',traffic_fractions[0]),(0x7a7e,'oncoming',traffic_fractions[1]),(0x8020,'opponent',av-13372),(0x8058,'police',av-13364)):
        source='*(unsigned int*)($a0+4)' if kind in ('forward','oncoming') else '0'
        lines += [f'if $pc == {hb+off:#x}',f'printf "TD2CAR {kind} %u %u %u %d %d %d %u %u %u\\n", *(unsigned int*){av-17216:#x}-$td2_epoch, *(unsigned short*){av-14792:#x}, $d7&65535, (short)$d0, (short)$d1, *(short*)($a3+46), *(unsigned int*){av-13394:#x}, *(unsigned short*){frac:#x}, {source}','end']
    lines += ['end','delete']
    output=command('\n'.join(lines)+'\n')
    (a.out/'gdb.txt').write_text(output)
    files=list(Path(temp).glob('*.bin'))
    completed={view:sum(f.name.startswith(view+'-') for f in files) for view in ('main','mirror')}
    for f in files:shutil.move(str(f),a.out/f.name)
(a.out/'metadata.json').write_text(json.dumps(dict(code_base=hb,data_base=db,a4=av,frames=a.frames,completed=completed,assets_base=a.base),indent=2)+'\n')
print(f'{completed["main"]} main / {completed["mirror"]} mirror completed frames: {a.out}')
