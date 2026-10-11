#!/usr/bin/env python3
"""Native weather state schema and read-only GDB probe builder.

Snapshot summaries locate calibration material; they do not prove duration/cadence.
The capture tool emits this schema at matching TIMING_STATE probe boundaries.
"""
import argparse
import json
from pathlib import Path
import struct

# name, address domain, byte offset, width
FIELDS=(
    ('clock','game',0xf96,4), ('vbl','game',0x48fe,4),
    ('loop','state',0x5e,4), ('rng','state',0x62,2),
    ('mode_b6','state',0xb6,2), ('track','state',0x118,2),
    ('gate_104','state',0x104,2), ('forecast_deadline','state',0x4bc,4),
    ('active_deadline','state',0x4b8,4), ('forecast_flag','state',0x4c0,2),
    ('transition','state',0x4c6,2), ('steering_x','state',0x4c2,2),
    ('steering_y','state',0x4c4,2), ('effects_enabled','state',0x4cc,2),
    ('effect_lifetime','state',0x4ce,2), ('palette_active','state',0x4d0,2),
    ('effect_delay','state',0x4d2,2), ('gear','state',0x44e,2),
    ('target_gear','state',0x450,2), ('view_aa','state',0xaa,2),
)
REGISTERS=('d0','d1','d7','sp')
# Exact native instruction boundaries: eligibility, deadline arithmetic/commits,
# fade mutations, generation and effect drawing. No target memory is changed.
PROBES=(0xdd14,0xdd2c,0xdd36,0xdd40,0xddf8,
        0xe1a2,0xe1ca,0xe1d4,0xe1f8,0xe200,0xe23c,0xe242,0xe246,0xe25c,
        0xe25e,0xe278,0xe294,0xbcaa,0xbcea,0xbd02,0xbd16,0xbd1a,
        0xbd32,0xbd36,0xbd48,0xbd4c,0x8a4c,0x8a5e,0x8a8e,0x8aa0,
        0x112e6,0x112f0,0x112f4,0x112fa,0x11300)


def address(game,domain,offset):
    assert domain in ('game','state')
    return game+(0xa6e if domain=='state' else 0)+offset


def probe_command(game,offset):
    assert offset in PROBES
    values=[f'*(unsigned {"int" if width==4 else "short"}*){address(game,domain,off):#x}'
            for _,domain,off,width in FIELDS]
    values += [f'(unsigned int)${reg}' for reg in REGISTERS]
    return ('printf "PDWEATHER_EVENT %d '+hex(offset)+' '+' '.join(['%u']*len(values))+
            '\\n", $pd_field, '+', '.join(values)+'\n')


def snapshot(data,game):
    return {name:struct.unpack_from('>I' if width==4 else '>H',data,address(game,domain,off))[0]
            for name,domain,off,width in FIELDS}


def parse_values(values):
    values=list(map(int,values.split()))
    names=[field[0] for field in FIELDS]+list(REGISTERS)
    assert len(values)==len(names), 'Weather probe schema mismatch'
    return dict(zip(names,values))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('captures',type=Path,nargs='+')
    for root in p.parse_args().captures:
        game=int((root/'game-base.txt').read_text(),0)
        result={name:snapshot((root/file).read_bytes(),game)
                for name,file in (('initial','chip.bin'),('final','final-chip.bin'))}
        print(json.dumps({'capture':root.name,**result},indent=2))
