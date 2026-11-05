import sys,json
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s);head=read_bytes(s,0x8970e,6);selected=head[:2]==bytes.fromhex('4ef9')
 assert selected==(os.environ.get('RR_EXPECT_SELECTED','1')=='1')
 result=dict(selected=selected,native_entry=head.hex())
 if selected:
  target=int.from_bytes(head[2:6],'big');assert 0x200000<=target<0xa00000 or target>=0x1000000
  expected=bytes.fromhex('41f9000a6f3c')+read_bytes(s,0x89714,0x1ce)
  assert read_bytes(s,target,0x1d4)==expected
  result.update(target=hex(target),bytes_equal=len(expected))
 else:assert head.hex()=='41f9000a6f3c'
 if os.environ.get('RR_EXPECT_MMU','0')!='0':
  result['stats']=counters(s,stats_address(s));assert result['stats']['mmu_tc']&0x8000
 result['provenance']=provenance(os.environ['SLAVE'],s)
 (s.out/'probe.json').write_text(json.dumps(result,indent=2)+'\n');print(result['selected'],result.get('target'),flush=True)
finally:s.quit()
