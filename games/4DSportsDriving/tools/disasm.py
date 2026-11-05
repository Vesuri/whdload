#!/usr/bin/env python3
"""Disassemble exact original code-hunk ranges; arguments are hex offsets."""
import sys
from pathlib import Path
import capstone
root=Path(__file__).resolve().parents[1]
code=(root/'tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes()[0x28:0x28+0x3a04c]
md=capstone.Cs(capstone.CS_ARCH_M68K,capstone.CS_MODE_M68K_000)
for i in md.disasm(code[int(sys.argv[1],16):int(sys.argv[2],16)],int(sys.argv[1],16)):
 print(f'{i.address:05x}: {i.bytes.hex():16} {i.mnemonic:10} {i.op_str}')
