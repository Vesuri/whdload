#!/usr/bin/env python3
"""Build the VERIFY slave, replay menus/max-detail preferences, stop in flight.
Run from anywhere. --bank captures gameplay input step 40 after a short right bank.
This is a flight-entry harness, not yet a validated FPS or deterministic-state benchmark.
"""
import argparse,hashlib,json,os,re,subprocess,sys,time
from pathlib import Path
import route_status as r,step_log
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--no-shot',action='store_true',help='Leave the exact flight anchor paused for a complete census');p.add_argument('--bank',action='store_true');p.add_argument('--dense',action='store_true');p.add_argument('--out',default='tmp/prof/entry');a=p.parse_args()
    os.chdir(ROOT);out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
    sock=ROOT/'tmp/run/default/.run/redbaron.sock'
    if sock.exists():
        try:r.command('quit')
        except (ConnectionRefusedError,FileNotFoundError):pass
    env=dict(os.environ,VERIFY='1',PANEL_CHECK='0',WARP='1',DETERMINISTIC='1',JOY0='none',JOY0_MODE='nothing',JOY1='none')
    if a.bank or a.dense:
        args=env.get('WHD_ARGS','');values=re.findall(r'(?i)\bCUSTOM5=(\d+)\b',args)
        value=int(values[-1]) if values else 0
        env['WHD_ARGS']=re.sub(r'(?i)\bCUSTOM5=\d+\b','',args).strip()+f' CUSTOM5={value|(2 if a.bank else 0)|(4 if a.dense else 0)}'
    subprocess.run(['bash','tools/build.sh'],env=env,check=True)
    slave=ROOT/'tmp/build/RedBaron-verify.slave';env['SLAVE']=str(slave)
    (out/'slave.slave').write_bytes(slave.read_bytes())
    listing=slave.with_name(slave.name+'.lst')
    if listing.exists():(out/'slave.lst').write_bytes(listing.read_bytes())
    start=time.monotonic()
    with (out/'serve.log').open('w') as log:
        server=subprocess.Popen([sys.executable,'tools/redbaron.py','serve'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    deadline=start+float(env.get('BOOT_TIMEOUT','120'))
    while True:
        if server.poll() is not None:raise RuntimeError('Server exited; see serve.log')
        try:
            if sock.exists():at=r.locate();break
        except (ConnectionRefusedError,FileNotFoundError,RuntimeError):pass
        if time.monotonic()>deadline:raise TimeoutError('Live VERIFY marker not found')
        time.sleep(0.5)
    state=r.read(at)
    if env.get('W6_PAUSE_TRACE') == '1':
        lines=listing.read_text(errors='replace').splitlines()
        def symbol(name):
            for i,line in enumerate(lines):
                if re.search(r'\b'+re.escape(name)+r':',line):
                    for following in lines[i:]:
                        match=re.match(r'00:([0-9A-F]+)\s',following)
                        if match:return int(match[1],16)
            raise ValueError(name)
        base=state['game_anchor']-symbol('tape_game_anchor')
        pending=base+symbol('time_pause_pending')
        commands=[]
        for name in ('time_pause_apply_begin','time_pause_apply_end'):
            commands += [f'break *{base+symbol(name):#x}', 'commands', 'silent',
                         f'printf "PAUSE {name} %u %u\\n", $sr, *(unsigned short*){pending:#x}',
                         'continue', 'end']
        print(r.command('gdb '+'\n'.join(commands)),flush=True)
    if env.get('FILL_TRACE') == '1':
        symbols=listing.read_text(encoding='latin1')
        def fsym(name):return int(re.search(r'^'+name+r'\s+00:([0-9A-Fa-f]+)',symbols,re.M)[1],16)
        base=state['game_anchor']-fsym('tape_game_anchor')
        (out/'diagnostic-base.json').write_text(json.dumps(dict(base=base,state=state)))
        print(r.command(f'gdb break *{base+fsym(env.get("TWIN_FAIL_SYMBOL","fill_twin_fail")):#x}'),flush=True)
    print('Waiting for the flight-only anchor...',flush=True)
    if state['game_steps']==0:
        print(r.command(f"until {state['game_anchor']:#x}"),flush=True)
    elif not (env.get('BOOT_BREAK') and state['game_steps']==1 and state['inflight']==1):
        raise RuntimeError(f'Unexpected already-running flight checkpoint: {state}')
    state=r.read(at)
    if state['inflight']!=1 or state['game_steps']!=1:raise RuntimeError(f'Unexpected anchor: {state}')
    entry_seconds=time.monotonic()-start
    initial=step_log.collect()
    (out/'entry-steps.json').write_text(json.dumps(initial,indent=2)+'\n')
    r.command(f'gdb dump binary memory tmp/build/entry-h3.bin {initial["h3"]:#x} {initial["h3"]+0xbd0c:#x}')
    (out/'entry-h3.bin').write_bytes((ROOT/'tmp/build/entry-h3.bin').read_bytes())
    if not a.no_shot:print(r.command('shot '+str(out/'first.png')),flush=True)
    if a.bank:
        # shot advances one PAL field: read the step again before counting crossings.
        current=r.read(at)['game_steps'];remaining=40-current
        if remaining<1:raise RuntimeError('Passed requested bank checkpoint')
        print(r.command(f"gdb break *{state['game_anchor']:#x}"),flush=True)
        print(r.command(f'gdb ignore $bpnum {remaining-1}'),flush=True)
        print(r.command('gdb continue'),flush=True)
        print(r.command('gdb delete'),flush=True)
        print(r.command('shot '+str(out/'banked.png')),flush=True)
    final=r.read(at)
    meta=dict(entry_seconds=entry_seconds,entry=state,final=final,
              archive_sha256=digest(ROOT/'tmp/archives/RedBaron_v2.1.lha'),
              slave_sha256=digest(slave),sim_sha256=digest((ROOT/'tmp/game'/env.get('GAME_DIR','RedBaron'))/'data/sim'),
              preferences_sha256=digest((ROOT/'tmp/game'/env.get('GAME_DIR','RedBaron'))/'data/SIMPREFS.PRF'),
              cpu=env.get('CPU','68000'),chip_kb=env.get('CHIP_KB','1024'),fast_kb=env.get('FAST_KB','2048'),
              detail='World max; Aircraft max; Ground detail ON IN COMBAT; original Time Scale')
    for source,name in [(ROOT/'tmp/run/default/.run/fsuae/Cache/Logs/debug.uae','debug.uae'),(ROOT/'tmp/run/default/.run/fsuae.log','fsuae.log')]:
        if source.exists():(out/name).write_bytes(source.read_bytes())
    meta['whd_args']=env.get('WHD_ARGS','')
    meta['extra_args']=env.get('EXTRA_ARGS','')
    meta['host_malloc_scribble']=env.get('MallocScribble','')
    meta['host_malloc_prescribble']=env.get('MallocPreScribble','')
    (out/'entry.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(f'Reached flight in {entry_seconds:.1f} s. Emulator paused; evidence: {out}',flush=True)
    print('Resume: python3 tools/redbaron.py cont; stop: python3 tools/redbaron.py quit',flush=True)
if __name__=='__main__':main()
