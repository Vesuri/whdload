#!/usr/bin/env python3
"""Execute the assembled sound-table fix against the original PAL/NTSC table, hunks above 16 MB."""
from unicorn_b import *
root=Path(__file__).resolve().parents[1]
D0,D1,D2,A0=9,10,11,1
versions={'658':('Gunship',0xa150),'1489':('GunshipNTSC',0xa16c)}
seg=0x41000000
cases=0
for version,(folder,routine) in versions.items():
 img=BinFmt().load_image(str(root/'tmp/game'/folder/'data/gamemule'))
 segs=img.get_segments();code=bytes(segs[0].get_data())
 assert code[routine:routine+6]==bytes.fromhex('48e7fffe41f9'),version
 assert code[routine+0x1a:routine+0x20]==bytes.fromhex('028200ffffff'),version
 table=struct.unpack('>I',code[routine+6:routine+10])[0]
 relocs={r.get_offset() for r in segs[0].get_reloc(segs[6]).get_relocs()}
 assert {table+4*k for k in range(16)}<=relocs,version
 entries=[struct.unpack('>I',code[table+4*k:table+4*k+4])[0] for k in range(16)]
 for hunk6 in (0x00200000,0x00fff000,0x02f04000,0x41f851f8):
  c=CPU()
  # Seglist: hunk n's link at seg+n*$100, BPTR to the next; hunk 6's data at its link+4.
  ok(u.uc_mem_map(c.h,seg,0x1000,7))
  links=[seg+n*0x100 for n in range(len(segs))]
  for n,a in enumerate(links):c.put(a,struct.pack('>I',links[n+1]>>2 if n+1<len(links) else 0))
  regs={r:0x54320000+r*0x101 for r in range(1,17) if r!=8};regs[D1]=links[0]
  for r,v in regs.items():c.rw(r,v)
  c.call(base+symbol('sound_hunk_find'))
  assert all(c.rr(r)==v for r,v in regs.items()),(version,'registers')
  assert struct.unpack('>I',c.get(base+symbol('sound_hunk'),4))[0]==links[6]+4,(version,'hunk 6')
  c.put(base+symbol('sound_hunk'),struct.pack('>I',hunk6))
  for v in entries:
   c.rw(D1,0xdeadbeef);c.rw(D2,(v+hunk6)&0xffffffff)
   c.call(base+symbol('sound_entry_fix'))
   assert (c.rr(D1),c.rr(D2))==(v>>24,(v&0xffffff)+hunk6),(version,hex(hunk6),hex(v),hex(c.rr(D1)),hex(c.rr(D2)))
   cases+=1
  c.close()
print(f'sound table fix: {cases} entries, PAL and NTSC, hunk 6 below and above 16 MB')
