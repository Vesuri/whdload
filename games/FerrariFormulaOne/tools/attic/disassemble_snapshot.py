from pathlib import Path
from capstone import *
import sys
b=Path(sys.argv[1]).read_bytes(); m=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000);m.skipdata=True
for lo,hi in [(0x197a0,0x1babc),(0x229a4,0x25400),(0x64a68,0x6ef20)]:
 for i in m.disasm(b[lo:hi],lo):print(f'{i.address:06x}: {i.bytes.hex():20} {i.mnemonic} {i.op_str}')
