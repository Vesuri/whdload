#!/usr/bin/env python3
"""Read-only emulator probes of saved phase-family slaves, with owned cleanup."""
import os,sys,subprocess,json
from pathlib import Path
from profile_window import command,ROOT
os.chdir(ROOT)
for phase,hz,baseline in [('minus64',20,'phase-minus64-native20'),('plus64',20,'phase-plus64-native20'),('minus64',50,'phase-minus64-d9')]:
    cap=Path('tmp/prof')/f'phase-release-{phase}-{hz}'
    env=dict(os.environ,SLAVE=str(ROOT/'tmp/prof'/baseline/'slave.slave'))
    try:
        subprocess.run([sys.executable,'tools/quick_start.py',str(cap),'--simulation',str(hz),'--tick',str(11*hz)],env=env,check=True)
        subprocess.run([sys.executable,'tools/release_step_probe.py',str(cap),'11.7'],env=env,check=True)
        m=json.loads((cap/'anchor.json').read_text())
        command(f'gdb dump binary memory {cap}/release-end.bin {m["memory_base"]:#x} {m["memory_base"]+m["memory_size"]:#x}')
        from simulation_fixture import read_fixture
        reference={t:s for t,mode,s in read_fixture(ROOT/'tmp/prof'/baseline,'bridge-end.bin')}
        samples=read_fixture(cap,'release-end.bin');assert all(s==reference[t] for t,mode,s in samples)
        (cap/'baseline-validation.json').write_text(json.dumps(dict(baseline=baseline,matching_full_states=len(samples),state_bytes=1510),indent=2)+'\n')
        print('Verified',cap,len(samples),'full states against baseline',flush=True)
    finally:
        subprocess.run([sys.executable,'tools/driving.py','quit'],env=env,check=False)
