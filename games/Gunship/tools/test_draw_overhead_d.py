from unicorn_b import *
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
def a(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
for lo,hi in [(200,-1),(0,0),(199,199),(0,199),(41,47),(-7,8),(192,210),(200,210),(10,9)]:
 c=CPU();c.put(base,blob);h0=0x300000;c.put(a('draw_overhead_h0'),struct.pack('>I',h0));c.put(a('draw_overhead_span_ready'),b'\0\1');c.put(h0+0x8d84,b'EDGE'+b'abcd'*200+b'ED');c.put(h0+0x90aa,struct.pack('>hhh',lo,0,hi))
 regs={r:0x123400+r for r in list(range(1,8))+list(range(9,17))}
 for r,v in regs.items():c.rw(r,v)
 c.call(a('draw_overhead_clear_spans'))
 assert all(c.rr(r)==v for r,v in regs.items())
 expected=b''.join(bytes.fromhex('ffff0000') if max(lo,0)<=y<=min(hi,199) else b'abcd' for y in range(200))
 assert c.get(h0+0x8d84,806)==b'EDGE'+expected+b'ED',(lo,hi)
 c.close()
c=CPU();c.put(base,blob);h0=0x300000;c.put(a('draw_overhead_h0'),struct.pack('>I',h0))
c.put(h0+0x8d84,b'EDGE'+bytes(800)+b'ED');c.call(a('draw_overhead_clear_spans'))
assert c.get(h0+0x8d84,806)==b'EDGE'+bytes.fromhex('ffff0000')*200+b'ED'
assert c.get(a('draw_overhead_span_ready'),2)==b'\0\1';c.close()
# Removed wait's replacement must change only Z, as the old completed BTST.
for flags in range(32):
 c=CPU();c.put(0x80000,bytes.fromhex('003c000440c04e71'));c.rw(17,0x2000|flags)
 ok(u.uc_emu_start(c.h,0x80000,0x80006,0,10));assert c.rr(9)&31==flags|4
 c.close()
print('PASS first-use initialization; nine span ranges/guards/register preservation; 32 redundant-wait CCR cases')
