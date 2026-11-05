#!/usr/bin/env python3
"""Read-only long phase-family capture and offline recurrent comparisons."""
import os,json,subprocess,sys
from pathlib import Path
root=Path.cwd();meta=json.loads((root/'tmp/prof/contact-prediction-d9-long/anchor.json').read_text())
for phase in ('minus64','plus64'):
    baseline='phase-'+phase+'-d9';cap='tmp/prof/contact-prediction-d9-'+phase+'-long'
    env=dict(os.environ)
    env.update({k:v for k,v in meta['settings'].items() if v is not None and k!='FSUAE_SHA256'})
    env.update(DEBUG_PORT='2501',WARP='1',SLAVE=str(root/'tmp/prof'/baseline/'slave.slave'))
    try:
        subprocess.run([sys.executable,'tools/quick_start.py',cap,'--simulation','50','--tick','450'],env=env,check=True)
        subprocess.run([sys.executable,'tools/contact_prediction_probe.py',cap,'800',baseline],env=env,check=True)
        subprocess.run([sys.executable,'tools/contact_long_comparison.py',cap,baseline,'phase-'+phase+'-native20'],env=env,check=True)
    finally:
        subprocess.run([sys.executable,'tools/driving.py','quit'],env=env,check=False)
