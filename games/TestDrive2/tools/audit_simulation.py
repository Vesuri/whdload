#!/usr/bin/env python3
"""Check v1 simulation hook boundaries, overlaps and direct incoming branches.
Requires the user's original duel file; never writes or embeds game bytes.
Whole-function PL_P replaces the tail too; operand-only PL_W/L/NOP are intentional.
Indirect calls and helper return adjustments still require manual review.
"""
import argparse, os, re, subprocess
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('duel',type=Path)
a=p.parse_args()
raw=a.duel.read_bytes()
if len(raw)!=108868: p.error('requires duel v1 (108868 bytes)')
out=subprocess.check_output([os.path.expanduser('/path/to/m68k-amiga-elf-objdump'),
    '-D','-b','binary','-m','m68k:68000','--start-address=40',
    '--stop-address='+str(40+0x1156c),str(a.duel)],text=True)
ins={}
for line in out.splitlines():
    m=re.match(r'\s*([0-9a-f]+):\s+((?:[0-9a-f]{4} ?)+)\s+(.+)',line)
    if m: ins[int(m[1],16)-40]=m[3]
spans=[]
source=Path(__file__).resolve().parents[1]/'whdload/simulation-patches.i'
for line in source.read_text().splitlines():
    m=re.search(r'PL_(PSS|PS|P)\s+\$([0-9a-f]+),([^;]+)',line)
    if not m:continue
    kind,start,args=m.groups();start=int(start,16)
    end=start+6+(int(args.split(',')[1]) if kind=='PSS' else 0)
    spans.append((start,end,kind))
errors=[]
for start,end,kind in spans:
    if start not in ins or (kind!='P' and end not in ins):
        errors.append(f'instruction boundary {start:05x}..{end:05x}')
    for other,other_end,_ in spans:
        if start<other<end:errors.append(f'overlap {start:05x}/{other:05x}')
for pc,op in ins.items():
    if any(start<=pc<end for start,end,_ in spans):continue
    m=re.match(r'(?:b\w+\.[sw]|jsr|jmp)\s+0x([a-f0-9]+)',op)
    if not m:continue
    dest=int(m[1],16)-40
    for start,end,_ in spans:
        if start<dest<end:errors.append(f'branch {pc:05x} -> {dest:05x} inside hook {start:05x}')
for error in errors:print(error)
print(f'{len(spans)} hooks checked; {len(errors)} errors')
raise SystemExit(bool(errors))
