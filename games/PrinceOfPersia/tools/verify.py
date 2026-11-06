#!/usr/bin/env python3
"""The VERIFY slave's block (PrinceOfPersiaVerify.s): find it in a session and read its fields.

    v=Verify(session); v.long('verify_steps'); v.until_step(100)
"""
import struct
from pop import symbols,SLAVE
MARKER=b'POPVERIFY\0'

class Verify:
    def __init__(self,s,slave=SLAVE):
        self.s=s;self.sym=symbols(slave);self.at=None
    def addr(self,name):
        if self.at is None:
            # PRELOAD keeps a copy of the slave file too; the live slave has _resload set.
            rel=self.sym['_resload']-self.sym['verify_block']
            self.at=self.s.find(MARKER,ok=lambda a:struct.unpack('>I',self.s.read(a+rel,4))[0]!=0)
            if self.at is None:raise RuntimeError('VERIFY block not found (normal slave?)')
        return self.at+self.sym[name]-self.sym['verify_block']
    def read(self,name,n):return self.s.read(self.addr(name),n)
    def long(self,name):return struct.unpack('>I',self.read(name,4))[0]
    def live(self,offset):
        """Runtime address of slave offset (a symbols() value) in the live slave."""
        self.addr('verify_block');return self.at+offset-self.sym['verify_block']
    def until_step(self,n,at='verify_stopped'):
        """Run until gameplay step n starts (its count taken, its input not yet read), or with
        at='verify_wait_stopped' until the frame-wait exit of step n (where A4 hashes).
        A breakpoint stops emulated time: use it outside traces only. Session.field is stale after."""
        if self.long('verify_steps')>=n:raise ValueError(f'step {n} already passed')
        self.s.cmd(f"set {{int}}{self.addr('verify_stop'):#x} = {n}")
        self.s.cmd(f"break *{self.live(self.sym[at]):#x}")
        self.s.cmd('continue',timeout=3600);self.s.cmd('delete')
        assert self.long('verify_steps')==n
    def dump(self):
        """The whole block, from verify_block to the end of the frame log."""
        end=self.sym['verify_log']+ENTRY*VERIFY_FRAMES
        return self.read('verify_block',end-self.sym['verify_block'])

VERIFY_FRAMES,ENTRY=2048,10
def fields(blob,sym):
    """Block dump -> dict of the long fields named in sym (offsets from verify_block)."""
    b=sym['verify_block'];out={}
    for n in ('verify_steps','verify_fields','verify_blits','verify_frames','verify_sabotaged','verify_vclock'):
        out[n]=struct.unpack_from('>I',blob,sym[n]-b)[0]
    return out
def frames(blob,sym):
    """Block dump -> frame log as dicts (step, period, work in lines; blits; target in fields)."""
    n=min(fields(blob,sym)['verify_frames'],VERIFY_FRAMES);o=sym['verify_log']-sym['verify_block']
    return [dict(zip(('step','period','work','blits','target'),struct.unpack_from('>HHHHH',blob,o+ENTRY*i))) for i in range(n)]
