#!/usr/bin/env python3
"""B6 chip-bus budget from trace_at.py chunks: bus_budget.py TRDIR...

Every DMA slot (2 CPU cycles) has an owner: free, refresh, CPU, copper, audio, blitter,
bitplane, sprite, disk. Per window it prints the shares per field, then splits the slots into
three phases: in a blit (from a BLTSIZE write to the blit's last DMA slot), CPU running
outside blits, and CPU stopped outside blits (the frame wait's STOP-free busy loop counts as
running). The bound for overlapping CPU work with blits is the free slots inside blits against
the CPU's slot demand when it runs (CPU slots per slot while running; code and data are in
slow RAM, which is on the chip bus on an A500). C1's estimate with contention: a blit left
running beside the CPU gets only the free slots, so it progresses at rho = free share outside
blits / blitter share inside blits, and each blit saves min(length, rho x following CPU gap).
"""
import collections,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import _amigaxdev  # noqa: F401
from amigaxdev import barto
NAMES={0:'free',1:'refresh',2:'CPU',3:'copper',4:'audio',5:'blitter',6:'bitplane',7:'sprite',8:'disk'}
def run(d):
    d=Path(d);meta=json.loads((d/'meta.json').read_text())
    tot=collections.Counter();phase={k:collections.Counter() for k in ('blit','cpu','stop')};nf=0;gaps=[]
    for name,_,_ in meta['chunks']:
        t=barto.load(str(d/name))
        for f in t.fields:
            nf+=1;dm=f.dma;sz=f.dma_size;n=len(dm)//sz
            # CPU stopped per slot, from the instruction stream (pc None = STOP)
            stopped=bytearray(n);c=0
            for pc,cost,_ in t.instructions(f):
                if pc is None:
                    a,b=c//2,min(n,(c+cost)//2)
                    stopped[a:b]=b'\1'*(b-a)
                c+=cost
            starts=[];bl=[]
            for i in range(n):
                o=i*sz;typ=dm[o+29];tot[typ]+=1
                if typ==2 and dm[o+1]&1 and struct.unpack_from('<I',dm,o+12)[0]==0xdff058:starts.append(i)
                elif typ==5:bl.append(i)
            span=bytearray(n);j=0
            for k,st in enumerate(starts):
                nx=starts[k+1] if k+1<len(starts) else n;end=st
                while j<len(bl) and bl[j]<nx:
                    if bl[j]>=st:end=bl[j]
                    j+=1
                span[st:end+1]=b'\1'*(end+1-st)
                if end>st and nx<n:gaps.append((end-st,nx-end))
            for i in range(n):
                typ=dm[i*sz+29]
                phase['blit' if span[i] else 'stop' if stopped[i] else 'cpu'][typ]+=1
        del t
    return nf,tot,phase,gaps
if __name__=='__main__':
    for d in sys.argv[1:]:
        nf,tot,phase,gaps=run(d);n=sum(tot.values())
        print(f'== {d}: {nf} fields; per field: '+', '.join(f'{NAMES[k]} {v/n*100:.1f}%' for k,v in sorted(tot.items())))
        for ph,c in phase.items():
            m=sum(c.values()) or 1
            print(f'  {ph:5} {m/n*100:5.1f}% of slots: '+', '.join(f'{NAMES[k]} {v/m*100:.1f}%' for k,v in sorted(c.items())))
        cpu=phase['cpu'];m=sum(cpu.values()) or 1
        bl=phase['blit'];mb=sum(bl.values()) or 1
        dem=cpu[2]/m
        rho=(cpu[0]/m)/(bl[5]/mb)
        save=sum(min(L,rho*G) for L,G in gaps)/(n/nf)/nf
        print(f'  C1 with contention: a deferred blit beside the CPU gets the free slots, {rho:.2f} of its speed;'
              f' saving min(length, {rho:.2f} x gap) per blit = {save:.3f} fields per field ({save*4:.2f} per 4-field frame)')
        print(f'  CPU running uses {dem*100:.0f}% of slots; inside blits {bl[0]/mb*100:.0f}% are free, so CPU work overlapped with a blit runs at about {min(1,bl[0]/mb/dem)*100:.0f}% speed (before the blitter yields slots)')
