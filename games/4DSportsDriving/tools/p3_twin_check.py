import json,struct,sys
from profile_window import command,ROOT
from pathlib import Path
p=Path(sys.argv[1]);b=(p/'memory.bin').read_bytes();at=b.index(b'4DSPANTW');m=json.loads((p/'anchor.json').read_text());addr=m['memory_base']+at+8
# Finish the current frame before reading live counters; memory.bin is only the anchor.
command(f'gdb delete\ntbreak *{m["game_base"]+0x7500:#x}\ncontinue')
live=p.resolve()/'span-twin-live.bin'
command(f'gdb dump binary memory {live.relative_to(ROOT)} {addr:#x} {addr+16:#x}')
passed,failed,active,kind,buffer=struct.unpack('>IIHHI',live.read_bytes())
r={'passed':passed,'failed':failed,'active':active,'buffer':buffer,'scope':'same-input solid/two-colour span twins, full 32000-byte bitmap'}
(p/'span-twin.json').write_text(json.dumps(r,indent=2)+'\n');print(r);assert passed>=100 and failed==0 and active==0
