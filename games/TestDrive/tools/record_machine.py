#!/usr/bin/env python3
"""Record first-value-wins effective launch options before buffered FS-UAE logging."""
import json,sys
from pathlib import Path
out=Path(sys.argv[1]);config={}
for arg in sys.argv[2:]:
    if arg.startswith('--') and '=' in arg:
        key,value=arg[2:].split('=',1);config.setdefault(key,value)
for key in ('amiga_model','cpu','chip_memory','fast_memory'):
    if key not in config:raise ValueError('missing explicit '+key)
config.setdefault('slow_memory','0')
out.write_text(json.dumps(config,indent=2)+'\n')
