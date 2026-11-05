#!/usr/bin/env python3
"""One-line-per-machine summary of aprof_run.py captures: aprof_matrix.py RUN...

Columns: fps; simulation ticks/s; exec STOP idle; CPU spinning in the game's BBUSY wait loops;
level-3 interrupt time (exception-vector subtrees for vector 27); the swap +04496 (inclusive);
the 3D geometry routines (self) as the CPU-bound part.
"""
import ast,json,os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev import aprof
# btst/bne pairs of every BBUSY wait loop (frame.md/render3d.md/interrupts.md).
WAITS=[0x02D84,0x02D8A,0x02EFA,0x02F00,0x030C6,0x030CC,0x0319A,0x031A0,0x031E6,0x031EC,0x08626,0x0862C,
       0x088D8,0x088DE,0x08BD6,0x08BDC,0x08D3E,0x08D44,0x08D7A,0x08D80,0x09198,0x0919E,0x09242,0x09248,
       0x092F6,0x092FC,0x0933C,0x09342]
GEOM=[(0x0625C,0x063DC),(0x063DC,0x06504),(0x06642,0x06792),(0x06792,0x06984),(0x082EC,0x08466),(0x08466,0x084A0),(0x05EA4,0x05F8E),(0x05D62,0x05EA4)]
print(f'{"machine":12s} {"fps":>5s} {"tick/s":>6s} {"idle":>5s} {"bwait":>6s} {"L3irq":>6s} {"swap":>5s} {"geom":>5s}')
for run in sys.argv[1:]:
    L=json.load(open(os.path.join(run,'layout.json')));g=L['gamemule'];k=L['kick13']
    h,pcs,nodes=aprof.parse_profile(open(os.path.join(run,'window.prof')).read());tot=h['units']
    c0,c1=[ast.literal_eval(l.split(' ',1)[1]) for l in open(os.path.join(run,'clocks.txt')).read().splitlines()]
    F=c1['vbl']-c0['vbl'];T=c1['tick']-c0['tick'];fr=pcs.get(g+0x44ca,(0,0))[1]
    pct=lambda u:100*u/tot
    idle=pcs.get(k+0xf90,(0,))[0]
    bw=sum(pcs.get(g+o,(0,))[0] for o in WAITS)
    geom=sum(v[0] for pc,v in pcs.items() if any(g+a<=pc<g+b for a,b in GEOM))
    ch,order,incl=aprof.call_tree(nodes)
    irq=sum(incl[n] for n,v in nodes.items() if n and v[2]==27 and nodes[v[0]][2]!=27)
    swap=sum(incl[n] for n,v in nodes.items() if n and v[2]==0 and v[1]==g+0x4496)
    print(f'{os.path.basename(run.rstrip("/")):12s} {50*fr/F:5.1f} {50*T/F:6.2f} {pct(idle):4.1f}% {pct(bw):5.1f}% {pct(irq):5.1f}% {pct(swap):4.1f}% {pct(geom):4.1f}%')
