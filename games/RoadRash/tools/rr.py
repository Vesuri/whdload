#!/usr/bin/env python3
"""Road Rash harness session: amigaxdev.gdbserve Server on common/run.sh, one instance per OUT.

  python3 tools/rr.py OUT serve       boot common/run.sh (DEBUG=1) as OUT's instance, attach gdb, listen
  python3 tools/rr.py OUT <command>   send a command (shot/wait/gdb/profile/quit...) to it

Each OUT runs as its own common/run.sh instance (tmp/run/<instance>/.run, named after OUT under
tmp/), so an interactive `make run` keeps running. Machine/launch variables (AMIGA_SETUP, WARP,
SLAVE, ...) come from the environment, with the old harness launcher's meanings (launch_env):
no SLAVE boots the shipped slave, AMIGA_SETUP='' is the custom 68000 A500 of game.conf, and
RR_PAD=1 puts a CD32 pad in port 1.
"""
import hashlib,os,re,sys
from pathlib import Path
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev.gdbserve import Server
ROOT=Path(__file__).resolve().parents[1]
COMMON=ROOT.parents[1]/'common'

def instance_for(out):
    """common/run.sh INSTANCE for a session directory: its path under tmp/ as a plain name."""
    try:rel=str(Path(out).resolve().relative_to(ROOT/'tmp'))
    except ValueError:rel=hashlib.sha256(str(out).encode()).hexdigest()[:12]
    return 'session-'+re.sub(r'[^A-Za-z0-9_-]','-',rel)[-60:]

def run_dir(out):
    return ROOT/'tmp/run'/instance_for(out)/'.run'

def launch_env(out,env=None):
    """The environment for common/run.sh, from the old harness launcher's variables."""
    e=dict(os.environ);e.update(env or {})
    e['GAME']=ROOT.name;e['INSTANCE']=instance_for(out)
    e.setdefault('SLAVE','original')
    if e['SLAVE']!='original':e['SLAVE']=str(Path(e['SLAVE']).resolve())
    if 'AMIGA_SETUP' in e and not e['AMIGA_SETUP']:
        del e['AMIGA_SETUP'];e['SETUP']='custom'
    if e.get('RR_PAD')=='1':e.setdefault('JOY1_MODE','cd32 gamepad')
    return e

def sock_for(out,name):
    """The server socket; relative to the current directory when the absolute path is
    over macOS's Unix socket limit (a deep checkout), so run tools from the game directory."""
    sock=str(run_dir(out)/f'{name}.sock')
    return sock if len(sock)<=100 else os.path.relpath(sock)

def server(out,name='rr',**kwargs):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    os.environ.update(launch_env(out))
    kwargs.setdefault('sock',sock_for(out,name))
    return Server(name,str(ROOT),run_script=str(COMMON/'run.sh'),run_dir=str(run_dir(out)),**kwargs)

if __name__=='__main__':
    if len(sys.argv)<3:sys.exit(__doc__)
    server(sys.argv[1]).main(sys.argv[2:])
