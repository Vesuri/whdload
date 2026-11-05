#!/usr/bin/env python3
import argparse,json,subprocess,sys
from pathlib import Path
import route_status as r,step_log
p=argparse.ArgumentParser();p.add_argument('--suffix',default='');p.add_argument('--resume',action='store_true');p.add_argument('mask',type=int,choices=[0,128]);a=p.parse_args();out=Path(f'tmp/prof/w4-030-{a.mask}{a.suffix}')
if Path('tmp/w4.pause').exists():raise SystemExit('W4 paused before starting another run; remove tmp/w4.pause to resume')
if not a.resume:subprocess.run([sys.executable,'tools/w4_boot.py','030',str(a.mask),str(out)],check=True)
step_log.advance(8);s=step_log.collect();assert s['count']==8
(out/'step8.json').write_text(json.dumps(s,indent=2)+'\n');r.command(f'gdb dump binary memory {out}/step8-h3.bin {s["h3"]:#x} {s["h3"]+0xbd0c:#x}')
subprocess.run([sys.executable,'tools/w4_clock.py','--entry',str(out),'--mask',str(a.mask),'--step','60','--out',str(out/'clock.json')],check=True)
subprocess.run([sys.executable,'tools/routine_wall_time.py',str(out/'clock.json'),'--first-step','8','--last-step','59','--out',str(out/'costs.json')],check=True)
# DMA observability is separate from the preceding cached-CPU timing window.
subprocess.run([sys.executable,'tools/capture_current.py','--out',str(out/'dma'),'--fields','20'],check=True)
subprocess.run([sys.executable,'tools/w4_rate.py','030',str(out)],check=True)
print(r.command('shot '+str((out/'end.png').resolve())))
(out/'complete.json').write_text(json.dumps(dict(complete=True,mask=a.mask,machine='030'),indent=2)+'\n')
