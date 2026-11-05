#!/usr/bin/env python3
import argparse,json,subprocess,sys
from pathlib import Path
import route_status as r,step_log
sys.path.insert(0,'tools');import census_window
p=argparse.ArgumentParser();p.add_argument('machine',choices=['a500','020','030']);p.add_argument('out',type=Path);a=p.parse_args()
start,end={'a500':(140,240),'020':(80,400),'030':(120,660)}[a.machine]
s=step_log.collect()
if s['count']<start:step_log.advance(start)
s=step_log.collect();assert s['count']==start
(a.out/'rate-start.json').write_text(json.dumps(s,indent=2)+'\n')
r.command(f'gdb dump binary memory {a.out}/rate-start-h3.bin {s["h3"]:#x} {s["h3"]+0xbd0c:#x}')
subprocess.run([sys.executable,'tools/w2_window.py','--timeout','55','--step-limit',str(end+1),'--out',str(a.out/'rate-census')],check=True)
c=json.loads((a.out/'rate-census/census.json').read_text());summary=census_window.summarize(c,start,end);assert summary['meets_2000_fields']
(a.out/'rate.json').write_text(json.dumps(summary,indent=2)+'\n');print(summary)
s=step_log.collect();r.command(f'gdb dump binary memory {a.out}/rate-end-h3.bin {s["h3"]:#x} {s["h3"]+0xbd0c:#x}')
