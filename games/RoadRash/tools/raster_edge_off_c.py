import sys,json,os
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 entry=read_bytes(s,0xb1994,10).hex();assert entry=='2f08207affb848e75000',entry
 result=dict(entry=entry,field=field(s),provenance=provenance(os.environ['SLAVE'],s));(s.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('native edge entry retained',entry,flush=True)
finally:s.quit()
