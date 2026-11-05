#!/usr/bin/env python3
"""Phase/routine/wait/DMA attribution of one render_trace_case.py capture.

Phases come from the PC of the main loop and render-function bodies (callees inherit the
phase of their caller). Exclusive cycles go to the nearest routine start (sim LINK A5 or
observed call target; slave listing symbols). Blitter polls are instructions that read
DMACONR, plus the conditional branch that follows one. DMA slot shares are aligned to
instructions by cumulative cycle position within each field (approximate, per field).
Usage: python3 tools/render_trace_report.py CAPTURE_DIR [--json OUT]
"""
import argparse,bisect,collections,json,re,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import _amigaxdev  # noqa: F401
from amigaxdev import barto

DMA={0:'free',1:'refresh',2:'CPU',3:'copper',4:'audio',5:'blitter',6:'bitplane',7:'sprite',8:'disk'}
# Render function 0056c body ranges; main loop body 21d28-21f32.
STAGES=[(0x56c,'render-pre'),(0x5fe,'background'),(0x6bc,'scene'),(0x7c4,'cockpit'),
        (0x830,'messages'),(0xafe,'publication'),(0xb10,'render-post'),(0xb80,None)]
LOOP=(0x21d28,0x21f32)
WORLD=0x1098
FRAME=0x21d30

