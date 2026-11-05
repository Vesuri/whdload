"""Shared local harness operations; all generated files remain under tmp/dev."""
import hashlib,json,os,re
from pathlib import Path
from td import server
ROOT=Path(__file__).resolve().parents[1]
GAME=ROOT/'tmp/game/TestDrive_v1.3_0089/TestDrive'
def command(text):
    reply=server.request('gdb '+text)
    if any(s in reply for s in ('ERROR','No symbol table','Cannot access memory','Undefined command','syntax error')):raise RuntimeError(reply)
    return reply

def output(path):
    p=Path(path).resolve()
    p.relative_to(ROOT/'tmp')
    if any(x.isspace() for x in str(p.relative_to(ROOT))):raise ValueError('Output names within tmp/ must not contain whitespace')
    p.parent.mkdir(parents=True,exist_ok=True)
    return p

def dump(path,start,end):
    p=output(path)
    # GDB cd takes the rest of the line as a path, unlike dump binary memory.
    command('cd '+str(ROOT))
    command(f'dump binary memory {p.relative_to(ROOT)} {start:#x} {end:#x}')
    if p.stat().st_size!=end-start:raise RuntimeError('truncated memory dump')
    return p

def machine_config():
    return json.loads((ROOT/'tmp/run/default/.run/machine.json').read_text())

def memory_config():
    config=machine_config()
    fast=int(config['fast_memory']);slow=int(config.get('slow_memory',0));chip=int(config['chip_memory'])
    if fast:return 0x200000,fast*1024,chip*1024
    if slow:return 0xc00000,slow*1024,chip*1024
    return 0,chip*1024,chip*1024

def snapshot(out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    server.request('stop');base,size,chip=memory_config()
    dump(out/'code.bin',base,base+size);dump(out/'chip.bin',0,chip)
    return base

def live_regions(out):
    from td_report import regions
    base=snapshot(out)
    rr={n:lo for lo,hi,n,o in regions((Path(out)/'code.bin').read_bytes(),base)}
    if not {'td','td-data'}<=rr.keys():raise RuntimeError('loaded TD root and data hunks not found')
    return base,rr

def listing(slave):
    # A slave's listing: TestDrive.lst beside a tmp/build/<build>/ slave, else <slave>.lst.
    old=Path(str(slave)+'.lst')
    return old if old.exists() else Path(slave).with_suffix('.lst')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
