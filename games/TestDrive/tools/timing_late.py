#!/usr/bin/env python3
"""Phase-5 later race trace after 600 native fields; no guest state writes."""
import argparse,json,os,shutil,subprocess,sys,time,socket,re,signal
from pathlib import Path
from harness import ROOT,server,snapshot,command,sha
from td_report import regions

def resolve(out):
    base=snapshot(out);ram=(out/'code.bin').read_bytes();chip=(out/'chip.bin').read_bytes()
    rr={n:lo for lo,hi,n,o in regions(ram,base)}
    db=rr['td-data']
    for name,offset,entry in [('h3',660,0x175e),('h4',668,0)]:
        q=db-base+offset
        if ram[q:q+2]!=b'\x4e\xf9':raise ValueError('overlay export is not loaded')
        addr=int.from_bytes(ram[q+2:q+6],'big')-entry
        mem,start=(ram,base) if base<=addr<base+len(ram) else (chip,0)
        expected=bytes.fromhex('4e55ffcc') if name=='h4' else bytes.fromhex('4e550000')
        if mem[addr-start+entry:addr-start+entry+4]!=expected:raise ValueError('overlay signature mismatch')
        rr[name]=addr
    return base,rr

def state(out,rr):
    b=(out/'code.bin').read_bytes();base=json.loads((ROOT/'tmp/run/default/.run/machine.json').read_text())
    lo=0x200000 if int(base['fast_memory']) else 0xc00000
    a4=rr['td-data']+0x7ffe
    fs={'vbl':(-31782,4),'mode':(-22504,2),'car':(-22500,2),'stage':(-23346,2),'pos':(-22352,4),'speed':(-22360,4),'gear':(-26336,2),'rng':(-25640,2),'frames':(-22312,4)}
    return {n:int.from_bytes(b[a4+off-lo:a4+off-lo+size],'big',signed=True) for n,(off,size) in fs.items()}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('out',type=Path);p.add_argument('--calibrate',action='store_true');p.add_argument('--h4',type=lambda s:int(s,0));p.add_argument('--fields',type=int,default=100);p.add_argument('--swap-only',action='store_true');a=p.parse_args()
    if a.out.exists():p.error('output exists')
    if not 1<=a.fields<=100 or (a.swap_only and a.fields<2):p.error('invalid field count')
    if not a.calibrate and a.h4 is None:
        pin=json.loads((ROOT/'manifest/race-anchor.json').read_text())
        preset=os.environ.get('TD_SETUP','a500')
        if preset not in pin['presets']:p.error('preset needs calibration')
        if any(os.environ.get(k) for k in ('AMIGA_SETUP','CPU','CHIP_KB','FAST_KB','SLOW_KB','EXTRA_ARGS')):p.error('custom machine/options need explicit --h4 calibration')
        if os.environ.get('WHD_ARGS','')!=pin['whd_args']:p.error('benchmark requires pinned WHD_ARGS')
        slave=Path(os.environ.get('SLAVE',str(ROOT/'tmp/build/release/TestDrive.Slave')))
        if sha(slave)!=pin['slave_sha256']:p.error('changed slave needs explicit --h4 calibration')
        if sha(ROOT/'manifest/runtime-inputs.sha256')!=pin['runtime_manifest_sha256']:p.error('runtime changed; recalibrate')
        a.h4=pin['presets'][preset]['h4']
    out=a.out.resolve();out.relative_to(ROOT/'tmp');out.mkdir(parents=True)
    s=socket.socket(socket.AF_UNIX);s.settimeout(.2)
    try:s.connect(server.sock)
    except (FileNotFoundError,ConnectionRefusedError):pass
    else:raise RuntimeError('active server')
    finally:s.close()
    shutil.copyfile(Path(os.environ.get('SLAVE',str(ROOT/'tmp/build/release/TestDrive.Slave'))),out/'slave.slave')
    env=dict(os.environ,FSUAE=str(ROOT/'tmp/phase3/native-emulator/fs-uae'),SLAVE=str(out/'slave.slave'),WARP='1',DETERMINISTIC='1',JOY0='none')
    if not env.get('AMIGA_SETUP'):env.setdefault('TD_SETUP','a500')
    env.pop('BOOT_BREAK',None);env.pop('BOOT_CONDITION',None)
    if not a.calibrate:
        anchor=a.h4+0xf6;env['BOOT_BREAK']=hex(anchor)
        env['BOOT_CONDITION']=f'*(unsigned int*){a.h4:#x} == 0x4e55ffcc && *(unsigned int*){anchor:#x} == 0x2b6c83da'
    f=(out/'serve.log').open('w');process=subprocess.Popen([sys.executable,str(ROOT/'tools/td.py'),'serve'],env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    ready=False
    try:
        until=time.monotonic()+1200
        while 'serving on' not in (out/'serve.log').read_text():
            if process.poll() is not None:raise RuntimeError('server exited')
            if time.monotonic()>until:raise TimeoutError('boot anchor')
            time.sleep(.5)
        ready=True
        if a.calibrate:
            for i in range(180):
                try:base,rr=resolve(out);break
                except (KeyError,ValueError):server.request('cont');time.sleep(1)
            else:raise RuntimeError('overlay unavailable')
        else:
            base,rr=resolve(out)
            if rr['h4']!=a.h4:raise RuntimeError('overlay address changed')
            regs=command('info registers pc a4 a5');(out/'anchor.txt').write_text(regs)
            if not re.search(r'pc\s+'+hex(anchor)+r'\b',regs):raise RuntimeError('anchor not held')
            start=state(out,rr)
            a5=int(re.search(r'a5\s+(0x[0-9a-f]+)',regs).group(1),16)
            raw=(out/'code.bin').read_bytes();offset=a5+8-base
            start['race_car']=int.from_bytes(raw[offset:offset+2],'big',signed=True)
            if 'CUSTOM3=1' in env.get('WHD_ARGS',''):
                if (start['mode'],start['stage'],start['race_car'],start['rng'])!=(1,3,0,0x1dc9):raise RuntimeError('controlled first-demo fixture mismatch: '+str(start))
            (out/'start-state.json').write_text(json.dumps(start,indent=2)+'\n')
            (out/'advance.txt').write_text(command('monitor fields 600'))
            snapshot(out/'late-start')
            if a.swap_only:
                subprocess.run([sys.executable,str(ROOT/'tools/swap_fields.py'),str(a.fields),str(out),str(out/'code.bin'),hex(base),'--swap-offset','0x7aaa'],env=env,check=True)
            else:
                (out/'profile.txt').write_text(server.request(f'profile {a.fields} {out}/trace.bin'))
                from amigaxdev import barto
                t=barto.load(str(out/'trace.bin'))
                for n,field in [('first',t.fields[0]),('last',t.fields[-1])]: (out/(n+'.png')).write_bytes(field.shot)
            snapshot(out/'end');(out/'end-state.json').write_text(json.dumps(state(out/'end',rr),indent=2)+'\n')
        shutil.copyfile(ROOT/'tmp/run/default/.run/machine.json',out/'machine.json')
        (out/'capture.json').write_text(json.dumps(dict(base=base,regions=rr,parts=[a.fields],calibration=a.calibrate,anchor='h4:000f6',fields=a.fields,slave_sha256=sha(out/'slave.slave'),whd_args=env.get('WHD_ARGS',''),source_sha256=sha(ROOT/'src/TestDriveHD.s')),indent=2)+'\n')
        print(json.dumps(dict(out=str(out),regions=rr)),flush=True)
    finally:
        if ready:server.request('quit')
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGTERM);process.wait(timeout=10)
        f.close()
        if (ROOT/'tmp/run/default/.run/fsuae.log').exists():shutil.copyfile(ROOT/'tmp/run/default/.run/fsuae.log',out/'fsuae.log')
        for name in ('fs-uae.log.txt','debug.uae'):
            log=ROOT/'tmp/run/default/.run/fsuae/Cache/Logs'/name
            if log.exists():shutil.copyfile(log,out/name)
if __name__=='__main__':main()
