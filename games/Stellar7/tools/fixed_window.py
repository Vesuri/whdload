#!/usr/bin/env python3
"""Capture a fixed SOL gameplay window with the VERIFY/CUSTOM5 menu fixture.
Usage: tools/fixed_window.py tmp/prof/base [--fields 100] [--frame 90] [--swaps-only]
CPU, CHIP_KB, FAST_KB, EXTRA_ARGS, AMIGA_MODEL and KICKSTART remain overridable.
"""
import argparse, os, socket, subprocess, sys, time, struct, json
from pathlib import Path
from stellar7 import SOCK
from stellar7_report import regions

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('out',type=Path)
p.add_argument('--fields',type=int,default=100)
p.add_argument('--frame',type=int,default=90)
p.add_argument('--checkpoints',type=int,nargs='*',default=[],help='additional simulation frames to snapshot after the trace')
p.add_argument('--swaps-only',action='store_true')
p.add_argument('--state-only',action='store_true')
a=p.parse_args()
if not 1 <= a.fields <= 100:
    p.error('--fields must be 1..100 (Barto capture limit); use checkpoints for longer runs')
if a.checkpoints != sorted(set(a.checkpoints)) or any(x <= a.frame for x in a.checkpoints):
    p.error('--checkpoints must be unique increasing simulation steps after --frame')
root=Path(__file__).resolve().parent.parent
os.chdir(root)
out=a.out.resolve(); out.relative_to(root/'tmp')
assert ' ' not in str(out.relative_to(root)), 'capture subdirectory must not contain spaces (gdb limitation)'
if out.exists() and any(out.iterdir()):
    p.error('capture directory is not empty; choose a new path to preserve previous measurements')
out.mkdir(parents=True,exist_ok=True)
def cmd(text, timeout=900):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(timeout);s.connect(SOCK);s.sendall(text.encode());reply=b''
        while part:=s.recv(65536):reply+=part
    result=reply.decode()
    if 'ERROR' in result:raise RuntimeError(result)
    return result
try:cmd('quit',5)
except (OSError,RuntimeError):pass
subprocess.run(['make','-s','-C','whdload','verify'],check=True)
(out/'slave.slave').write_bytes(Path('whdload/Stellar7.Slave').read_bytes())
env=dict(os.environ,SLAVE=str(out/'slave.slave'),WHD_ARGS='CUSTOM5=1 '+os.environ.get('WHD_ARGS',''),JOY0='none',JOY1='none',DETERMINISTIC='1',WARP='1')
os.environ['SLAVE']=env['SLAVE']
fast=int(env.get('FAST_KB','0')); chip=int(env.get('CHIP_KB','512'))
base=0x200000 if fast else 0xc00000
size=fast*1024 if fast else 1536*1024
log=(out/'serve.log').open('w')
server=subprocess.Popen([sys.executable,'tools/stellar7.py','serve'],stdout=log,stderr=subprocess.STDOUT,env=env)
def dump(destination=out):
    destination.mkdir(parents=True,exist_ok=True)
    code=str((destination/'code.bin').relative_to(root)); cb=str((destination/'chip.bin').relative_to(root))
    cmd(f'gdb dump binary memory {code} {base:#x} {base+size:#x}\ndump binary memory {cb} 0 {chip*1024:#x}')
    return (destination/'code.bin').read_bytes(),(destination/'chip.bin').read_bytes()
try:
    deadline=time.monotonic()+120
    while 'serving on' not in (out/'serve.log').read_text():
        if server.poll() is not None:raise RuntimeError((out/'serve.log').read_text())
        if time.monotonic()>deadline:raise TimeoutError('server startup')
        time.sleep(.2)
    print('Booting to loaded game...',flush=True)
    for attempt in range(120):
        cmd('wait 0.1');cmd('stop');mem,ch=dump()
        try:r={n:lo for lo,hi,n,o in regions(mem,base,ch)}
        except ValueError:continue
        if 's7' in r:break
    else:raise RuntimeError('game not loaded')
    h=r['s7']; data=r['s7-data']; anchor=h+0x2c16
    count=struct.unpack_from('>H',mem,data-base+0x1e96)[0]
    if count>a.frame:raise RuntimeError(f'Already passed frame {a.frame}: {count}')
    print(f'Waiting for gameplay frame {a.frame}...',flush=True)
    reply=cmd(f'gdb break *{anchor:#x}\ncondition $bpnum *(unsigned short*){data+0x1e96:#x} >= {a.frame}\ncontinue\ndelete')
    mem,ch=dump()
    count=struct.unpack_from('>H',mem,data-base+0x1e96)[0]
    assert count==a.frame,(count,a.frame)
    (out/'anchor.txt').write_text(reply+f'\nframe={count}\ncode={h:#x}\ndata={data:#x}\nbase={base:#x}\n')
    (out/'metadata.json').write_text(json.dumps(dict(code_base=h,data_base=data,base=base,frame=count,fields=a.fields,cpu=env.get('CPU','68000'),chip_kb=chip,fast_kb=fast,whd_args=env['WHD_ARGS'],verify_flags=env.get('VERIFY_FLAGS','')),indent=2)+'\n')
    (out/'state.bin').write_bytes(mem[data-base:data-base+0x823c])
    print(f'At frame {count}; capturing {a.fields} fields...',flush=True)
    if a.state_only:pass
    elif a.swaps_only:
        subprocess.run([sys.executable,'tools/swap_fields.py',str(a.fields),str(out),str(out/'code.bin'),hex(base),str(out/'chip.bin')],check=True,env=env)
    else:
        cmd(f'profile {a.fields} {out}/trace.bin')
        import barto
        t=barto.load(out/'trace.bin')
        if len(t.fields) != a.fields:raise RuntimeError(f'Requested {a.fields} fields, captured {len(t.fields)}')
        (out/'first.png').write_bytes(t.fields[0].shot);(out/'last.png').write_bytes(t.fields[-1].shot)
        for tool,target in [('stellar7_report.py','report.txt'),('frames.py','frames.txt')]:
            args=[sys.executable,'tools/'+tool,str(out/'trace.bin'),str(out/'code.bin')]
            args+=['--base',hex(base)] if tool=='stellar7_report.py' else [hex(base)]
            with (out/target).open('w') as f:subprocess.run(args,stdout=f,env=env,check=True)
    for checkpoint in a.checkpoints:
        reply=cmd(f'gdb break *{anchor:#x}\ncondition $bpnum *(unsigned short*){data+0x1e96:#x} >= {checkpoint}\ncontinue\ndelete')
        folder=out/'checkpoints'/str(checkpoint)
        mem,ch=dump(folder)
        count=struct.unpack_from('>H',mem,data-base+0x1e96)[0]
        if count != checkpoint:raise RuntimeError(f'Checkpoint {checkpoint} already passed: {count}')
        (folder/'anchor.txt').write_text(reply+f'\nframe={count}\ncode={h:#x}\ndata={data:#x}\nbase={base:#x}\n')
        (folder/'state.bin').write_bytes(mem[data-base:data-base+0x823c])
    print('Saved '+str(a.out),flush=True)
finally:
    try:cmd('quit',5)
    except (OSError,RuntimeError):pass
    try:server.wait(timeout=5)
    except subprocess.TimeoutExpired:server.terminate()
    log.close()
