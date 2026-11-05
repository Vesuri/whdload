#!/usr/bin/env python3
"""Native converter oracle; hooks every write, checks output and guards.
Unicorn validates semantics, never performance. Game-derived fixtures stay in tmp/.
"""
import argparse, ctypes as C, hashlib, json, os, random, re, struct
from pathlib import Path
import numpy as np

P=C.c_void_p; I=C.c_int; Q=C.c_uint64; Z=C.c_size_t
u=C.CDLL(str(Path(os.environ['AMIGA_UNICORN'])/'lib/libunicorn.2.dylib'))
for name,args in {'uc_open':[I,I,C.POINTER(P)],'uc_ctl':[P,C.c_uint32],
 'uc_mem_map':[P,Q,Q,C.c_uint32],'uc_mem_write':[P,Q,P,Z],'uc_mem_read':[P,Q,P,Z],
 'uc_reg_write':[P,I,P],'uc_reg_read':[P,I,P],'uc_emu_start':[P,Q,Q,Q,Z],
 'uc_close':[P],'uc_hook_add':[P,C.POINTER(Z),I,P,P,Q,Q]}.items():
    getattr(u,name).argtypes=args; getattr(u,name).restype=I
u.uc_strerror.argtypes=[I]; u.uc_strerror.restype=C.c_char_p
BASE=0x10000; SRC=0x40000; DST=0x60000; STACK=0x90000; STOP=0x1000

def ck(e):
    if e: raise RuntimeError(u.uc_strerror(e).decode())

class CPU:
    def __init__(self,blob,model):
        self.selected=None; self.forced=0
        self.h=P(); ck(u.uc_open(7,1<<30,C.byref(self.h)))
        ck(u.uc_ctl(self.h,7|(1<<26)|(1<<30),I(model)))
        ck(u.uc_mem_map(self.h,0,0x100000,7)); self.write(BASE,blob)
        self.reg(17,0x2700)
        self.writes=[]
        def hook(h,kind,address,size,value,data): self.writes.append((address,size))
        self.callback=C.CFUNCTYPE(None,P,I,Q,I,C.c_int64,P)(hook)
        handle=Z(); ck(u.uc_hook_add(self.h,C.byref(handle),1<<11,self.callback,None,1,0))
    def write(self,a,b): ck(u.uc_mem_write(self.h,a,b,len(b)))
    def read(self,a,n):
        b=C.create_string_buffer(n); ck(u.uc_mem_read(self.h,a,b,n)); return b.raw
    def reg(self,r,v=None):
        x=C.c_uint32(v or 0); ck(u.uc_reg_read(self.h,r,C.byref(x)) if v is None else u.uc_reg_write(self.h,r,C.byref(x))); return x.value
    def run(self,entry,src,height,custom=None,cpu=2,custom5=1):
        size=len(src); self.write(SRC,src+b'\x5a'*64)
        self.write(DST-64,b'\xa5'*(size+128)); self.write(STACK,struct.pack('>I',STOP))
        for r in range(1,17): self.reg(r,0x12340000+r)
        self.reg(1,SRC); self.reg(2,DST); self.reg(8,STACK)
        self.reg(9,320); self.reg(12,height)
        self.reg(5,0x30000)
        self.write(0x30000-778,struct.pack('>I',0x3000))
        self.write(0x3000-402,bytes.fromhex('4e75')) # WaitBOVP: semantics tested live
        if custom is not None:
            self.write(BASE+0x1de4,struct.pack('>I',custom))
            if self.selected is not None: self.write(BASE+self.selected,struct.pack('>H',self.forced or (30 if cpu<4 else 0)))
            self.write(BASE+0x1e04,struct.pack('>I',custom5)) # limiter bypass by default in CPU-only tests
            self.write(4,struct.pack('>I',0x2000))
            self.write(0x2000+296,struct.pack('>H',0x80 if cpu==5 else 8 if cpu==4 else 2))
        before=[self.reg(r) for r in range(1,17)]
        self.writes=[]
        e=u.uc_emu_start(self.h,BASE+entry,STOP,10000000,3000000)
        if e: raise RuntimeError(f"{u.uc_strerror(e)} entry={entry:x} pc={self.reg(18):x} height={height} custom={custom} model={cpu}")
        assert self.reg(18)==STOP, 'instruction/timeout budget exceeded'
        assert self.read(SRC,size)==src, 'source modified'
        assert self.read(DST-64,64)==b'\xa5'*64 and self.read(DST+size,64)==b'\xa5'*64, 'guard modified'
        coverage=np.zeros(size,dtype=np.uint16)
        for address,n in self.writes:
            if STACK-512<=address<STACK: continue
            if any(lo<=address and address+n<=hi for lo,hi in getattr(self,"allowed_stores",())):continue
            assert DST<=address and address+n<=DST+size, ('unexpected store',hex(address),n)
            coverage[address-DST:address-DST+n]+=1
        assert np.all(coverage==1), 'output not written exactly once'
        if custom is not None:
            after=[self.reg(r) for r in range(1,17)]
            assert before[:7]+before[8:]==after[:7]+after[8:], 'wrapper register corruption'
            assert after[7]==STACK+4
        return self.read(DST,size),len(self.writes)
    def close(self): ck(u.uc_close(self.h))

