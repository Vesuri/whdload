#!/usr/bin/env python3
"""Derive tfx.020 relocation sites from HUNK_RELOC32, never opcode guesses."""
import map_symbols as m,struct,json,hashlib
from pathlib import Path
ns=m.load(m.GAME/'tfx.020');bs=m.load(m.GAME/'TFX.040')
ranges=[(1,0xd98,0x24d4),(1,0x27e0,0x4330),(1,0x4938,0x4a00),(2,0x7cec,0x270f4)]
# Whole original DMA groups match; two sprogtab pointers have merged addends.
for h,base in [(2,0xd98),(4,0xda0),(7,0x24d4),(8,0x27e0),(10,0x4938)]:
 old=bs[h];mask={k for offs in old['relocs'].values() for o in offs for k in range(o,o+4)}
 assert all(a==b for i,(a,b) in enumerate(zip(old['data'],ns[1]['data'][base:])) if i not in mask)
lines=['; tfx.020 (571008 bytes): HUNK_RELOC32 sites targeting the original DMA groups.', '; Each group: source section, number of longword offsets, then offsets.', '; CPU-only palettes, sprite pointer tables and page selectors are excluded.']
report=[]
for ri,(tgt,start,end) in enumerate(ranges):
 lines.append('chip_reloc_'+['mouse','display','audio','video'][ri]+':')
 for src,h in enumerate(ns):
  offsets=sorted(o for o in h['relocs'].get(tgt,[]) if start<=struct.unpack_from('>I',h['data'],o)[0]<end)
  if not offsets:continue
  lines.append(f'        dc.w {src},{len(offsets)}')
  for i in range(0,len(offsets),8):lines.append('        dc.l '+','.join(f'${o:05x}' for o in offsets[i:i+8]))
  report.append(dict(target=tgt,start=start,end=end,chip_offset=[0,0x1740,0x3290,0x3358][ri],source=src,count=len(offsets),offsets=offsets))
 lines.append('        dc.w -1')
text='\r\n'.join(lines)+'\r\n'
root=m.ROOT; (root/'src/chip_reloc_new.i').write_bytes(text.encode())
(m.ROOT/'tmp/step8/relocations.json').write_text(json.dumps(report,indent=2))
print([(r['source'],r['target'],r['count']) for r in report])
