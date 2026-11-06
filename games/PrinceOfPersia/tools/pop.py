#!/usr/bin/env python3
"""Prince of Persia harness: the gdb-stub server, and capture sessions on the native FS-UAE.

    python3 tools/pop.py serve          boot (common/run.sh DEBUG=1), attach gdb, listen
    python3 tools/pop.py <command...>   one command to the running server (shot, wait, quit...)

The run options of common/run.sh (SETUP, BUILD, SLAVE, WHD_ARGS, POP_VERSION, INSTANCE, ...)
apply to serve.

Library for the capture tools: Session(out, env) with key(), fields(), shot(), profile(),
read(), quit(). Each session is a common/run.sh INSTANCE named after its output directory
(under tmp/), whose .run links to the instance's run directory. It boots the private native
FS-UAE in tmp/native-emulator/ (monitor key/fields; it profiles the full 24-bit window, so no
lldb fix is needed), or POP_FSUAE=PATH. It boots SLAVE=path (environment), SLAVE=original
(the shipped slave) or by default the existing release build (make slave; the VERIFY tools
default to make verify's); the listing beside it (tmp/build/<BUILD>/PrinceOfPersia.lst)
gives the symbols. The machine is a500-1.5m, warp, deterministic, with port 0 empty.
"""
import hashlib,os,re,subprocess,sys,tempfile
from pathlib import Path
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev import barto
ROOT=Path(__file__).resolve().parents[1]
os.environ['GAME']=ROOT.name
sys.path.insert(0,str(ROOT.parents[1]/'common/tools'))
from game_server import game_server  # noqa: E402
RELEASE=ROOT/'tmp/build/release/PrinceOfPersia.Slave'
VERIFY=ROOT/'tmp/build/verify/PrinceOfPersia.Slave'
# POP_FSUAE selects another build with the harness commands (AmigaXDev's native builds have them).
FSUAE=Path(os.environ.get('POP_FSUAE') or ROOT/'tmp/native-emulator/fs-uae')
FSUAE_SHA=None if os.environ.get('POP_FSUAE') else '3627080a0932fac3c546edf67c611b6fba57cdf1355a08868732606bd82e1c27'
# The booted slave: SLAVE=path, SLAVE=original (the shipped 4.4, no listing), else the
# release build. In the fork's harness the default build equalled the shipped slave.
SLAVE_ENV=os.environ.get('SLAVE','')
SLAVE=Path(SLAVE_ENV if SLAVE_ENV not in ('','original') else RELEASE).resolve()
# Amiga raw key codes.
KEYS=dict(kp4=0x2d,kp6=0x2f,kp8=0x3e,kp2=0x1e,kp7=0x3d,kp9=0x3f,ctrl=0x63,k=0x35,up=0x4c,down=0x4d,right=0x4e,left=0x4f,shift=0x60,space=0x40,ret=0x44,esc=0x45)

def instance_of(out):
    """The common/run.sh INSTANCE for an output directory under tmp/."""
    return re.sub(r'[^A-Za-z0-9_-]+','-',str(Path(out).resolve().relative_to(ROOT/'tmp'))).strip('-')

class Session:
    def __init__(self,out,env):
        if FSUAE_SHA and hashlib.sha256(FSUAE.read_bytes()).hexdigest()!=FSUAE_SHA:raise RuntimeError('native FS-UAE changed')
        self.out=Path(out).resolve();self.out.mkdir(parents=True,exist_ok=True)
        self.instance=instance_of(self.out);os.environ['INSTANCE']=self.instance
        self.s=game_server('pop',profile_window=False)
        run=ROOT/'tmp/run'/self.instance/'.run';run.mkdir(parents=True,exist_ok=True)
        link=self.out/'.run'
        if not link.is_symlink():link.symlink_to(os.path.relpath(run,self.out))
        base=dict(FSUAE=str(FSUAE),SETUP='a500-1.5m',WARP='1',DETERMINISTIC='1',JOY0='none',FSUAE_CLAIM_STRICT='1',
                  INSTANCE=self.instance,SLAVE='original' if SLAVE_ENV=='original' else str(SLAVE))
        base.update(env)
        self.g=self.s.boot(base);self.field=0
    def cmd(self,text,timeout=600):
        r=self.g.cmd(text,timeout=timeout)
        checked=r.replace('FILESYS: EXALL called twice with ERROR_NO_MORE_ENTRIES','')
        if any(x in checked for x in ('ERROR','not supported','Undefined')):raise RuntimeError(r)
        return r
    def fields(self,n):
        if n>0:self.cmd(f'monitor fields {n}');self.field+=n
    def key(self,name,down):
        k=KEYS[name] if isinstance(name,str) else name
        self.cmd(f'monitor key {k:x} {int(down)}')
    def shot(self,name):
        p=self.out/'.run/shot.bin';self.cmd(f'monitor profile 1 "" "{p}"');self.field+=1
        f=barto.load(str(p)).fields[-1];(self.out/name).write_bytes(f.shot);return self.out/name
    def profile(self,n,path):
        r=self.cmd(f'monitor profile {n} "" "{Path(path).resolve()}"',timeout=3600);self.field+=n;return r
    def read(self,addr,n):
        # gdb's dump takes no quoted file name, so the game directory's path must have no spaces.
        (ROOT/'tmp').mkdir(exist_ok=True)
        fd,p=tempfile.mkstemp(prefix='pop-mem-',dir=ROOT/'tmp');os.close(fd)
        if ' ' in p:raise RuntimeError(f'gdb dump cannot write to a path with spaces: {p}')
        try:self.cmd(f'dump binary memory {p} {addr:#x} {addr+n:#x}');return Path(p).read_bytes()
        finally:os.unlink(p)
    def find(self,probe,ranges=((0xc00000,0x180000),(0,0x80000)),ok=lambda a:True):
        """Address of the first probe (bytes) in slow then chip memory for which ok(addr), or None."""
        for a,n in ranges:
            m=self.read(a,n);i=m.find(probe)
            while i>=0:
                if ok(a+i):return a+i
                i=m.find(probe,i+1)
    def regs(self,names='pc'):return self.cmd('info registers '+names)
    def quit(self):
        try:self.g.p.terminate();self.g.p.wait(timeout=5)
        except Exception:pass
        # common/run.sh stop stops only the emulator this instance started.
        subprocess.run(['bash',str(ROOT.parents[1]/'common/run.sh'),'stop'],cwd=ROOT,
                       env=dict(os.environ,GAME=ROOT.name,INSTANCE=self.instance),check=False)

def symbols(slave=SLAVE):
    """Label -> offset in the slave, from the vasm listing beside it."""
    lst=Path(slave).with_suffix('.lst').read_bytes().decode('latin-1')
    out={}
    for line in lst.split('Symbols by name:')[1].split('Symbols by value:')[0].splitlines():
        m=re.match(r'(\S+)\s+00:([0-9A-F]{8})$',line.strip())
        if m:out[m[1]]=int(m[2],16)
    return out

if __name__=='__main__':
    game_server('pop').main(sys.argv[1:])
