import sys,json
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 head=read_bytes(s,0x8b02e,8)
 selected=head[:2]==bytes.fromhex('4ef9')
 expect=os.environ.get('RR_EXPECT_SELECTED','1')=='1';assert selected==expect
 result=dict(selected=selected,native_entry=head.hex())
 if selected:
  target=int.from_bytes(head[2:6],'big');assert 0x200000<=target<0xa00000 or target>=0x1000000,hex(target)
  native=bytes.fromhex('33fcffff000a59e4')+read_bytes(s,0x8b036,0x348)
  copied=read_bytes(s,target,0x350);assert copied==native
  result.update(target=hex(target),bytes_equal=len(copied))
 else:assert head.hex()=='33fcffff000a59e4'
 if os.environ.get('RR_EXPECT_MMU','0')!='0':
  result['stats']=counters(s,stats_address(s));assert result['stats']['mmu_tc']&0x8000
 result['provenance']=provenance(os.environ['SLAVE'],s)
 (s.out/'probe.json').write_text(json.dumps(result,indent=2)+'\n');print(result['selected'],result.get('target'),flush=True)
finally:s.quit()
