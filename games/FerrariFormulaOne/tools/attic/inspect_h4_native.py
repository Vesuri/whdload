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
for start,end in [(0x1aac0,0x1af80),(0x24ae0,0x24e80)]:
 for i in c.disasm(mem[start:end],start):text.append(f'{i.address:06x}: {i.mnemonic} {i.op_str}')
p=Path('tmp/dev/tmp/h4-native.txt');p.write_text('\n'.join(text)+'\n');print(p)
