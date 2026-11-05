#!/usr/bin/env python3
"""Inspect terminal synthetic result-call fixtures at native formatter returns."""
import argparse,json,re,struct
from pathlib import Path
from profile_window import command,ROOT
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--case',type=int,choices=range(1,5),required=True);a=p.parse_args();cap=a.capture.resolve();meta=json.loads((cap/'anchor.json').read_text());offset=(0x56b8,0x5752,0x587a,0x58ba)[a.case-1];at=meta['game_base']+offset
out=command(f'gdb delete\ntbreak *{at:#x}\ncontinue\ninfo registers pc');print(out,flush=True);assert int(re.search(r'^pc\s+0x([0-9a-f]+)',out,re.M)[1],16)==at
path=cap/'formatted-memory.bin';command(f'gdb dump binary memory {path.relative_to(ROOT)} 0x200000 0x600000');b=path.read_bytes();buffer=b.index(b'4DRFMTFX')+8;value=b[buffer:buffer+16].split(b'\0',1)[0].decode();expected=('25:00.00','1638:21.00','65536:00.00','65536:00.00')[a.case-1];assert value==expected,(value,expected);assert b[buffer+15]==0x5a
result={'case':a.case,'native_return_offset':hex(offset),'text':value,'guard_intact':True};(cap/'format-check.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