def main():
    p=argparse.ArgumentParser();p.add_argument('cap',type=Path);p.add_argument('--json',type=Path)
    p.add_argument('--top',type=int,default=14);a=p.parse_args()
    meta=json.loads((a.cap/'entry.json').read_text());sim=meta['sim']
    banks=[]
    for lo,hi in meta['regions']:
        f=a.cap/f'ram-{lo:x}.bin'
        if f.exists():banks.append((lo,f.read_bytes()))
    def read(addr,n):
        for lo,b in banks:
            if lo<=addr and addr+n<=lo+len(b):return b[addr-lo:addr-lo+n]
        return None
    def word(addr):
        b=read(addr,2);return struct.unpack('>H',b)[0] if b else None
    def long(addr):
        b=read(addr,4);return struct.unpack('>I',b)[0] if b else None
    # Regions: sim hunk 0 from its segment length; slave from its code bytes.
    simlen=long(sim-8)*4-8 if long(sim-8) else 0x3e384
    slave=(a.cap/'slave.slave').read_bytes();code=slave[32:32+256]
    slave_base=None
    for lo,b in banks:
        i=b.find(code)
        if i>=0:slave_base=lo+i;break
    syms=[]
    lst=(a.cap/'slave.lst').read_bytes().decode('latin1')
    if 'Symbols by value:' in lst:
        for m in re.finditer(r'^([0-9A-F]{8}) ([A-Za-z_][\w.]*)$',lst.split('Symbols by value:',1)[1],re.M):
            v=int(m.group(1),16)
            if v<len(slave):syms.append((v,m.group(2)))
    syms.sort();symv=[v for v,_ in syms]
    starts=set(x for x in range(sim,sim+simlen,2) if word(x)==0x4e55)
    trace=barto.load(a.cap/'trace.bin')
    def name(pc):
        if pc is None:return '[stopped]'
        if pc==0x7fffffff:return '[irq entry]'
        if sim<=pc<sim+simlen:
            i=bisect.bisect_right(order,pc)-1
            return f'sim:{order[i]-sim:05x}' if i>=0 else f'sim:{pc-sim:05x}'
        if slave_base and slave_base<=pc<slave_base+len(slave):
            i=bisect.bisect_right(symv,pc-slave_base)-1
            return 'slave:'+(syms[i][1] if i>=0 else f'{pc-slave_base:x}')
        if pc>=0xf80000:return 'rom'
        return 'other'
    # Main context = stack holding most cycles (SP page groups, as redbaron_report.py).
    pages=collections.Counter()
    for f in trace.fields[:6]:
        for pc,cost,r in trace.instructions(f):pages[r[15]>>12]+=cost
    groups,cur=[],[]
    for pg in sorted(pages):
        if cur and pg-cur[-1]>2:groups.append(cur);cur=[]
        cur.append(pg)
    groups.append(cur);groups.sort(key=lambda g:-sum(pages[x] for x in g))
    mlo,mhi=groups[0][0]<<12,(groups[0][-1]+2)<<12
    # Pass 1: discover call targets for routine starts.
    for f in trace.fields:
        pend=None
        for pc,cost,r in trace.instructions(f):
            if pc is None or pc==0x7fffffff:pend=None;continue
            if pend is not None and r[15]==pend-4 and sim<=pc<sim+simlen:
                t=long(pc+2) if word(pc)==0x4ef9 else pc
                if t and sim<=t<sim+simlen:starts.add(t)
            pend=None
            op=word(pc)
            if op is not None and ((op&0xff00)==0x6100 or (op&0xffc0)==0x4e80):pend=r[15]
    order=sorted(starts)
    def ea_reads_dmaconr(pc,r):
        op=word(pc)
        if op is None:return False
        # btst #n,<ea> / btst Dn,<ea> / tst.b|w <ea> reading DMACONR
        if (op&0xffc0)==0x0800 or (op&0xf1c0)==0x0100 or (op&0xffc0) in (0x4a00,0x4a40):
            mode,reg=(op>>3)&7,op&7;ext=4 if (op&0xffc0)==0x0800 else 2
            if mode==2:ea=r[8+reg]
            elif mode==5:ea=(r[8+reg]+struct.unpack('>h',read(pc+ext,2) or b'\0\0')[0])&0xffffffff
            elif mode==7 and reg==1:ea=long(pc+ext)
            elif mode==7 and reg==0:ea=struct.unpack('>h',read(pc+ext,2) or b'\0\0')[0]&0xffffff
            else:return False
            return ea in (0xdff002,0xdff003)
        return False
    phase='loop';frames=0;world_calls=0
    cyc=collections.Counter();waits=collections.Counter();irq=collections.Counter()
    fn=collections.defaultdict(collections.Counter);fnwait=collections.defaultdict(collections.Counter)
    slots=collections.defaultdict(collections.Counter);fieldcyc=[]
    frame_fields=[]
    for f in trace.fields:
        recs=[pc_cost for pc_cost in trace.instructions(f)]
        tot=sum(c for _,c,_ in recs) or 1;fieldcyc.append(tot)
        dmat=bytes(f.dma[29::f.dma_size]);nd=len(dmat)
        pos=0;prev_poll=False
        for pc,cost,r in recs:
            main_ctx=mlo<=r[15]<mhi and pc not in (None,0x7fffffff)
            if main_ctx and sim<=pc<sim+simlen:
                o=pc-sim
                if LOOP[0]<=o<LOOP[1]:phase='loop'
                elif STAGES[0][0]<=o<STAGES[-1][0]:
                    for (lo,nm),(hi,_) in zip(STAGES,STAGES[1:]):
                        if lo<=o<hi:phase=nm;break
                if o==WORLD:phase='world';world_calls+=1
                if o==FRAME:frames+=1;frame_fields.append(f.index)
            ph=phase if main_ctx else 'irq'
            if not main_ctx:irq[name(pc)]+=cost
            cyc[ph]+=cost
            k=name(pc);fn[ph][k]+=cost
            if pc not in (None,0x7fffffff):
                isp=ea_reads_dmaconr(pc,r)
                op=word(pc) or 0
                isbr=prev_poll and (op&0xfe00)==0x6600
                if isp or isbr:waits[ph]+=cost;fnwait[ph][k]+=cost
                prev_poll=isp
            lo_s=pos*nd//tot;pos+=cost;hi_s=pos*nd//tot
            if hi_s>lo_s:slots[ph].update(dmat[lo_s:hi_s])
    nf=len(trace.fields);field=sum(fieldcyc)/nf
    ms=lambda c:c/field*20.0
    total=sum(cyc.values())
    frames_obs=max(frames-1,1)
    span=(frame_fields[-1]-frame_fields[0]) if len(frame_fields)>1 else nf
    print(f'# {a.cap}: {nf} fields, {frames} frame anchors, {world_calls} world calls; '
          f'{span/frames_obs:.2f} fields/frame between first/last anchor ({50*frames_obs/span:.2f} FPS)')
    print(f'slave base {slave_base:#x}' if slave_base else 'slave not located', f'sim {sim:#x}+{simlen:#x}; cycles/field {field:.0f}')
    print('\n## Phases (ms per frame over the whole capture; % of all cycles)')
    print(f'{"phase":13}{"ms/frame":>9}{"%":>6}{"wait ms":>8}  DMA slots during phase')
    order_ph=['loop','world','render-pre','background','scene','cockpit','messages','publication','render-post','irq']
    out={}
    for ph in order_ph:
        c=cyc.get(ph,0)
        if not c:continue
        sl=slots[ph];n=sum(sl.values()) or 1
        d=', '.join(f'{DMA.get(k,k)} {100*v/n:.0f}%' for k,v in sorted(sl.items()) if 100*v/n>=1)
        print(f'{ph:13}{ms(c)/frames_obs:9.2f}{100*c/total:6.1f}{ms(waits[ph])/frames_obs:8.2f}  {d}')
        out[ph]=dict(ms_per_frame=ms(c)/frames_obs,share=c/total,wait_ms=ms(waits[ph])/frames_obs,
                     dma={DMA.get(k,str(k)):v/n for k,v in sl.items()},
                     top=[(k,ms(v)/frames_obs) for k,v in fn[ph].most_common(a.top)],
                     wait_top=[(k,ms(v)/frames_obs) for k,v in fnwait[ph].most_common(8)])
    for ph in ('scene','cockpit','publication','world','irq','background','messages'):
        if ph not in out:continue
        print(f'\n## {ph}: exclusive ms/frame by routine (blitter-poll ms in brackets)')
        for k,v in fn[ph].most_common(a.top):
            w=fnwait[ph][k]
            print(f'{ms(v)/frames_obs:8.3f}  {k}'+(f'  [{ms(w)/frames_obs:.3f} poll]' if w else ''))
    allslots=collections.Counter()
    for f in trace.fields:allslots.update(bytes(f.dma[29::f.dma_size]))
    n=sum(allslots.values())
    print('\nAll DMA slots:',', '.join(f'{DMA.get(k,k)} {100*v/n:.1f}%' for k,v in sorted(allslots.items())))
    if a.json:a.json.write_text(json.dumps(dict(frames=frames,fields=nf,phases=out),indent=1)+'\n')

if __name__=='__main__':main()
