import os,sys,subprocess,json
from pathlib import Path
from matrix_a import config
root=Path(sys.argv[1]).resolve();root.mkdir(parents=True,exist_ok=True);results=[]
for i,cell in enumerate(['a500-1m','a1200','030-50','040-25','060-50']):
 env=config(cell);env['WHD_ARGS']='NoCache CUSTOM2=1';env['RR_LANE_SELECTED']='0';env['DEBUG_PORT']=str(26793+i)
 out=root/cell;subprocess.run([sys.executable,str(Path(__file__).with_name('lane_scan_probe_c.py')),str(out)],env=env,check=True)
 result=json.loads((out/'probe.json').read_text());assert result['native_entry_unchanged'];results.append(dict(cell=cell,result=result))
(root/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
