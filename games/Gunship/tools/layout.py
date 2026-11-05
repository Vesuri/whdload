#!/usr/bin/env python3
"""Locate the live gamemule hunks and the KickEmu Kickstart in a dump: layout.py MEMDIR

Writes MEMDIR/layout.json {gamemule, gamemule_data, hunks[0..8], kick13, launcher}. The live code hunk is
the voted base whose segment header (size longword at base-8) matches; PRELOAD file copies
vote higher but have no header. The data hunk is found by following the segment BPTR chain.
"""
import collections,json,os,struct,sys
FAST=0x200000
G=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','tmp/game/Gunship/data/')
M=b''
def l32(a):return struct.unpack('>I',M[a-FAST:a-FAST+4])[0]
def votes(blob):
    v=collections.Counter()
    for o in range(0,len(blob)-16,64):
        w=blob[o:o+16]
        if len(set(w))<6:continue
        i=M.find(w);k=0
        while i>=0 and k<20:v[FAST+i-o]+=1;i=M.find(w,i+1);k+=1
    return v
def live(name,off,ln):
    for b,c in votes(open(G+name,'rb').read()[off:off+ln]).most_common(8):
        if ln+8<=l32(b-8)<=ln+16:return b
    raise SystemExit(f'{name}: no live hunk')
def locate(mem):
    """Layout dict from a fast-RAM image ($200000-$A00000)."""
    global M
    M=mem
    code=live('gamemule',0x40,0xf0c8)
    seg=code-4;hunks=[]
    for i in range(9):hunks.append(seg+4);seg=l32(seg)*4
    data=hunks[6]
    kick=None
    K=open(os.environ['KICK13'],'rb').read()
    i=M.find(K[0x1000:0x1020]);kick=FAST+i-0x1000
    return dict(gamemule=code,gamemule_data=data,hunks=hunks,kick13=kick,launcher=live('Gunship',0x20,0x1c68))

if __name__=='__main__':
    MEM=sys.argv[1];out=locate(open(os.path.join(MEM,'fast.bin'),'rb').read())
    json.dump(out,open(os.path.join(MEM,'layout.json'),'w'));print({k:(hex(v) if isinstance(v,int) else [hex(x) for x in v]) for k,v in out.items()})
