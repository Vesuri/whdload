from unicorn_b import *
from layout import locate
mem=(root/'tmp/step7-d2-smoke/fast.bin').read_bytes();h=locate(mem)['hunks']
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
def a(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
for allocation in (0,0x700000):
 c=CPU();c.put(0x200000,mem);c.put(base,blob)
 arena=0x600000;exe=0x500000;resload=0x510000
 c.put(arena+a('RT_HUNKS')-base,struct.pack('>9I',*h))
 c.put(4,struct.pack('>I',exe))
 # AllocMem stub records requested size/flags, returning supplied result.
 c.put(exe-198,bytes.fromhex('23c00052000023c100520004203c')+struct.pack('>I',allocation)+bytes.fromhex('4e75'))
 c.put(resload+0x64,bytes.fromhex('23c90052000823c80052000c4e75'))
 c.rw(1,arena);c.rw(3,resload);c.call(a('cpu_render_install'))
 assert c.rr(9)==0,hex(c.rr(9))
 size,flags,image,patch=struct.unpack('>4I',c.get(0x520000,16))
 assert (size,flags)==(36010,5),(size,flags)
 assert c.get(h[0],0xf0c8)==mem[h[0]-0x200000:h[0]-0x200000+0xf0c8]
 if allocation:assert image==h[0] and patch and c.get(a('cpu_render_native_line'),10)==c.get(h[0]+0x8548,10)
 else:assert image==patch==0 and c.get(a('cpu_render_buffer'),4)==bytes(4)
 c.close()
print('PASS MEMF_FAST allocation request, no-memory native fallback, complete native trampoline and patch dispatch')
