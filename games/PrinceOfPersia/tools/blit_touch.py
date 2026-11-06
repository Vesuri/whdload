#!/usr/bin/env python3
"""B2: CPU accesses to a blit's memory before the next blit starts: blit_touch.py TRDIR...

Reads trace_at.py chunks. A blit starts at a CPU write to BLTSIZE ($dff058) and runs to the
next one. Its memory is the set of words its D channel wrote and its A/B/C channels read
(DMA records: type 5, address at offset 12). A hazard for deferring the blitter wait is a CPU
data access (type 2, extra 1) to a word of the blit's D, or a CPU write to a word of its
A/B/C, between the blit's start and the next one's. Each hazard is reported by the PC of
the instruction running at that slot (slot = cycle / 2 within a field) and the call site of
the blit-start routine (`g:$053a2` or `g:$053d6`, the only BLTSIZE writers). Also prints, per
call site, the blit count and the buffers its D channel wrote, and C1's bound: with the wait
moved to the next blit start, each blit saves min(its length, the CPU time to the next start)
(bus contention ignored), reported in fields per traced field.
"""
import bisect,collections,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import _amigaxdev  # noqa: F401
from amigaxdev import barto
REC=struct.Struct('<HQHI')

def label(pc,rb,sl):
    if pc is None:return 'STOP'
    if pc==0x7fffffff:return 'exc'
    if rb<=pc<rb+0x45800:return f'g:${pc-rb+0x1000:05x}'
    if sl<=pc<sl+0x10000:return f'slave:${pc-sl:04x}'
    return f'${pc:06x}'

BUFFERS=((0x49fee,'buf0'),(0x53c2e,'buf1'),(0x5d86e,'buf2'))
def where(a):
    for b,n in BUFFERS:
        if b<=a<b+40000:return n
    return f'${a&~0xfff:05x}'
def run(dirs):
    saves=[];hz=collections.Counter();starts=collections.Counter();nblits=0;examples={};dst=collections.defaultdict(collections.Counter)
    for d in dirs:
        d=Path(d);meta=json.loads((d/'meta.json').read_text());rb,sl=meta['reloc_base'],meta['slave_at']
        cur=None;site=None   # current blit: dict(start=call site, d=set, src=set)
        spans=[]             # (start slot, last blitter slot), slots counted across fields
        for name,first,_ in meta['chunks']:
            t=barto.load(str(d/name))
            for fi,f in enumerate(t.fields):
                base=(first+fi)*(len(f.dma)//f.dma_size)
                # slot -> pc of the instruction running then
                pcs=[];c=0;entries=[]   # (cycle, call site) at each blit-start routine entry
                for pc,cost,_ in t.instructions(f):
                    if pc in (rb+0x53a2-0x1000,rb+0x53d6-0x1000) and pcs:entries.append((c,pcs[-1][1]))
                    pcs.append((c,pc));c+=cost
                keys=[k for k,_ in pcs]
                ekeys=[k for k,_ in entries]
                def site_at(slot):
                    i=bisect.bisect_right(ekeys,slot*2)-1
                    return entries[i][1] if i>=0 else site
                def pc_at(slot):
                    i=bisect.bisect_right(keys,slot*2)-1
                    return pcs[i][1] if i>=0 else None
                dm=f.dma;sz=f.dma_size
                for i in range(0,len(dm),sz):
                    typ=dm[i+29]
                    if typ==2:
                        reg,dat,size,addr=REC.unpack_from(dm,i)
                        if addr==0xdff058 and reg&0x100:
                            if cur:
                                for a in cur['d']:dst[cur['start']][where(a)]+=1
                            spans.append([base+i//sz,None])
                            site=site_at(i//sz);cur=dict(start=label(site,rb,sl),d=set(),src=set());nblits+=1
                            starts[cur['start']]+=1;continue
                        if cur is None or dm[i+31]!=1 or addr>=0x80000:continue
                        w=addr&~1;write=bool(reg&0x100)
                        if w in cur['d'] or (write and w in cur['src']):
                            k=(cur['start'],label(pc_at(i//sz),rb,sl),'D' if w in cur['d'] else 'src','w' if write else 'r')
                            hz[k]+=1;examples.setdefault(k,hex(addr))
                    elif typ==5 and cur is not None:
                        reg,dat,size,addr=REC.unpack_from(dm,i)
                        (cur['d'] if reg==0 else cur['src']).add(addr&~1);spans[-1][1]=base+i//sz
            del t
        nf=sum(k for _,_,k in meta['chunks'])
        save=sum(min(e-b,spans[j+1][0]-e) for j,(b,e) in enumerate(spans[:-1]) if e)
        busy=sum(e-b for b,e in spans if e)
        saves.append((d.name,nf,len(spans),busy/71051/nf,save/71051/nf))
    return nblits,starts,hz,examples,dst,saves

if __name__=='__main__':
    n,starts,hz,ex,dst,saves=run(sys.argv[1:])
    for name,nf,nb,busy,save in saves:
        print(f'{name}: {nf} fields, {nb} blits; blitter busy {busy:.2f} fields/field, C1 saves up to {save:.2f}')
    print('blits',n)
    for k,v in sorted(starts.items()):print(f'  {k}: {v} blits, D words in',dict(dst[k].most_common(4)))
    print('hazards (blit started at, CPU access at, which memory, r/w): count, example address')
    for k,v in hz.most_common():print(' ',k,v,ex[k])
