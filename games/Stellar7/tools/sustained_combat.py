#!/usr/bin/env python3
"""Serial selected-rate combat through nominal tick 9600 or first inactive tick.

The end is observed before death/exit reset, so menus never dilute throughput.
Keeps exact builds, field-counter checkpoints, active actor counts, health,
input-history integrity and pending debt. No invulnerability or actor changes.
"""
import argparse
import fcntl
import json
import os
import struct
import subprocess
import sys
from pathlib import Path
import audit_hooks
import input_history_state
import rate_matrix
import sim60_state
import simulation_rate
ROOT=Path(__file__).resolve().parent.parent


def run(prefix,machines,end):
    prefix=prefix.resolve();prefix.relative_to(ROOT/'tmp');prefix.mkdir(parents=True,exist_ok=True)
    assert end>5400 and end%300==0, 'end must be a multiple of 300 beyond the heavy reference'
    results={}
    with (ROOT/'tmp/rate-matrix.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        try:
            for machine in machines:
                cpu,model,chip,fast,slow,hz,ntsc=rate_matrix.MACHINES[machine]
                n=3 if cpu=='68000' else 12
                scale=lambda tick:(tick*n+11)//12
                folder=prefix/machine;listing=prefix/(machine+'.lst');report=prefix/(machine+'.json')
                if folder.exists():raise ValueError(f'Use a fresh prefix; preserving {folder}')
                flags=f'-DSIM60=1 -DS60_SUBSTEPS={n} -DLEVEL_TEST={scale(201)-1} -DLEVEL_LAST=6 -DAPPROACH_TYPE=10'
                if n==3:flags+=' -DPOLYGON_BLIT_IRQ=1'
                flags+=' -L '+os.path.relpath(listing,ROOT)
                env=dict(os.environ,CPU=cpu,AMIGA_MODEL=model,CHIP_KB=str(chip),FAST_KB=str(fast),SLOW_KB=str(slow),NTSC=str(ntsc),EXTRA_ARGS=(f'--uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency={hz} --uae_cpu_cycle_exact=true' if hz else ''),WHD_ARGS='CUSTOM1=1 CUSTOM3=1',VERIFY_FLAGS=flags)
                if model=='A1200':env['KICKSTART']=os.environ['KICKSTART_A1200']
                points=[scale(t) for t in range(900,end+1,300)]
                command=[sys.executable,'tools/fixed_window.py',os.path.relpath(folder,ROOT),'--tick',str(scale(600)),'--tick-checkpoints',*map(str,points),'--level','6','--state-only','--fields','1','--stop-on-inactive']
                print('Extended combat '+machine,flush=True)
                with (prefix/(machine+'.log')).open('w') as log:subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
                listing.with_suffix('.slave').write_bytes((folder/'slave.slave').read_bytes())
                audit=audit_hooks.installed(folder,listing)
                paths=[folder]+sorted((folder/'checkpoints').iterdir(),key=lambda p:int(p.name))
                samples=[]
                for path in paths:
                    state=sim60_state.read(path);history=input_history_state.read(path)
                    assert not history['missing_ticks'] and not history['queue_drops'],history
                    data=(path/'state.bin').read_bytes()
                    samples.append(dict(tick=state['ticks'],field=state['observed_field'],pending=state['pending_ticks'],energy=struct.unpack_from('>h',data,0x46c4)[0],active=bool(data[0x1e53]),active_actors=struct.unpack_from('>H',data,0x43b2)[0]))
                terminal=json.loads((folder/'terminal.json').read_text()) if (folder/'terminal.json').exists() else None
                assert all(x['active'] for x in samples[:-1])
                if terminal:assert not samples[-1]['active'] and samples[-1]['tick']==terminal['actual_tick']
                else:assert samples[-1]['active'] and samples[-1]['tick']==scale(end)
                result=dict(machine=machine,substeps=n,flags=flags,measurement=simulation_rate.interval(paths[0],paths[-1]),segments=[simulation_rate.interval(a,b) for a,b in zip(paths,paths[1:])],samples=samples,terminal=terminal,hooks=audit,scope='Active session only, including the final lethal/exit update if observed; no modal/retry time.')
                report.write_text(json.dumps(result,indent=2)+'\n');results[machine]=result
                print(machine,json.dumps(result['measurement']),flush=True)
        finally:
            with (prefix/'restore.log').open('w') as log:subprocess.run(['make','-s','slave'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    return results


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('prefix',type=Path)
    p.add_argument('--machines',nargs='+',choices=rate_matrix.MACHINES,default=list(rate_matrix.MACHINES))
    p.add_argument('--end',type=int,default=9600,help='nominal N=12 endpoint; checkpoints every 300 ticks')
    a=p.parse_args();run(a.prefix,a.machines,a.end)
