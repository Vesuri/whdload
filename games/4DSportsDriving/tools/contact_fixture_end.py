#!/usr/bin/env python3
"""After a contact trace, enter the next update to save the final fixture sample."""
import json,sys
from pathlib import Path
from profile_window import command,ROOT
from simulation_fixture import read_fixture
p=Path(sys.argv[1]).resolve();m=json.loads((p/'anchor.json').read_text())
out=command(f'until {m["game_base"]+0xe5f8:#x}');(p/'contact-end-checkpoint.txt').write_text(out)
command(f'gdb dump binary memory {p.relative_to(ROOT)}/contact-end.bin {m["memory_base"]:#x} {m["memory_base"]+m["memory_size"]:#x}')
r=read_fixture(p,'contact-end.bin');assert len(r)==64 and r[-1][0]/r[-1][1]==12.6
print('Saved all64 samples through12.6s')