def reference(src):
    pixels=np.frombuffer(src,dtype=np.uint8).reshape(-1,8)
    return b''.join(np.packbits((pixels>>bit)&1,axis=1).tobytes() for bit in range(8))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('build');p.add_argument('--output',required=True)
    p.add_argument('--capture',help='retained matrix directory with raw sources')
    a=p.parse_args(); build=Path(a.build); blob=(build/'payload.bin').read_bytes()
    family=json.loads((build/'build.json').read_text()).get('render_family','auto')
    forced=0 if family=='auto' else int(family)
    syms={m[1]:int(m[0],16) for m in re.findall(r'^([0-9A-F]{8}) (\S+)$',(build/'slave.lst').read_text(),re.M)}
    rng=random.Random(0xCD32); count=stores=0
    captured={128:[],166:[],200:[]}
    if a.capture:
        capture=Path(a.capture); seen=set()
        with (capture/'chunky-sources.bin').open('rb') as stream:
            for line in (capture/'matrix-events.txt').read_text().splitlines():
                fields=line.split()
                if not fields or fields[0]!='C': continue
                size=int(fields[4]); src=stream.read(size)
                assert len(src)==size
                scene=int(fields[1])
                if scene not in seen:
                    seen.add(scene); captured[size//320].append(src)
            assert not stream.read(1), 'extra raw source bytes'

    for model in (2,3,4,5):
        c=CPU(blob,min(model,4)) # Unicorn 060 lacks MOVEM; test 060 dispatch on 040 ISA.
        c.selected=syms.get('render_selected'); c.forced=forced
        for height,original in ((128,0x17f6),(166,0x195e),(200,0x1ac6)):
            size=320*height
            fixtures=[bytes(size),b'\xff'*size,bytes(range(256))*(size//256),bytes(rng.randrange(256) for _ in range(size))]
            for src in fixtures+captured[height]:
                # 166 rows is not a multiple of 256.
                if len(src)!=size: src=(bytes(range(256))*((size+255)//256))[:size]
                want=reference(src)
                for entry,custom in ((original,None),(syms[f'kalms_{"030" if model<4 else "040"}_{height}'],None),(0x178a,0),(0x178a,2)):
                    got,n=c.run(entry,src,height,custom,model)
                    assert got==want, (model,height,hex(entry),custom,next(i for i,(x,y) in enumerate(zip(got,want)) if x!=y))
                    count+=1; stores+=n
        c.close()
    cache_cases=0
    for flags,setup in ((2,0),(2,256),(8,256),(128,256)):
        for custom in (0,1,2):
            for custom5 in (0,1,2,3,4):
                c=CPU(blob,2)
                c.write(BASE+0x1de4,struct.pack('>I',custom))
                c.write(BASE+0x1e04,struct.pack('>I',custom5))
                c.write(BASE+0x121e,struct.pack('>I',0x80000))
                c.write(0x80000+96,bytes.fromhex('203c')+struct.pack('>I',setup)+bytes.fromhex('4e75'))
                c.write(4,struct.pack('>I',0x2000)); c.write(0x2000+296,struct.pack('>H',flags))
                c.write(0x80000+4,bytes.fromhex('4ef900001000')) # Abort stops
                c.write(STACK,struct.pack('>I',STOP)); c.reg(8,STACK)
                c.reg(3,0x80000); c.reg(9,0x123); c.reg(11,0x7654)
                ck(u.uc_emu_start(c.h,BASE+syms['render_setcpu'],STOP,1000000,1000))
                assert c.reg(18)==STOP and c.reg(11)==0x7654
                if custom==2 and custom5==4:
                    assert c.read(c.reg(8),4)==struct.pack('>I',9), 'unsupported blitter option accepted'
                else:
                    assert c.reg(9)==(setup if custom in (0,1) else 0x123), 'cache-policy gate failed'
                    assert c.reg(8)==STACK+4
                if custom==2 and 'render_selected' in syms:
                    assert int.from_bytes(c.read(BASE+syms['render_selected'],2),'big')==(forced or (30 if setup&256 and not flags&0x88 else 0))
                cache_cases+=1; c.close()
    rejected=[]
    # Deliberately damaged local code proves coverage and pixel checks can fail.
    for name in ('missing-converter','wrong-mask','wrong-geometry'):
        changed=bytearray(blob); entry=syms['kalms_030_128']
        if name=='missing-converter': changed[entry:entry+2]=bytes.fromhex('4e75')
        elif name=='wrong-mask':
            at=changed.index(bytes.fromhex('33333333'),entry)
            changed[at+3]^=1
        else: entry=syms['kalms_030_166']
        c=CPU(bytes(changed),2); src=bytes(range(256))*160
        try:
            got,n=c.run(entry,src,128)
            assert got==reference(src), 'incorrect pixels'
        except AssertionError: rejected.append(name)
        finally: c.close()
    assert len(rejected)==3, 'negative oracle fixture unexpectedly accepted'
    out=Path(a.output)
    assert Path('tmp').resolve() in out.resolve().parents and not out.exists()
    out.write_text(json.dumps(dict(passed=True,cases=count,hooked_stores=stores,cache_gate_cases=cache_cases,negative_fixtures_rejected=rejected,captured_frames=sum(map(len,captured.values())),cpu_models=[68020,68030,68040],note='060 dispatch executed on 040 ISA because Unicorn 060 rejects MOVEM',build_sha256=hashlib.sha256(blob).hexdigest()),indent=2)+'\n')
    print(out.read_text())
if __name__=='__main__': main()
