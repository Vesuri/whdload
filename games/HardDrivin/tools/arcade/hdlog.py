"""Parse a hd.lua log: rows of (time, script time st, frame, tick, inputs[0x21], results[0x86], adc[12],
srf = (front, rear) surface types before plan.road; None in older logs)."""
import sys
def rows(path):
    t0=None
    for line in open(path):
        p=line.split()
        if p[0]=='T': t0=float(p[1])
        if p[0]=='E' and t0 is None and int(p[3])==1: t0=float(p[1])-16   # older logs: first event (coin) at 16
        if p[0]!='R': continue
        w=lambda s:[int(s[i:i+4],16) for i in range(0,len(s),4)]
        yield dict(t=float(p[1]),st=float(p[1])-t0,frame=int(p[2]),tick=int(p[3],16),
                   inp=w(p[4]),res=w(p[5]),adc=w(p[6]),
                   srf=(int(p[7][:2],16),int(p[7][2:],16)) if len(p)>7 else None)
def s16(v): return v-65536 if v&0x8000 else v
if __name__=='__main__':
    R=list(rows(sys.argv[1]))
    print(len(R),'rows')
    import collections
    dt=collections.Counter(round((b['t']-a['t'])*1000,1) for a,b in zip(R,R[1:]))
    print('interval ms',dt.most_common(8))
    dtick=collections.Counter((b['tick']-a['tick']) for a,b in zip(R,R[1:]))
    print('tick delta',dtick.most_common(8))
    print('input[0xa] (ticks) values',collections.Counter(r['inp'][0xa] for r in R).most_common(8))
    for r in R[::100]:
        print('%.3f'%r['t'],' '.join('%04x'%x for x in r['inp']))
