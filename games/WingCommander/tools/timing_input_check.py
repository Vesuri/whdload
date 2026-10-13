#!/usr/bin/env python3
"""Native input-history FIFO order, latch ownership, register and overflow checks."""
import argparse
import json
import re
import struct
from pathlib import Path
from timing_audit_check import CPU
from cd32_runtime import ROOT, locate

S=0x180000


def check(memory,layout,blob,sym):
    count=0
    for model in (2,4):
        c=CPU(memory,layout,model);c.write(S,blob)
        c.write(S+sym['timing_data'],struct.pack('>I',c.data))
        def value(label,fmt='H',v=None):
            at=S+sym[label]
            if v is not None:c.write(at,struct.pack('>'+fmt,v))
            return struct.unpack('>'+fmt,c.read(at,struct.calcsize('>'+fmt)))[0]
        def record():
            regs={r:0x12340000+r for r in range(1,17) if r!=8}
            regs[17]=0x271f
            c.run(S+sym['timing_record_input']-c.code,registers=regs)
            for r,want in regs.items():
                assert c.reg(r)==(0xdff000 if r==1 else want),(r,c.reg(r),want)
            assert c.reg(8)==0x1f0004
        before=c.read(c.data,0xfda0);record()
        assert c.read(c.data,0xfda0)==before and value('timing_input_head')==0
        value('timing_active',v=1)
        for field in range(63):
            pad=bytes((field+i)&255 for i in range(15))
            keys=bytes((field*3+i)&255 for i in range(128))
            c.data_value(0x7f02,'I',field)
            c.write(c.data+0x7e06,pad);c.write(c.data+0x7f58,keys)
            c.data_value(0x805e,'H',field&63)
            record()
            want=struct.pack('>I',field)+pad+b'\0'+keys+struct.pack('>HH',field&63,0)
            assert c.read(S+sym['timing_input_ring']+152*field,152)==want
            assert c.read(c.data+0x7e0c,2)==bytes(2)
            assert value('timing_input_head')==field+1
            count+=1
        ring=c.read(S+sym['timing_input_ring'],152*64)
        record()
        assert value('timing_input_head')==63 and value('timing_input_lost')==1
        assert value('timing_input_overflows','I')==1
        assert c.read(S+sym['timing_input_ring'],152*64)==ring
        value('timing_input_tail',v=1)
        record()
        assert value('timing_input_head')==0
        # Drain the oldest records, including the wrapped published slot.
        for field in range(1,64):
            c.run(S+sym['timing_take_sample']-c.code)
            assert c.reg(9)==1
            assert c.read(S+sym['timing_sample_clock'],152)==c.read(S+sym['timing_input_ring']+field*152,152)
        c.run(S+sym['timing_take_sample']-c.code);assert c.reg(9)==0
        value('timing_replay',v=1)
        c.write(S+sym['timing_game'],struct.pack('>I',c.code))
        c.write(S+sym['timing_sample_pad'],bytes(range(16)))
        c.write(S+sym['timing_sample_keys'],bytes(range(128)))
        dest=0x1e8000;c.write(dest,bytes([255])*132)
        c.run(S+sym['timing_pad_read']-c.code,struct.pack('>HI',1,dest))
        assert c.read(dest,16)==bytes(range(15))+bytes([255])
        c.run(S+sym['timing_keys_read']-c.code,struct.pack('>I',dest))
        assert c.read(dest,132)==bytes(range(128))+bytes([255])*4
        # The native FIFO has newer commands than this captured field. Neither
        # repeated calls nor cursor wrap may drain them early or duplicate one.
        c.data_value(0x8058,'I',0);c.data_value(0x805c,'H',62);c.data_value(0x805e,'H',2)
        for i,b in [(62,11),(63,12),(0,13),(1,14)]:c.data_value(0x7fd8+i,'B',b)
        value('timing_sample_producer',v=0)
        got=[]
        for _ in range(4):
            c.run(S+sym['timing_key_command']-c.code);got.append(c.reg(9)&65535)
        assert got==[11,12,65535,65535]
        value('timing_sample_producer',v=2)
        got=[]
        for _ in range(3):
            c.run(S+sym['timing_key_command']-c.code);got.append(c.reg(9)&65535)
        assert got==[13,14,65535]
        # Exercise original edge dispatch and its latch advance. Only the final
        # command side effect is a counting sink; native edge predicates remain.
        sink=0x1e9000;c.write(sink,bytes(4))
        c.write(c.code+0x19500,bytes.fromhex('52b9')+struct.pack('>I',sink)+bytes.fromhex('70004e75'))
        c.write(c.data+0xc6c8,bytes(32));value('timing_abort',v=0);value('timing_pad_count',v=0)
        for pressed in (0,1,1,0,1,0):
            c.write(S+sym['timing_sample_pad'],bytes([pressed])+bytes(15))
            c.run(S+sym['timing_queue_pad']-c.code)
        c.run(S+sym['timing_pad_edges']-c.code)
        assert c.read(sink,4)==struct.pack('>I',2)
        c.run(S+sym['timing_pad_edges']-c.code)
        assert c.read(sink,4)==struct.pack('>I',2)
        assert value('timing_pad_count')==0
        c.close()
    return count


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('build',type=Path)
    p.add_argument('--memory',type=Path,default=Path('tmp/phase7-combat-controls/start-fast.bin'))
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();out=a.output.resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('new tmp output required')
    memory=a.memory.read_bytes();layout=locate(memory);blob=(a.build/'payload.bin').read_bytes()
    sym={name:int(off,16) for off,name in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)}
    count=check(memory,layout,blob,sym)
    start=sym['timing_record_input'];end=sym['timing_pad_read']
    part=blob[start:end];assert part.count(bytes.fromhex('740e'))==1
    broken=blob[:start]+part.replace(bytes.fromhex('740e'),bytes.fromhex('740d'))+blob[end:]
    try:check(memory,layout,broken,sym)
    except AssertionError:pass
    else:raise AssertionError('truncated pad-copy sabotage passed')
    out.mkdir(parents=True)
    (out/'report.json').write_text(json.dumps(dict(records=count,inactive=True,wrap=True,full_preserves_unread=True,latches_transferred=True,short_copy_rejected=True,consumer_order=True,command_cursor_wrap=True,native_edges_exactly_once=True,scope='native producer/consumer and command boundaries; live cadence checked separately'),indent=2)+'\n')
    print(f'PASS: {count} ordered records; native input copy, command cursor, edge delivery, overflow and negative control')


if __name__=='__main__':main()
