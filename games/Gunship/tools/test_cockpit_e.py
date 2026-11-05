from unicorn_b import *
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data())
listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
def a(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(base,blob)
def l(p,v):c.put(p,struct.pack('>I',v))
def w(p,v):c.put(p,struct.pack('>H',v))
# Native trampoline stand-ins count executions without touching hardware.
for name,p in [('cockpit_native_erase',0x520000),('cockpit_native_draw',0x520004)]:
 c.put(a(name),bytes.fromhex('52b9')+struct.pack('>I',p)+bytes.fromhex('4e75'))
arena=0x600000;h6=0x700000;inputs=0x510000;flags=0x510100
l(a('timing_runtime_arena'),arena);l(arena+a('RT_HUNKS')-base+24,h6)
w(arena+a('RT_CAPTURE_OWNER')-base,1)
c.put(a('cockpit_inputs'),struct.pack('>3I',inputs,inputs+2,inputs+4));c.put(inputs,bytes([31,0,0,60,80,0]))
l(a('cockpit_restore_counters'),flags)
def frame(index):
 w(h6+0x4bb0,index);c.rw(8,0x8f000);c.call(a('cockpit_check_restores'))
 c.rw(8,0x8f000);c.call(a('cockpit_erase'));c.rw(8,0x8f000);c.call(a('cockpit_draw'))
def counts():return struct.unpack('>2I',c.get(0x520000,8))
for i in [0,1,0,1]:frame(i)
assert counts()==(2,2),counts()
c.put(inputs+4,b'Q');frame(0);frame(1);assert counts()==(4,4)
w(flags+12,2);frame(0);w(flags+12,1);frame(1);w(flags+12,0);frame(0)
assert counts()==(7,7),counts()
w(arena+a('RT_BOUNDARY_PHASE')-base,1);frame(0);assert counts()==(8,8)
w(arena+a('RT_BOUNDARY_PHASE')-base,0);c.rw(8,0x8f000);c.call(a('cockpit_invalidate'));frame(0);frame(1)
assert counts()==(10,10),counts()
c.close();print('PASS independent back buffers, changed inputs, overlapping panel restores, modal fallback and native-swap invalidation')
