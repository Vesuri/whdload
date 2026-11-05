#!/usr/bin/env python3
"""Capture several fixed demo windows without rebooting between read-only samples.
Invoked by fixed_window.sh; no separate emulator or debugger ownership.
DEMO_TICKS="opening 50 200 350 500 650 800" covers the opening and six camera segments.
"""
import argparse,os,shutil,subprocess,sys,tempfile
from pathlib import Path
from state_fields import command
from i500_report import regions

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('fields',type=int);p.add_argument('out',type=Path)
p.add_argument('base',type=lambda x:int(x,0));p.add_argument('ticks')
a=p.parse_args();ticks=a.ticks.split()
assert ticks,'no windows requested'
assert not os.environ.get('STATE_FIELDS'),'multi-view mode does not capture state'
for tick in ticks:
    assert tick=='opening' or 0<=int(tick)<900,'director tick must be 0..899'
assert 'opening' not in ticks[1:],'opening must be the first window'
blob=(a.out/'code.bin').read_bytes()
g=next(lo for lo,hi,name,o in regions(blob,a.base) if name=='game')
tools=Path(__file__).resolve().parent

def run(name,*args):
    return subprocess.run([sys.executable,str(tools/name),*map(str,args)],check=True,capture_output=True,text=True).stdout

for tick in ticks:
    out=a.out/f'view-{tick}';out.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(a.out/'slave.slave',out/'slave.slave')
    if tick!='opening':
        reply=command(f"""break *{g+0x7ee:#x}
set $i500_seek = 0
continue
while *(unsigned short *){g+0x268d0:#x} != {tick} && $i500_seek < 1800
continue
set $i500_seek = $i500_seek + 1
end
if *(unsigned short *){g+0x268d0:#x} == {tick}
printf "I500DEMO {tick}\\n"
end
delete
""")
        assert f'I500DEMO {tick}\n' in reply,'director anchor not reached'
        (out/'anchor.txt').write_text(reply)
    else:
        shutil.copyfile(a.out/'anchor.txt',out/'anchor.txt')
    shutil.copyfile(a.out/'code.bin',out/'code.bin')
    if os.environ.get('SWAP_ONLY')=='1':
        print(run('swap_fields.py',a.fields,out,out/'code.bin',hex(a.base)),end='',flush=True)
    else:
        target=(out/'trace.bin').resolve()
        reply=run('i500.py','profile',a.fields,target)
        assert target.is_file(),f'no trace: {reply}'
    with tempfile.TemporaryDirectory(prefix='i500-view-') as temporary:
        dump=Path(temporary)/'code.bin'
        command(f'dump binary memory {dump} {a.base:#x} {a.base+len(blob):#x}')
        assert dump.is_file(),'memory capture failed'
        shutil.move(str(dump),out/'code.bin')
    if os.environ.get('SWAP_ONLY')!='1':
        import _amigaxdev  # noqa: F401
        from amigaxdev import barto
        trace=barto.load(str(out/'trace.bin'))
        (out/'first.png').write_bytes(trace.fields[0].shot)
        (out/'last.png').write_bytes(trace.fields[-1].shot)
        report=run('frames.py',out/'trace.bin',out/'code.bin',hex(a.base))
        (out/'frames.txt').write_text(report);print(report,end='',flush=True)
    print(f'completed demo window {tick}: {out}',flush=True)
