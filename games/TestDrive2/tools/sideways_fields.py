#!/usr/bin/env python3
"""Read-only sideways capture: per completed main view, the drawn and raw heading/lane
and the main rows; per backdrop computation, d2 and its inputs. Used by fixed_window.sh
via SIDEWAYS_FRAMES; SIDEWAYS_RECOVERY=1 also records recovery state and dumps the data
hunk at the first 1000 VBL entries (OUT/../state, as state_fields.py).
  sideways_fields.py FRAMES OUT CODE.bin BASE [--recovery]
Records in OUT/gdb.txt (see tools/sideways_report.py):
  BD d2 curve_sum heading camera_segment camera_fraction field summed_segment
  RW frame field drawn_heading/4 drawn_lane raw_heading drawn_lane.l raw_lane.l
  REC frame field recovery_flag damage_timer player_position race_clock
Main rows (44 x 52 bytes from -5702(a4); x at +10, y at +12) go to OUT/rNNNN.bin.
"""
import argparse, json, shutil, tempfile
from pathlib import Path
from state_fields import command
from td2_report import regions

p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('frames',type=int);p.add_argument('out',type=Path)
p.add_argument('dump',type=Path);p.add_argument('base',type=lambda x:int(x,0))
p.add_argument('--recovery',action='store_true')
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
rr={n:lo for lo,hi,n,o in regions(a.dump.read_bytes(),a.base)}
hb,db=rr['duel'],rr['duel-data'];av=db+0x7ffe;end=db+0x7a70;rows=av-5702
clock=f'*(unsigned int*){av-17216:#x}-$e'
state=a.out.parent/'state'
with tempfile.TemporaryDirectory(prefix='td2-sideways-') as temp:
    lines=['set $n = 0','set $field = 0',f'set $e = *(unsigned int*){av-17216:#x}',
           f'break *{hb+0x8c9e:#x}',f'break *{hb+0x6c74:#x}']
    if a.recovery:
        lines=[f'dump binary memory {temp}/initial.bin {db:#x} {end:#x}']+lines+[f'break *{hb+0x231c:#x}',
               f'while $n < {a.frames} || $field < 1000','continue',
               f'if $pc == {hb+0x231c:#x} && $field < 1000',f'eval "dump binary memory {temp}/s%04d.bin {db:#x} {end:#x}", $field','set $field = $field + 1','end']
    else:
        lines+=[f'while $n < {a.frames}','continue']
    lines+=[f'if $pc == {hb+0x8c9e:#x} && $n < {a.frames}',
            f'printf "BD %d %u %d %d %d %u %d\\n", (short)$d2, *(unsigned int*){av-13398:#x}, *(short*){av-13390:#x}, *(short*){av-13394:#x}, *(unsigned short*){av-13392:#x}, {clock}, *(short*){av-17234:#x}','end',
            f'if $pc == {hb+0x6c74:#x} && $n < {a.frames}',
            f'eval "dump binary memory {temp}/r%04d.bin {rows:#x} {rows+44*52:#x}", $n',
            f'printf "RW %d %u %d %d %d %d %d\\n", $n, {clock}, *(short*){av-13388:#x}, *(short*){av-13382:#x}, *(short*){av-13390:#x}, *(int*){av-13382:#x}, *(int*){av-13386:#x}']
    if a.recovery:
        lines.append(f'printf "REC %d %u %d %d %u %u\\n", $n, {clock}, *(short*){av-14916:#x}, *(short*){av-12938:#x}, *(unsigned int*){av-17238:#x}, *(unsigned int*){av-10864:#x}')
    lines+=['set $n = $n + 1','end','end','delete']
    (a.out/'gdb.txt').write_text(command('\n'.join(lines)+'\n'))
    for f in Path(temp).glob('r*.bin'):shutil.move(str(f),a.out/f.name)
    if a.recovery:
        state.mkdir(exist_ok=True)
        for f in Path(temp).glob('s*.bin'):shutil.move(str(f),state/f.name[1:])
        shutil.move(str(Path(temp)/'initial.bin'),state/'initial.bin')
        (state/'metadata.json').write_text(json.dumps(dict(code_base=hb,data_base=db,a4=av,fields=1000),indent=2)+'\n')
print(f'{a.out}: {len(list(a.out.glob("r*.bin")))} completed main views')
