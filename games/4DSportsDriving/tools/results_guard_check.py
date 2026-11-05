#!/usr/bin/env python3
"""Inspect installed native result guards using terminal source-owned fixtures."""
import argparse,json,re,struct
from pathlib import Path
from profile_window import command,ROOT
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--case',type=int,choices=range(5,9),required=True);p.add_argument('--at-stop',action='store_true');a=p.parse_args();cap=a.capture.resolve();meta=json.loads((cap/'anchor.json').read_text());off={5:0x56b8,6:0x5728,7:0x5842,8:0x5850}[a.case];at=meta['game_base']+off
out=command('gdb info registers pc sp d0 sr' if a.at_stop else f'gdb delete\ntbreak *{at:#x}\ncontinue\ninfo registers pc sp d0 sr');print(out,flush=True)
def reg(n):return int(re.search(r'^'+n+r'\s+0x([0-9a-f]+)',out,re.M)[1],16)
assert reg('pc')==at
path=cap/'guard-memory.bin';command(f'gdb dump binary memory {path.relative_to(ROOT)} 0x200000 0x600000');b=path.read_bytes();buf=b.index(b'4DRFMTFX')+8;initial_sp=struct.unpack_from('>I',b,buf+16)[0];actual_sp=reg('sp');assert actual_sp==initial_sp+({6:12}.get(a.case,0)),(initial_sp,actual_sp)
result={'case':a.case,'pc_offset':hex(off),'stack_delta':actual_sp-initial_sp,'ccr':reg('sr')&31}
if a.case==5:
 text=b[buf:buf+16].split(b'\0',1)[0].decode();assert text=='21:50.72',text;assert b[buf+15]==0x5a;result['text']=text;result['guard_intact']=True
else:
 # Remote SR is diagnostic only; actual Scc/ADDX selftests verify flags.
 assert reg('d0')== (65536 if a.case==8 else 65535)
if a.case==6:
 out=command(f'gdb delete\ntbreak *{meta["game_base"]+0x572a:#x}\ntbreak *{meta["game_base"]+0x5786:#x}\ncontinue\ninfo registers pc');assert reg('pc')==meta['game_base']+0x572a;result['nonzero_penalty_branch']=hex(0x572a)
if a.case==8:
 out=command(f'gdb delete\ntbreak *{meta["game_base"]+0x5892:#x}\ntbreak *{meta["game_base"]+0x5852:#x}\ncontinue\ninfo registers pc');assert reg('pc')==meta['game_base']+0x5892;result['unsigned_winner_branch']=hex(0x5892)
(cap/'guard-check.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
