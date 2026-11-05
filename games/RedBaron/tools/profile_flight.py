#!/usr/bin/env python3
"""Capture and analyse up to 100 PAL fields from the max-detail flight route.
Paths passed to --out are relative to the game directory; the destination must not exist.
The first host debugger attachment can take minutes. One extra unrecorded field elapses before the recorded window.
"""
import argparse,hashlib,json,os,shutil,socket,subprocess,sys,time
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(*args,output=None):
    if output:
        with output.open('w') as f:subprocess.run(args,check=True,stdout=f)
    else:subprocess.run(args,check=True)
def command(text):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(1900);s.connect(str(ROOT/'tmp/run/default/.run/redbaron.sock'));s.sendall(text.encode());chunks=[]
        while part:=s.recv(65536):chunks.append(part)
    reply=b''.join(chunks).decode()
    if 'ERROR' in reply:raise RuntimeError(reply)
    return reply

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',default='tmp/prof/'+datetime.now().strftime('profile-%Y%m%d-%H%M%S'))
    p.add_argument('--fields',type=int,default=100,choices=range(1,101),metavar='1..100')
    a=p.parse_args();os.chdir(ROOT);out=Path(a.out).resolve()
    if out.exists():raise SystemExit(f'Refusing to overwrite {out}')
    # Validate before booting; gdb dump filenames must have no spaces below ROOT.
    try:rel=out.relative_to(ROOT)
    except ValueError:raise SystemExit('--out must be below the game directory')
    if any(c.isspace() for c in str(rel)):raise SystemExit('--out must have no spaces below the game directory')
    run(sys.executable,'tools/reach_flight.py','--out',str(out))
    import route_status as r
    at=r.locate();before=r.read(at)
    print(command(f'gdb dump binary memory {rel}/fast-before.bin 0x200000 0x400000'),flush=True)
    names=['trace.bin']
    started=time.monotonic()
    for count,name in zip((a.fields,),names):
        print(f'Capturing {count} PAL fields to {name}...',flush=True)
        print(command(f'profile {count} {out/name}'),flush=True)
    print(command(f'gdb dump binary memory {rel}/fast-after.bin 0x200000 0x400000'),flush=True)
    after=r.read(at);(out/'after.json').write_text(json.dumps(after,indent=2)+'\n')
    shutil.copyfile(ROOT/'tmp/run/default/.run/fsuae/Cache/Logs/debug.uae',out/'emulator.uae')
    meta=dict(fields=a.fields,chunks=[a.fields],unrecorded_start_fields=1,before=before,after=after,host_capture_seconds=time.monotonic()-started,
              files={name:hashlib.file_digest((out/name).open('rb'),'sha256').hexdigest() for name in names})
    (out/'capture.json').write_text(json.dumps(meta,indent=2)+'\n')
    os.environ['SLAVE']=str(out/'slave.slave')
    run(sys.executable,'tools/redbaron_report.py',str(out/names[0]),str(out/'fast-before.bin'),
        '--top','25',output=out/'report.txt')
    run(sys.executable,'tools/profile_metrics.py',str(out),output=out/'metrics.log')
    print(f'Complete: {out}/report.txt and metrics.json. Emulator is paused.')
if __name__=='__main__':main()
