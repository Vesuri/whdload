from pathlib import Path
import sys,json,struct
sys.path.insert(0,str(Path.cwd()/'Games/FerrariFormulaOne'))
from native import catalog
from capstone import *
g=Path('tmp/dev/tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu');layout=json.loads(Path('Games/FerrariFormulaOne/layout.json').read_text());mem=bytearray(0x80000)
for group in catalog(g):
 if group['header'] not in (0,0x22f30,0x30a30,0x30a7c):continue
 for h in group['hunks']:
  base=layout[str(h['number'])]['base'];mem[base:base+len(h['data'])]=h['data']
  for dest,offs in h['reloc'].items():
   for off in offs:struct.pack_into('>I',mem,base+off,struct.unpack_from('>I',mem,base+off)[0]+layout[str(dest)]['base'])
c=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_020)
text=[]
for start,end in [(0x6a2d0,0x6a61a),(0x6b168,0x6b37a),(0x6b050,0x6b0f0),(0x6b950,0x6ba60),(0x2428a,0x242d0),(0x248b0,0x2496c),(0x23288,0x233a0),(0x239a0,0x23ab0),(0x66802,0x6694e),(0x23946,0x239a0),(0x654fc,0x6553c)]:
 for i in c.disasm(mem[start:end],start):text.append(f'{i.address:06x}: {i.mnemonic} {i.op_str}')
p=Path('tmp/dev/tmp/h3-native.txt');p.write_text('\n'.join(text)+'\n');print(p)
