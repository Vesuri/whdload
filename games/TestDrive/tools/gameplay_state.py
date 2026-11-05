#!/usr/bin/env python3
"""Read-only gameplay snapshots; tentative fields are not simulation specifications."""
import json,sys
from pathlib import Path
from harness import ROOT,dump,live_regions
out=ROOT/'tmp/phase3'/sys.argv[1]
base,rr=live_regions(out)
data=dump(out/'data.bin',rr['td-data'],rr['td-data']+0x32a4).read_bytes()
fields={'mode':(-22504,2),'selection':(-22500,2),'gear':(-26336,2),'rpm':(-26340,2),'speed_fixed':(-22360,4),'position_fixed':(-22352,4),'chances':(-23352,2),'stage_candidate':(-23346,2),'end_position':(-26234,2)}
state={name:int.from_bytes(data[0x7ffe+off:0x7ffe+off+n],'big',signed=True) for name,(off,n) in fields.items()}
state['regions']=rr;(out/'state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state))
