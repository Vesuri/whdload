#!/usr/bin/env python3
"""Check the existing v1 JOTD delay/protection hook boundaries and direct branches.
Requires the user's original gpc file; never writes or embeds game bytes.
Whole-function PL_P replaces the tail too; operand-only PL_W/L/NOP are intentional.
Indirect calls and helper return adjustments still require manual review.
"""
import argparse, os, re, subprocess
import _amigaxdev  # noqa: F401
from amigaxdev.env import tool
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('gpc',type=Path)
a=p.parse_args()
raw=a.gpc.read_bytes()
if len(raw)!=94708: p.error('requires gpc v1 (94708 bytes)')
out=subprocess.check_output([tool('objdump'),
    '-D','-b','binary','-m','m68k:68000','--start-address=40',
    '--stop-address='+str(40+0xe544),str(a.gpc)],text=True)
ins={}
for line in out.splitlines():
    m=re.match(r'\s*([0-9a-f]+):\s+((?:[0-9a-f]{4} ?)+)\s+(.+)',line)
    if m: ins[int(m[1],16)-40]=m[3]
# Existing delay helper adjusts return from $17a to $182; protection skips
# land on whole instructions. These are existing JOTD hooks, not Phase 2 patches.
spans=[(0x39e,0x3a4,'P'),(0x818c,0x8192,'PS'),(0x7094,0x709a,'PS'),(0x75c8,0x75ce,'PS'),(0x174,0x182,'PS'),(0x2b90,0x2ba4,'S'),(0x4978,0x4984,'S'),(0x707a,0x7080,'PS'),(0xe06,0xe10,'PSS'),(0x729a,0x72a2,'PSS'),(0xc12c,0xc132,'RNG'),(0xc1de,0xc1e4,'PS')]
# Phase 6 spans are declared beside the installed hooks.
source=Path(__file__).resolve().parents[1]/'src'
for name in ('GrandPrixCircuitHD.s','simulation.s'):
 for start,length in re.findall(r'PERF_RANGE h0:([0-9A-F]+) (\d+)',(source/name).read_text()):
  start=int(start,16);spans.append((start,start+int(length),'PS'))
errors=[]
for start,end,kind in spans:
    if start not in ins or (kind!='P' and end not in ins):
        errors.append(f'instruction boundary {start:05x}..{end:05x}')
    for other,other_end,_ in spans:
        if start<other<end:errors.append(f'overlap {start:05x}/{other:05x}')
# Linear disassembly sees a branch inside adjacent format/label strings.
# Confirm the exact data bytes before excluding this single false instruction.
assert raw[40+0x2636:40+0x2648] == b'%ld\0%ld\0Lap Number'
for pc,op in ins.items():
    if pc == 0x263c: continue  # 'd\0La', not an executable BCC to odd $729f
    if any(start<=pc<end for start,end,_ in spans):continue
    m=re.match(r'(?:b\w+\.[sw]|jsr|jmp)\s+0x([a-f0-9]+)',op)
    if not m:continue
    dest=int(m[1],16)-40
    for start,end,_ in spans:
        if start<dest<end:errors.append(f'branch {pc:05x} -> {dest:05x} inside hook {start:05x}')
for error in errors:print(error)
print(f'{len(spans)} hooks checked; {len(errors)} errors')
raise SystemExit(bool(errors))
