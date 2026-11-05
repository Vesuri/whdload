#!/usr/bin/env python3
"""Gunship harness session on a native FS-UAE with the harness commands (monitor key/fields).

Library: Session(out, env) with key(), fields(), shot(), profile(), read(), quit().
Each session boots common/run.sh as its own instance (tmp/run/<instance>/, named after `out`
under tmp/), so it has its own runtime copy and gdb-stub port and leaves an interactive
`make run` window alone. Without SLAVE it boots the shipped slave (SLAVE=original);
SLAVE=path (environment) boots a rebuilt slave; GUNSHIP_FSUAE picks another native build.
"""
import hashlib,os,re,subprocess,sys,tempfile
from pathlib import Path
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev.gdbserve import Server,require_harness
from amigaxdev import barto
ROOT=Path(__file__).resolve().parents[1]
COMMON=ROOT.parents[1]/'common'
def instance_for(out):
    """common/run.sh INSTANCE for a session directory: its path under tmp/ as a plain name."""
    try:rel=str(out.relative_to(ROOT/'tmp'))
    except ValueError:rel=hashlib.sha256(str(out).encode()).hexdigest()[:12]
    return 'session-'+re.sub(r'[^A-Za-z0-9_-]','-',rel)
# The menus need the mouse: AmigaXDev's native builds have `monitor mouse` and `monitor input`
# (Session checks with require_harness). GUNSHIP_FSUAE picks another build, e.g. fs-uae-aprof.
FSUAE=os.environ.get('GUNSHIP_FSUAE') or os.path.join(os.environ['AMIGA_SHARE'],'fs-uae-arm/fs-uae')
BUTTONS={1:'JOY1_FIRE_BUTTON',2:'JOY1_2ND_BUTTON'}  # port-0 mouse
# Profiling machines. a500-fast is the game's default (game.conf SETUP, game.sh game_prepare);
# the 030/040/060 entries are cycle-exact
# cores without an MMU model (aprof needs that), on the a1200-fast base so the memory layout
# stays the same. EXTRA_ARGS goes first on FS-UAE's command line, so it overrides the setup.
# --uae_uaeboard=full+indirect (the shared setups' choice for data caches) hangs this build at
# reset; with PRELOAD the directory drives work without it.
CE=' --uae_cpu_data_cache=true'
MACHINES={
    'a500-fast':dict(AMIGA_SETUP='a500-fast'),
    'a1200-fast':dict(AMIGA_SETUP='a1200-fast'),
    'a1200-030':dict(AMIGA_SETUP='a1200-fast',EXTRA_ARGS='--cpu=68EC030 --uae_cpu_frequency=50000000'+CE),
    'a1200-040':dict(AMIGA_SETUP='a1200-fast',EXTRA_ARGS='--cpu=68040-NOMMU --uae_cpu_frequency=25000000'+CE),
    'a1200-060':dict(AMIGA_SETUP='a1200-fast',EXTRA_ARGS='--cpu=68060-NOMMU --uae_cpu_frequency=50000000'+CE),
}
def machine():
    """Environment for $MACHINE (default: the caller's AMIGA_SETUP or SETUP, else the game's SETUP)."""
    m=os.environ.get('MACHINE')
    return dict(MACHINES[m]) if m else {}
# Amiga raw key codes.
KEYS=dict(up=0x4c,down=0x4d,right=0x4e,left=0x4f,shift=0x60,space=0x40,ret=0x44,esc=0x45,
          n1=0x01,n2=0x02,n3=0x03,n4=0x04,tab=0x42,lamiga=0x66,lalt=0x64,f1=0x50,f2=0x51,f3=0x52,f4=0x53,f5=0x54,f6=0x55,f7=0x56,f8=0x57,f9=0x58,f10=0x59)

class Session:
    def __init__(self,out,env=None):
        self.out=Path(out).resolve();self.out.mkdir(parents=True,exist_ok=True)
        self.instance=instance_for(self.out);self.run=ROOT/'tmp/run'/self.instance/'.run'
        self.s=Server('gunship',str(ROOT),run_script=str(COMMON/'run.sh'),run_dir=str(self.run),profile_window=False)
        base=dict(GAME=ROOT.name,INSTANCE=self.instance,SLAVE='original',FSUAE=FSUAE,WARP='1',DETERMINISTIC='1',JOY0='none',FSUAE_CLAIM_STRICT='1')
        if os.environ.get('SLAVE'):base['SLAVE']=str(Path(os.environ['SLAVE']).resolve())
        base.update(machine());base.update(env or {})
        self.g=self.s.boot(base);require_harness(self.g,"key","fields","mouse","input");self.field=0
    def cmd(self,text,timeout=600):
        r=self.g.cmd(text,timeout=timeout)
        checked=r.replace('FILESYS: EXALL called twice with ERROR_NO_MORE_ENTRIES','')
        if any(x in checked for x in ('ERROR','not supported','Undefined','Protocol error')):raise RuntimeError(r)
        return r
    def fields(self,n):
        if n>0:self.cmd(f'monitor fields {n}');self.field+=n
    def key(self,name,down):
        k=KEYS[name] if isinstance(name,str) else name
        self.cmd(f'monitor key {k:x} {int(down)}')
    def mouse(self,dx,dy):
        # Large moves in steps: the emulator feeds a delta to the counters over the field.
        while dx or dy:
            sx=max(-64,min(64,dx));sy=max(-64,min(64,dy))
            self.cmd(f'monitor mouse {sx} {sy}');self.fields(2);dx-=sx;dy-=sy
    def click(self,button=1,hold=4,after=4):
        self.cmd(f'monitor input {BUTTONS[button]} 1');self.fields(hold)
        self.cmd(f'monitor input {BUTTONS[button]} 0');self.fields(after)
    def tap(self,name,hold=3,after=3):
        self.key(name,1);self.fields(hold);self.key(name,0);self.fields(after)
    def shot(self,name):
        p=self.run/'shot.bin';self.cmd(f'monitor profile 1 "" "{p}"');self.field+=1
        f=barto.load(str(p)).fields[-1];(self.out/name).write_bytes(f.shot);return self.out/name
    def profile(self,n,path):
        r=self.cmd(f'monitor profile {n} "" "{Path(path).resolve()}"',timeout=3600);self.field+=n;return r
    def read(self,addr,n):
        # gdb's dump takes no quoted file name, and the worktree path may have spaces.
        fd,p=tempfile.mkstemp(prefix='gunship-mem-');os.close(fd)
        try:self.cmd(f'dump binary memory {p} {addr:#x} {addr+n:#x}');return Path(p).read_bytes()
        finally:os.unlink(p)
    def regs(self,names='pc'):return self.cmd('info registers '+names)
    def quit(self):
        try:self.g.cmd('kill',timeout=10)
        except Exception:pass
        # common/run.sh stop kills only the emulator this instance recorded.
        subprocess.run(['bash',str(COMMON/'run.sh'),'stop'],env=dict(os.environ,GAME=ROOT.name,INSTANCE=self.instance),capture_output=True)

sys.modules["gunship"]=sys.modules[__name__]
