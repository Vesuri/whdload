#!/usr/bin/env python3
"""Fresh-boot TD capture driver. Fixed windows require an explicit TD anchor.
Phase-1 VBL diagnostics are not race benchmarks; the race anchor belongs to phase 4.
"""
import argparse,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
from td import server
from harness import ROOT,GAME,live_regions,snapshot,sha,command,output
from state_fields import capture as state_capture

def run(args,env=None,stdout=None):
    return subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,env=env,stdout=stdout,check=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['demo','fixed']);p.add_argument('out',type=Path)
    p.add_argument('--slave',type=Path);p.add_argument('--fields',type=int,default=5)
    p.add_argument('--state-fields',type=int,default=0);p.add_argument('--skip-fields',type=int,default=0)
    p.add_argument('--anchor',type=lambda s:int(s,0));p.add_argument('--state-only',action='store_true')
    p.add_argument('--watch-state',action='store_true')
    p.add_argument('--swap-only',action='store_true')
    p.add_argument('--timeout',type=int,default=300);p.add_argument('--swap-offset',type=lambda s:int(s,0))
    a=p.parse_args()
    if not 1<=a.fields<=100:p.error('trace fields must be 1..100')
    if a.anchor is not None and not 0<=a.anchor<0x7c0c:p.error('anchor outside TD root hunk')
    if a.mode=='fixed' and a.anchor is None:p.error('fixed capture requires --anchor; phase 4 selects the race anchor')
    if a.swap_only and a.swap_offset is None:p.error('--swap-only requires --swap-offset')
    if a.state_only and not a.state_fields:p.error('--state-only requires --state-fields')
    if a.out.exists():p.error('output exists; choose a fresh directory')
    out=a.out.resolve();output(out/'capture.json');out.mkdir(exist_ok=True)
    slave=(a.slave or Path(os.environ.get('SLAVE') or GAME/'TestDrive.slave')).resolve()
    shutil.copyfile(slave,out/'slave.slave')
    env=dict(os.environ,SLAVE=str(out/'slave.slave'),WARP='1',DETERMINISTIC='1')
    if not env.get('AMIGA_SETUP'):env.setdefault('TD_SETUP','a500')
    env.pop('BOOT_BREAK',None)
    env.pop('BOOT_CONDITION',None)
    keydata={k:env.get(k) for k in ('TD_SETUP','AMIGA_SETUP','CPU','CHIP_KB','FAST_KB','SLOW_KB','EXTRA_ARGS','WHD_ARGS')}
    keydata.update(slave=sha(slave),runtime=sha(ROOT/'manifest/runtime-inputs.sha256'))
    key=hashlib.sha256(json.dumps(keydata,sort_keys=True).encode()).hexdigest()
    cache=ROOT/'tmp/prof'/('hunk-'+key+'.json');cache.parent.mkdir(exist_ok=True,parents=True)
    hb=json.loads(cache.read_text())['hunk'] if cache.exists() else None
    process=None;handle=None
    def stop():
        nonlocal process,handle
        if process is not None:
            try:server.request('quit')
            except (ConnectionError,FileNotFoundError):pass
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
            process=None
        if handle:handle.close();handle=None
    def boot(calibration=False):
        nonlocal process,handle
        log=out/('calibration-serve.log' if calibration else 'serve.log')
        handle=log.open('w');process=subprocess.Popen([sys.executable,str(ROOT/'tools/td.py'),'serve'],cwd=ROOT,env=env,stdout=handle,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+a.timeout
        while time.monotonic()<deadline:
            if 'serving on' in log.read_text():return
            if process.poll() is not None:raise RuntimeError(log.read_text())
            time.sleep(.5)
        raise TimeoutError('server startup/anchor timeout: '+str(log))
    def locate():
        deadline=time.monotonic()+a.timeout
        while time.monotonic()<deadline:
            try:return live_regions(out)
            except RuntimeError:
                if env.get('BOOT_BREAK'):raise RuntimeError('TD hunks missing at fixed anchor; refusing to advance the guest')
                server.request('cont');time.sleep(.5)
        raise TimeoutError('TD hunks not found')
    # One server per harness. Refuse to clobber an active interactive session.
    import socket
    s=socket.socket(socket.AF_UNIX);s.settimeout(.2)
    try:s.connect(server.sock)
    except (FileNotFoundError,ConnectionRefusedError):pass
    else:s.close();raise RuntimeError('TD server is active; stop it before a fresh-boot capture')
    s.close()
    try:
        if a.mode=='fixed' and hb is None:
            boot(True);base,rr=locate();hb=rr['td'];cache.write_text(json.dumps(dict(hunk=hb,key=keydata),indent=2)+'\n');stop()
        if a.mode=='fixed':
            from td_report import game_bytes
            original=game_bytes()[0x28+a.anchor:0x28+a.anchor+2]
            env['BOOT_BREAK']=hex(hb+a.anchor)
            env['BOOT_CONDITION']=f'*(unsigned int*){hb:#x} == 0x600063ae && *(unsigned short*){hb+a.anchor:#x} == {int.from_bytes(original,"big")}'
        boot();base,rr=locate()
        if a.mode=='fixed':
            if rr['td']!=hb:raise RuntimeError('loaded hunk differs from calibration')
            anchor_report=command('info registers pc a4')
            (out/'anchor.txt').write_text(anchor_report)
            import re
            if not re.search(r'pc\s+'+hex(hb+a.anchor)+r'\b',anchor_report):raise RuntimeError('fixed anchor moved during calibration snapshot; do not compare this capture')
        else:
            from ingame import driving
            deadline=time.monotonic()+a.timeout
            while time.monotonic()<deadline:
                server.request('shot '+str(out/'poll.png'))
                if driving(out/'poll.png'):break
                server.request('cont');time.sleep(.5);server.request('stop')
            else:raise TimeoutError('driving view not reached')
        if a.state_fields:state_capture(a.state_fields,out/'state',out/'code.bin',base,a.skip_fields)
        if a.swap_only:
            run([ROOT/'tools/swap_fields.py',a.fields,out,out/'code.bin',hex(base),'--swap-offset',hex(a.swap_offset)],env)
        if not a.state_only and not a.swap_only:
            reply=server.request(f'profile {a.fields} {out}/trace.bin');(out/'profile.txt').write_text(reply)
            if not (out/'trace.bin').exists():raise RuntimeError(reply)
            import _amigaxdev
            from amigaxdev import barto
            t=barto.load(str(out/'trace.bin'))
            if not any(pc not in (None,0x7fffffff) for f in t.fields for pc,c,r in t.instructions(f)):raise RuntimeError('trace has no PCs')
            for name,f in [('first',t.fields[0]),('last',t.fields[-1])]: (out/(name+'.png')).write_bytes(f.shot)
            if a.mode=='demo':
                from ingame import driving
                if not all(driving(out/(n+'.png')) for n in ('first','last')):raise RuntimeError('trace left driving view')
        if a.watch_state:
            if not a.state_fields:raise ValueError('--watch-state requires state capture')
            run([ROOT/'tools/state_watch.py',out/'state'],env)
        server.request('shot '+str(out/'end.png'));snapshot(out)
        shutil.copyfile(ROOT/'tmp/run/default/.run/fsuae.log',out/'fsuae.log')
        shutil.copyfile(ROOT/'tmp/run/default/.run/machine.json',out/'machine.json')
        (out/'capture.json').write_text(json.dumps(dict(mode=a.mode,anchor=a.anchor,trace_fields=0 if a.state_only or a.swap_only else a.fields,state_fields=a.state_fields,skip_fields=a.skip_fields,base=base,regions=rr,inputs=keydata,slave_sha256=sha(out/'slave.slave')),indent=2)+'\n')
    finally:stop()
    reportenv=dict(env,SLAVE=str(out/'slave.slave'))
    if not a.state_only and not a.swap_only:
        with (out/'report.txt').open('w') as f:run([ROOT/'tools/td_report.py',out/'trace.bin',out/'code.bin','--base',hex(base)],reportenv,f)
        args=[ROOT/'tools/frames.py',out/'trace.bin',out/'code.bin',hex(base)]
        if a.swap_offset is not None:args+=['--swap-offset',hex(a.swap_offset)]
        with (out/'frames.txt').open('w') as f:run(args,reportenv,f)
    print('Capture complete:',out)
if __name__=='__main__':main()
