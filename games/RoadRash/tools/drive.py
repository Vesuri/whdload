#!/usr/bin/env python3
"""Drive Road Rash into a race and profile it, on the private native FS-UAE (tools/build-fsuae.sh).

  python3 tools/drive.py OUT shots      boot, take a shot every STEP fields up to TOTAL, pressing
                                        fire at the fields in FIRES=a,b,... (find the route timing)
  python3 tools/drive.py OUT race       route: fire on intro, title, joystick screen; wait for the
                                        race; then profile PROFILE fields with joystick up held

Route (user): fire in the intro, fire on the title, fire on the joystick screen, wait for the game.
Input goes through `monitor input JOY2_* 0|1` (joystick in game port 2, JOY1 is the mouse port). Runs are WARP=1 DETERMINISTIC=1,
so field counts are repeatable. Each step's screenshot lands in OUT; the profile is OUT/prof-NN.bin
(100-field Barto chunks) reduced to OUT/profile.pkl.gz.
Environment: AMIGA_SETUP (default a1200-fast, the game's SETUP), SLAVE (default: the shipped
slave), and the timings below. The run is OUT's common/run.sh instance (tools/rr.py).
"""
import json,os,sys,signal,hashlib
from pathlib import Path
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev.gdbserve import Server,require_harness
from amigaxdev import barto
from amigaxdev.callprofile import Reduction
from rr import COMMON,launch_env,run_dir,sock_for
ROOT=Path(__file__).resolve().parents[1]
FSUAE=ROOT/'tmp/emulator/fs-uae'
E=lambda k,d:int(os.environ.get(k,d))

class Session:
    def __init__(self,out):
        self.out=Path(out).resolve();self.out.mkdir(parents=True,exist_ok=True)
        # common/run.sh as this OUT's own instance; self.run is its run directory.
        self.run=run_dir(self.out)
        self.s=Server('rrdrive',str(ROOT),run_script=str(COMMON/'run.sh'),run_dir=str(self.run),sock=sock_for(self.out,'rrdrive'),profile_window=False)
        env=dict(FSUAE=os.environ.get('FSUAE',str(FSUAE)),WARP='1',DETERMINISTIC='1',JOY0='none',JOY1=os.environ.get('RR_JOY1','none'),WINDOW='none',FSUAE_CLAIM_STRICT='1')
        env=launch_env(self.out,env)
        self.g=self.s.boot(env);self.field=0;self.log=[]
        # The pinned original private build predates capability discovery, but
        # its fields/input commands have been validated against game counters.
        legacy={
            'ee8e2f41e49021d7377d2adf782ebaff6a99fc49df57e6007d86b862bcf7cbc3',
            # Private passive RAM-read build: 44 normal matrix runs, MMU and
            # per-step capture checks recorded in simulation-timing.md.
            'e0b2532ace1de7dd4d66d811488ec67ea7080b9991ee57e7190d8e31483f99cc',
        }
        if hashlib.sha256(Path(env['FSUAE']).read_bytes()).hexdigest() not in legacy:
            try:require_harness(self.g,'fields','input')
            except Exception:self.quit();raise
        actual=(self.run/'fsuae/Cache/Logs/debug.uae').read_text()
        for var,key in [('RR_EXPECT_CPU','cpu_model'),('RR_EXPECT_MMU','mmu_model')]:
            if var in os.environ and f'{key}={os.environ[var]}\n' not in actual:
                # UAE omits mmu_model entirely when it is zero.
                if key=='mmu_model' and os.environ[var]=='0' and '\nmmu_model=' not in actual:continue
                self.quit();raise RuntimeError(f'effective {key} does not match {os.environ[var]}')
    def cmd(self,text,timeout=600):
        r=self.g.cmd(text,timeout=timeout)
        if any(x in r for x in ('Remote failure reply','not supported','Undefined command','Protocol error','Cannot access memory')):raise RuntimeError(f'{text}: {r}')
        return r
    def fields(self,n):
        while n>0:
            k=min(n,6000);self.cmd(f'monitor fields {k}',timeout=3600);self.field+=k;n-=k
    def input(self,event,v):
        self.cmd(f'monitor input {event} {v}');self.log.append((self.field,event,v))
    def press(self,event,hold=5):
        self.input(event,1);self.fields(hold);self.input(event,0)
    def shot(self,name):
        p=self.run/'shot.bin';self.cmd(f'monitor profile 1 "" "{p}"',timeout=1800);self.field+=1
        f=barto.load(str(p)).fields[-1];(self.out/name).write_bytes(f.shot);os.unlink(p)
        print(f'field {self.field}: {name}',flush=True)
    def quit(self):
        self.g.p.kill();self.g.p.wait()
        try:os.kill(int((self.run/'fsuae.pid').read_text()),signal.SIGKILL)
        except ProcessLookupError:pass

def rd(s,addr,size=4):
    r=s.cmd(f'x/1{"w" if size==4 else "h"}x {addr:#x}')
    return int(r.split(':')[1].split()[0],16)

def to_race(s,settle=100,limit=8000):
    """Machine-independent route: press fire every 100 fields until the race's per-field hook
    ($a5916 = $87040) runs, then wait until the race field counter $a5d4c reaches SETTLE."""
    while s.field<limit:
        if rd(s,0xa5916)==0x87040 and rd(s,0xa5d4c)>=settle:
            s.shot('4-race.png');return
        if rd(s,0xa5916)!=0x87040:s.press('JOY2_FIRE_BUTTON')
        s.fields(95)
    s.shot('race-not-reached.png');raise RuntimeError('race not reached')

def shots(s):
    step,total=E('STEP',100),E('TOTAL',3000)
    fires=sorted(int(x) for x in os.environ.get('FIRES','').split(',') if x)
    while s.field<total:
        n=min([step]+[f-s.field for f in fires if f>s.field])
        s.fields(n)
        if s.field in fires:s.press('JOY2_FIRE_BUTTON');print(f'fire at {s.field-5}',flush=True)
        else:s.shot(f'f{s.field+1:05d}.png')

def race(s):
    # Defaults: fire at fields 900, 1700, 1900; the race clock starts ~3200; profile from 3300.
    s.fields(E('INTRO',899));s.shot('1-intro.png');s.press('JOY2_FIRE_BUTTON')
    s.fields(E('TITLE',794));s.shot('2-title.png');s.press('JOY2_FIRE_BUTTON')
    s.fields(E('JOYSCREEN',194));s.shot('3-joystick.png');s.press('JOY2_FIRE_BUTTON')
    s.fields(E('LOAD',1394));s.shot('4-race.png')
    n=E('PROFILE',500);red=Reduction()
    s.input('JOY2_UP',1);start=s.field
    for i in range(0,n,100):
        p=s.out/f'prof-{i//100:02d}.bin'
        s.cmd(f'monitor profile {min(100,n-i)} "" "{p}"',timeout=3600);s.field+=min(100,n-i)
        t=red.feed(str(p));(s.out/f'prof-{i//100:02d}.png').write_bytes(t.fields[-1].shot)
        if not os.environ.get('KEEP'):os.unlink(p)
        print(f'profiled fields {start}..{s.field}',flush=True)
    s.input('JOY2_UP',0);red.save(str(s.out/'profile.pkl.gz'));s.shot('5-after.png')

if __name__=='__main__':
    if len(sys.argv)!=3 or sys.argv[2] not in ('shots','race'):sys.exit(__doc__)
    s=Session(sys.argv[1])
    try:{'shots':shots,'race':race}[sys.argv[2]](s)
    finally:
        (s.out/'inputs.json').write_text(json.dumps(s.log)+'\n');s.quit()
