import json,sys,os
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s);stats=counters(s,stats_address(s));assert stats['race_cacr']==int(os.environ['RR_EXPECT_CACR']),stats
 assert read_bytes(s,0x8747e,6).hex()=='0c790020000a', 'enhanced path unexpectedly installed'
 result=dict(stats=stats,provenance=provenance(os.environ['SLAVE'],s));(s.out/'probe.json').write_text(json.dumps(result,indent=2)+'\n');print('original path, CACR',stats['race_cacr'],flush=True)
finally:s.quit()
