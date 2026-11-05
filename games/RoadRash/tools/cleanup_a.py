#!/usr/bin/env python3
"""Stop only A-series emulator processes whose live cwd matches their recorded run."""
import os,signal,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'tmp'
# Sessions run as common/run.sh instances, tmp/run/session-<out under tmp/>/ (tools/rr.py).
for pidfile in root.glob('run/session-a-*/.run/fsuae.pid'):
    pid=int(pidfile.read_text());out=pidfile.parent.parent.resolve()
    name=subprocess.run(['ps','-p',str(pid),'-o','comm='],capture_output=True,text=True).stdout.strip()
    if 'fs-uae' not in name:continue
    cwd=subprocess.run(['lsof','-a','-p',str(pid),'-d','cwd','-Fn'],capture_output=True,text=True).stdout.splitlines()
    if 'n'+str(out) not in cwd:continue
    # Leave currently active test processes alone unless explicitly selected.
    allowed=os.environ.get('RR_CLEAN_RUNS','').split(',')
    if '*' not in allowed and out.name[len('session-'):] not in allowed:continue
    try:os.kill(pid,signal.SIGKILL);print('stopped',pid,out.name)
    except ProcessLookupError:pass
