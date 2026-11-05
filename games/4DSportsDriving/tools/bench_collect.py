"""Collect completed bench_cell rows, checking each against its frozen slave/window."""
import argparse,hashlib,json,sys
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);parser.add_argument('captures',nargs='+');parser.add_argument('--fallback-slave',type=Path,action='append',default=[]);a=parser.parse_args();out=a.output;rows=[]
for name in a.captures:
 p=Path(name);r=json.loads((p/'bench.json').read_text());w=json.loads((p/'window.json').read_text())
 candidates=[p/'slave.slave']+a.fallback_slave
 binaries=[q for q in candidates if q.exists() and hashlib.sha256(q.read_bytes()).hexdigest()==r['slave_sha256']]
 assert binaries,('No matching frozen/rebuilt binary',p)
 r['binary_evidence']=str(binaries[0])
 for k,v in w.items():assert r[k]==v,(p,k)
 r=dict(r,evidence=str(p));rows.append(r)
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rows,indent=2)+'\n')
for r in rows:print(r['evidence'],f"{r['fps']:.5f} FPS / {r['steps_per_second']:.5f} steps/s")
