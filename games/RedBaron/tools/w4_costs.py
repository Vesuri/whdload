import json,sys
from pathlib import Path
sys.path.insert(0,'tools')
import fill_costs
out=Path(sys.argv[1]);m=json.loads((out/'entry.json').read_text())
r=fill_costs.measure([out/f'chunk{i}/trace.bin' for i in range(3)],m['entry']['sim'])
(out/'costs.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['summary'],indent=2))
