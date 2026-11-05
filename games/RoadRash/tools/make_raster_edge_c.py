from pathlib import Path
import re,shutil,difflib
base=Path('src');dst=Path('tmp/c-raster-edge-source');shutil.copytree(base,dst)
rows=[]
for line in Path('tmp/ana/game.dis').read_text().splitlines():
 m=re.match(r'([0-9a-f]{6})\s+[0-9a-f]+\s+(.+)',line)
 if m and 0xb1994<=int(m[1],16)<0xb1ab8:rows.append((int(m[1],16),m[2].strip()))
skip={0xb19a2,0xb19a4,0xb19c2,0xb19c4}
code=['; Private exact edge helper: mutable table remains native.','raster_edge_fast:']
for addr,op in rows:
 code.append(f'edge_{addr:x}:')
 if addr in skip:continue
 op=op.replace('$b1950(pc)','$b1950')
 op=re.sub(r'\$(b[0-9a-f]+)',lambda m: 'edge_'+m[1] if 0xb1994<=int(m[1],16)<0xb1ab8 else m[0],op)
 code.append(' '+op)
(dst/'raster_edge.s').write_text('\n'.join(code)+'\n')
p=dst/'RoadRashHD.s';s=p.read_text();pos=s.index('pl_c_simulation\n');pos=s.index('PL_START',pos)+len('PL_START');s=s[:pos]+'\n\tPL_P $31994,raster_edge_fast\n'+s[pos:];s+='\n IFD C_STEP_BUILD\n include raster_edge.s\n ENDC\n';p.write_text(s)
