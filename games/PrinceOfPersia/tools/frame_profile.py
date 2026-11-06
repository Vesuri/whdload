#!/usr/bin/env python3
"""B4 per-frame call profiles of a VERIFY tape.

    frame_profile.py run OUT TAPE FIRST_STEP FIELDS   trace and reduce -> OUT/frames.pkl.gz
    frame_profile.py cmp OUT [TOP]                    4-field frames against 5-9-field frames

Level-start frames (under g:$0ae38) are counted apart. A frame runs from one frame-wait exit (verify_wait_end) to the next: work, then the wait.
Per frame it keeps the period and work (fields), and the inclusive and self cycles of every routine
(call stacks rebuilt as in amigaxdev.callprofile; 'stop' is time in STOP under its caller,
'exception' the interrupt entry gaps). Traces go in chunks of 50 fields and are deleted.
"""
import collections,gzip,json,os,pickle,struct,sys
from pathlib import Path
os.environ.setdefault('SLAVE',os.path.join(os.path.dirname(os.path.abspath(__file__)),'../tmp/build/verify/PrinceOfPersia.Slave'))
from pop import Session
from verify import Verify
import _amigaxdev  # noqa: F401
from amigaxdev import barto
from amigaxdev.callprofile import _opkind
FIELD=142102   # CPU cycles per PAL field with the frequency fix

class Frames:
    def __init__(self,split,wait):
        self.split,self.wait=split,wait;self.frames=[];self.cur=None
        self.stack=();self.sps=();self.pend=0;self.pos=0
    def close(self):
        if self.cur:
            st=self.cur.pop('stacks');incl=collections.Counter();own=collections.Counter()
            for s,c in st.items():
                for fr in set(s):incl[fr]+=c
                if s:own[s[-1]]+=c
            self.cur['incl']=incl;self.cur['self']=own;self.cur['end']=self.pos;self.frames.append(self.cur)
    def feed(self,t):
        d,u,cache=t.data,struct.unpack_from,{}
        stack,sps,pend,pos=self.stack,self.sps,self.pend,self.pos
        for f in t.fields:
            off,end=f.insn_off,f.insn_end
            while off<end:
                pc=None
                while True:
                    v=u('<I',d,off)[0];off+=4
                    if v>=0xffff0000:break
                    if pc is None:pc=v
                c=0xffffffff-v;sp=u('<I',d,off+60)[0];off+=68;pos+=c
                cur=self.cur
                if pc is None:
                    if cur:cur['stacks'][stack+('stop',)]+=c
                    continue
                if pc==0x7fffffff:
                    pend=3
                    if cur:cur['stacks'][stack+('exception',)]+=c
                    continue
                while sps and sp>sps[-1]:stack,sps=stack[:-1],sps[:-1]
                if pend==1:stack,sps=stack+(pc,),sps+(sp,)
                elif pend==3:stack,sps=stack+(('irq',pc),),sps+(sp,)
                if pc==self.split:
                    self.pos=pos-c;self.close()
                    cur=self.cur=dict(start=pos-c,wait=None,stacks=collections.Counter())
                elif pc==self.wait and cur and cur['wait'] is None:cur['wait']=pos-c
                if cur:cur['stacks'][stack]+=c
                pend=_opkind(t,pc,cache)
        self.stack,self.sps,self.pend,self.pos=stack,sps,pend,pos

def run(out,tape,first,n):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    s=Session(out,dict(WHD_ARGS=f'CUSTOM4={tape} CUSTOM5=0'));v=Verify(s);tmp=out/'chunk.bin'
    try:
        while True:
            s.fields(25)
            try:v.addr('verify_block');break
            except RuntimeError:pass
        rb=struct.unpack('>I',s.read(v.live(v.sym['_reloc_base']),4))[0]
        fr=Frames(v.live(v.sym['verify_wait_end']),v.live(v.sym['verify_wait']))
        v.until_step(first);i=0
        while i<n:
            k=min(50,n-i);s.profile(k,tmp);fr.feed(barto.load(str(tmp)));tmp.unlink();i+=k
            print('traced',i,flush=True)
    finally:
        s.quit()
        if tmp.exists():tmp.unlink()
    with gzip.open(out/'frames.pkl.gz','wb') as f:
        pickle.dump(dict(reloc_base=rb,slave_at=v.live(0),first_step=first,frames=fr.frames),f)

def label(fr,rb,sl):
    if isinstance(fr,tuple):return 'IRQ '+label(fr[1],rb,sl)
    if isinstance(fr,str):return fr
    if rb<=fr<rb+0x45800:return f'g:${fr-rb+0x1000:05x}'
    if sl<=fr<sl+0x10000:return f'slave:${fr-sl:04x}'
    return f'${fr:06x}'

def cmp(out,top=25):
    with gzip.open(Path(out)/'frames.pkl.gz','rb') as f:D=pickle.load(f)
    rb,sl=D['reloc_base'],D['slave_at'];F=D['frames']
    for x in F:x['period']=(x['end']-x['start'])/FIELD;x['work']=((x['wait'] or x['end'])-x['start'])/FIELD
    # Frames under g:$0ae38 belong to the level-start sequence (its own loop at g:$0b882).
    start=rb+0xae38-0x1000;ls=[x for x in F if start in x['incl']];F=[x for x in F if start not in x['incl']]
    groups={'4':[x for x in F if round(x['period'])<=4],'5-9':[x for x in F if 5<=round(x['period'])<=9]}
    print(f"{len(F)} gameplay frames: {len(groups['4'])} of 4 fields, {len(groups['5-9'])} of 5-9, {sum(round(x['period'])>=10 for x in F)} of 10+;"
          f" {len(ls)} level-start frames (g:$0ae38), periods {sorted(collections.Counter(round(x['period']) for x in ls).items())}")
    mean=lambda g,k:sum(x['incl'].get(k,0) for x in g)/max(1,len(g))/FIELD
    for g in groups:print(f"  {g:4} work mean {sum(x['work'] for x in groups[g])/max(1,len(groups[g])):.2f} fields")
    keys=set().union(*(x['incl'] for x in F))
    rows=sorted(((mean(groups["5-9"],k)-mean(groups["4"],k),k) for k in keys),key=lambda r:-r[0])
    print(f"{'routine':24} {'4':>6} {'5-9':>6} {'grows':>6}   (inclusive fields per frame)")
    for dlt,k in rows[:top]:print(f"{label(k,rb,sl):24} {mean(groups['4'],k):6.2f} {mean(groups['5-9'],k):6.2f} {dlt:6.2f}")

if __name__=='__main__':
    if sys.argv[1]=='run':run(sys.argv[2],sys.argv[3],int(sys.argv[4]),int(sys.argv[5]))
    else:cmp(sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 25)
