import json,struct,sys
from pathlib import Path
from profile_window import command,ROOT
p=Path(sys.argv[1]);b=(p/'memory.bin').read_bytes();m=json.loads((p/'anchor.json').read_text());at=b.index(b'4DFRAMTW');addr=m['memory_base']+at+8
command(f'gdb delete\ntbreak *{m["game_base"]+0x7500:#x}\ncontinue')
live=p.resolve()/'frame-twin-live.bin';command(f'gdb dump binary memory {live.relative_to(ROOT)} {addr:#x} {addr+10:#x}');passed,failed,phase=struct.unpack('>IIH',live.read_bytes());r={'passed':passed,'failed':failed,'phase':phase,'bytes_per_frame':32000};(p/'frame-twin.json').write_text(json.dumps(r,indent=2)+'\n');print(r);assert passed>=10 and failed==phase==0
