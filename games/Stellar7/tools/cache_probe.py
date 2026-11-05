#!/usr/bin/env python3
"""Build/read a scratch-only CACR probe; no playable source or cache policy changes.

The probe has timing overhead and is for functional cache observations only.
Run its retained VERIFY binary with fixed_window --prebuilt, CUSTOM1=1, through
completed tick 200. The 68000 path must report unsupported without executing MOVEC.
"""
import argparse
import json
import os
import re
import struct
import subprocess
from pathlib import Path
from stellar7_report import locate
ROOT=Path(__file__).resolve().parent.parent


def build(prefix, substeps):
    prefix=prefix.resolve();prefix.relative_to(ROOT/'tmp');prefix.parent.mkdir(parents=True,exist_ok=True)
    relative=lambda p:os.path.relpath(p,ROOT/'whdload')
    source=(ROOT/'whdload/Stellar7.s').read_text()
    assert source.count('jsr (resload_SetCPU,a2)')==1
    source=source.replace('jsr (resload_SetCPU,a2)','jsr (resload_SetCPU,a2)\n        bsr cache_probe_boot')
    simulation=(ROOT/'whdload/sim60.s').read_text().replace('s60_loop_complete:\n','s60_loop_complete:\n        bsr cache_probe_tick\n')
    sim=prefix.with_suffix('.sim.s');sim.write_text(simulation)
    source=source.replace('INCLUDE sim60.s',f'INCLUDE "{relative(sim)}"')
    source+='\n        INCLUDE "../tools/cache_probe.s"\n'
    src=prefix.with_suffix('.s');src.write_text(source)
    cmd=[os.environ['VASM'],'-m68000','-pic','-x','-devpac','-Fhunkexe','-nosym','-DSIM60=1','-DVERIFY=1',f'-DS60_SUBSTEPS={substeps}', '-I.','-Iinclude','-I'+os.environ['WHDLOAD']+'/Include','-I'+os.environ['WHDLOAD']+'/Src/sources','-I'+os.environ['NDK'],'-L',relative(prefix.with_suffix('.lst')),'-o',relative(prefix.with_suffix('.slave')),relative(src)]
    with prefix.with_suffix('.log').open('w') as log:subprocess.run(cmd,cwd=ROOT/'whdload',stdout=log,stderr=subprocess.STDOUT,check=True)


def read(folder,listing):
    folder,listing=Path(folder),Path(listing)
    binary=(folder/'slave.slave').read_bytes();assert binary==listing.with_suffix('.slave').read_bytes()
    meta=json.loads((folder/'metadata.json').read_text());memory=(folder/'code.bin').read_bytes()
    size=struct.unpack_from('>I',binary,28)[0]*4
    origin=locate(memory,binary[32:32+size],meta['base'],header=32);assert origin is not None
    offset=int(re.search(r'^cache_probe_record\s+00:([0-9A-F]+)',listing.read_text(encoding='latin1'),re.M)[1],16)
    at=origin-meta['base']+offset;assert memory[at:at+4]==b'CA60'
    version,count,attn,supported,boot,game=struct.unpack_from('>4H2I',memory,at+4)
    assert version==1 and supported==bool(attn&2)
    assert (count==2) if supported else (count==0 and boot==game==0xffffffff)
    return dict(cpu=meta['cpu'],attn_flags=hex(attn),supported=bool(supported),observations=count,after_setcpu=hex(boot) if supported else None,gameplay_tick_200=hex(game) if supported else None,scope='Diagnostic build; Supervisor executes only MOVEC CACR,D0 and RTE. No performance inference from probe timing.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    b=sub.add_parser('build');b.add_argument('prefix',type=Path);b.add_argument('--substeps',type=int,choices=(3,12),default=12)
    r=sub.add_parser('read');r.add_argument('capture',type=Path);r.add_argument('--listing',type=Path,required=True)
    a=p.parse_args()
    if a.command=='build':build(a.prefix,a.substeps)
    else:print(json.dumps(read(a.capture,a.listing),indent=2))
