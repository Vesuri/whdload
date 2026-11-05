import os,sys,json
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 sites={hex(a):read_bytes(s,a,10).hex() for a in (0x8660e,0x8747e,0x86fa0,0x89d32,0x87736,0x870dc,0x8915a,0xa876c,0x8984e)}
 selection=None;stats=None
 if os.environ.get('RR_SELECT_REASON'):
  target=rd(s,0x871de);data=read_bytes(s,target,1024);off=data.find(b'RRCSEL01');assert off>=0
  selection=list(struct.unpack_from('>4I',data,off+8))
  stats=counters(s,stats_address(s))
  if os.environ.get('RR_MMU_TEST'):assert stats['mmu_tc']&0x8000,stats
  assert selection[3]==int(os.environ['RR_SELECT_REASON']),selection
  assert sites['0x8747e'].startswith('4ef9' if selection[3]==3 else '0c790020000a59da'),sites
  if selection[3]!=3:
   assert sites['0x8660e'].startswith('33fc0001000a6f00'),sites
   assert sites['0x87736'].startswith('4eb9000aecba'),sites
   assert sites['0xa876c'].startswith('4ff900077cbe'),sites
   assert sites['0x8984e'].startswith('243c00001c0084c6'),sites
 (s.out/'toggle.json').write_text(json.dumps(dict(selection=selection,stats=stats,sites=sites,state=snapshot(s),provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n')
 print(selection,sites)
finally:s.quit()
