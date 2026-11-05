"""Exact repeated full-window evidence, not just matching frame counts."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('first');p.add_argument('repeat');a=p.parse_args();root=Path(__file__).resolve().parents[1]/'tmp/prof';paths=[root/x for x in [a.first,a.repeat]]
base=[json.loads((p/'baseline.json').read_text()) for p in paths];meta=[json.loads((p/'metadata.json').read_text()) for p in paths]
result=dict(first=a.first,repeat=a.repeat,same_slave=(paths[0]/'slave.slave').read_bytes()==(paths[1]/'slave.slave').read_bytes(),same_layout=meta[0]['layout']==meta[1]['layout'],same_configuration=meta[0]['configuration']==meta[1]['configuration'],same_windows=base[0]['windows']==base[1]['windows'],same_events=base[0]['events']==base[1]['events'],same_per_field=base[0]['per_field']==base[1]['per_field'])
for kind in ['states','fronts']:result['same_'+kind+'_digest']=(paths[0]/(kind+'.bin.sha256')).read_text()==(paths[1]/(kind+'.bin.sha256')).read_text()
result['passed']=all(v for k,v in result.items() if k.startswith('same_'));(paths[1]/'repeat-comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(result);assert result['passed']
