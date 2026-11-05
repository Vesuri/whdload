"""Bounded production-order bundle regression, one owned emulator at a time."""
import json,subprocess,sys
from pathlib import Path
import route_status as r
machine=sys.argv[1];scene={'a500':'steady','020':'bank','030':'dense'}[machine];mask=4026 if machine=='030' else 8127
out=Path(f'tmp/prof/w5-bundle-{machine}-{scene}')
def run(*cmd):subprocess.run([sys.executable,*map(str,cmd)],check=True)
run('tools/w5_boot.py',machine,mask,out,'--immediate','--scene',scene)
run('tools/w2_window.py','--out',out/'regression','--step-limit',40,'--timeout',55)
run('tools/w5_vbl_check.py',out)
if machine=='030':
 run('tools/capture_current.py','--out',out/'dma','--fields',20)
 run('tools/w5_saved_audit.py',out)
 d=json.loads((out/'display.json').read_text())
 assert d['observable'] and not d['active_display_conflicts']
r.command('shot '+str((out/'end.png').resolve()))
(out/'complete.json').write_text(json.dumps(dict(complete=True,machine=machine,mask=mask,scene=scene),indent=2)+'\n')
