"""Production flight entry: only playback owns the original loop."""
from unicorn_b import *
for name in ['Gunship','GunshipNTSC']:
 c=CPU();slave=build/'release'/f'{name}.Slave'
 c.put(base,bytes(BinFmt().load_image(str(slave)).get_segments()[0].get_data()))
 syms={n:int(v,16) for v,n in re.findall(r'^([0-9A-F]{8}) (\w+)$',slave.with_suffix('.lst').read_text(encoding='latin1'),re.M)}
 def addr(n):return base+syms[n]
 arena=0x300000;h0=0x400000;h6=0x500000;marker=0x600000
 c.put(addr('timing_runtime_arena'),struct.pack('>I',arena))
 c.put(arena+syms['RT_HUNKS'],struct.pack('>I',h0));c.put(arena+syms['RT_HUNKS']+24,struct.pack('>I',h6))
 c.put(h0+syms['GS0_563a'],bytes.fromhex('13fc0001')+struct.pack('>I',marker)+bytes.fromhex('4e75'))
 c.put(addr('timing_runtime_loop'),bytes.fromhex('13fc0002')+struct.pack('>I',marker)+bytes.fromhex('70044e75'))
 for flag in [0,1,2,3,255,1,0]:
  c.put(h6+0x45cc,bytes([flag]));c.put(marker,b'\0')
  regs={r:0x8000+r for r in range(1,17)};regs[8]=0x8f000
  for r,v in regs.items():c.rw(r,v)
  c.call(addr('timing_flight_entry'))
  assert c.get(marker,1)==bytes([1 if flag==1 else 2])
  assert all(c.rr(r)==v for r,v in regs.items() if r!=8)
  assert c.rr(8)==0x8f004
 print(name,'7 ownership cases including demo -> normal play passed')
 c.close()
