from pathlib import Path
exec(Path('tools/check_c3_native_frame.py').read_text().split('rng=random.Random')[0])
ph=sy['_phase_state']
def prepare(phase,n,fraction=False):
 for addr,body in images:write(addr,body)
 write(a4-0x7fe0,bytes.fromhex('4e75'))
 for k in range(1,17):reg(k,k*0x10101)
 reg(17,0x2000);reg(5,a4)
 for off,value in [(0x9606,0),(0x9605,0),(0x9910,15),(0x993e,1),(0x991c,0 if fraction else 22),(0x9911,0),(0x991d,0),(0x95ff,0),(0xe94a,255),(0xaf31,0),(0xf790,0),(0xf791,255),(0xaddc,0)]:pack(a4+off-65536,'B',value)
 for off,value in [(0x9928,0),(0x992a,0),(0x9936,1),(0x990e,0),(0x9926,0)]:pack(a4+off-65536,'h',value)
 pack(a4-0x66c0,'I',a4-0x68c6+8);pack(a4-0x6bb8,'4h',16384,0,0,16384)
 for symbol,size in [('_phase_state',78),('_phase_speed_cache',8),('_time_scalar_state',16),('_drivetrain_state',16),('_projection_state',36),('_motion_position_state',20),('_motion_state',32)]:write(sy[symbol],bytes(size))
 pack(sy['_time_scalar_fields'],'H',n);write(sy['_dispatch_state']+24,b'\x01')
 pack(ph,'HHH',1,0,phase);pack(ph+32,'H',1);pack(ph+38,'H',1)
 if fraction:
  for off,value in [(12,8192),(16,4096),(20,8192),(24,4096)]:pack(ph+off,'I',value)
 invoke(sy['_phase_frame'])
 return read(a4-0x670a,0x5c),read(ph,78)
try:
 count=0
 for n in [1,2,3,7,8,9,15,16,17,31,64]:
  expected=prepare(0,n)
  for phase in range(8):
   assert prepare(phase,n)==expected,(n,phase)
   count+=1
 prepare(5,1,True)
 assert struct.unpack('>H',read(ph+4,2))[0]==6
 assert struct.unpack('>I',read(ph+16,4))[0]==3072
 assert struct.unpack('>I',read(ph+24,4))[0]==3072
 report=dict(passed=True,idle_phase_cases=count,fractional_zero_word_state_preserved=True,scope='Current installed 68000 phase frame. All eight idle phase residues produce identical native car and phase state for eleven elapsed intervals. Nonzero hidden V/R fractions retain their phase and exact increments.')
 Path('tmp/c3-idle-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
