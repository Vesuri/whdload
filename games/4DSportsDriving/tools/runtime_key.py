#!/usr/bin/env python3
"""Private emulator monitor input; Amiga raw key IDs in hex, queued press/release.
Examples: 44 (Return), 63+24 (Ctrl-G), 4c (Up), 45 (Escape).
Uses the emulator keyboard path; does not change guest memory.
"""
import sys
from profile_window import command
keys=[int(x,16) for x in sys.argv[1].split('+')]
assert all(0<=x<128 for x in keys)
import json
from pathlib import Path
irq=json.loads(Path('tmp/runtime-input.json').read_text())['irq']
command('stop')
for state, seq in [(1,keys),(0,list(reversed(keys)))]:
    script='\n'.join(f'monitor key {key:x} {state}' for key in seq)
    if '--native' in sys.argv[2:]:
        print(command('gdb '+script).strip())
        command('profile 10 '+str(Path('tmp/native-key-step.bin').resolve()))
    else:
        print(command(f'gdb {script}\ndelete\nbreak *{irq:#x}\nignore $bpnum 9\ncontinue\ndelete').strip())
