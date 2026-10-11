#!/usr/bin/env python3
"""Check observed vertex-coordinate reads follow writes in the same cache epoch.

Covers the named native coordinate read/write sites after an observed validity
reset. Covers transformed and projected coordinates at the listed sites, not all
consumers or unseen paths. Reads before the first reset are reported as incomplete coverage.
"""
import argparse
import json
import re
import struct
from pathlib import Path
import barto

READS = {0x17b5e:0, 0x17b6e:1, 0x17b7e:2,
         0x17c22:0, 0x17c32:1, 0x17c42:2,
         0x17cfe:1, 0x17d08:0, 0x17d28:2}
WRITES = {0x17bd4:0, 0x17be6:1, 0x17bf8:2,
          0x17ca4:0, 0x17cc2:1, 0x17ce0:2}
ARRAYS = (0x484c, 0x4c48, 0x5044, 0x5440, 0x583c)
# Axis, address register, optional index register/width, guarded opcode.
PROJECTED_READS = {
    0x14666:(3,11,None,0,'2213'), 0x1466e:(3,11,None,0,'2413'),
    0x1468a:(4,9,6,32,'92b16800'),
    0x146f8:(3,10,None,0,'2212'), 0x14700:(3,10,None,0,'2412'),
    0x1471a:(4,9,6,32,'90b16800'),
    0x14736:(3,11,None,0,'2413'), 0x1473e:(3,11,None,0,'2613'),
    0x14764:(4,9,2,32,'24312800'),
    0x14782:(3,11,None,0,'2013'), 0x1478a:(3,11,None,0,'2613'),
    0x147a0:(4,8,2,32,'90b02800'),
    0x149e2:(3,14,4,32,'90b64800'), 0x149ea:(4,12,4,32,'90b44800'),
    0x14a02:(3,14,4,32,'d0b64800'), 0x14a0a:(4,12,4,32,'90b44800')}
PROJECTION_INPUT_READS = {
    0x14b80:(1,8,None,0,'2010'),
    0x17f18:(0,8,0,16,'22f00000'), 0x17f22:(1,8,0,16,'22f00000'),
    0x17f2c:(2,8,0,16,'22b00000'),
    0x17e1a:(1,8,None,0,'9a90'),
    0x17e28:(0,9,None,0,'2411'), 0x17e2a:(0,8,None,0,'9490'),
    0x17e38:(1,9,None,0,'2611'), 0x17e3a:(1,8,None,0,'9690'),
    0x17e48:(2,9,None,0,'2811'), 0x17e4a:(2,8,None,0,'9890'),
    0x17e62:(0,8,None,0,'d490'), 0x17e7c:(2,8,None,0,'d890'),
    0x17fe4:(1,8,4,16,'24304000'), 0x17fee:(2,8,4,16,'22304000'),
    0x17ff8:(0,8,4,16,'20304000'),
    0x180fa:(1,8,4,16,'96b04000'),
    0x18104:(0,8,5,16,'20305000'), 0x18108:(0,8,4,16,'90b04000'),
    0x18112:(1,8,5,16,'24305000'), 0x18116:(1,8,4,16,'94b04000'),
    0x18120:(2,8,5,16,'22305000'), 0x18124:(2,8,4,16,'92b04000'),
    0x1813a:(0,8,4,16,'d0b04000'), 0x1814e:(2,8,4,16,'d2b04000')}
TRANSFORMED_EXTRA_WRITES = {
    0x17f84:(0,8,2,16,'21992000'), 0x17f96:(1,8,2,16,'21992000'),
    0x17fa8:(2,8,2,16,'21912000')}
PROJECTED_WRITES = {
    0x17d1e:(3,8,None,0,'2080'), 0x17d3e:(4,8,None,0,'2080'),
    0x17e64:(3,9,None,0,'2282'), 0x17e7e:(4,9,None,0,'2284'),
    0x18008:(3,8,4,16,'21804000'), 0x18012:(4,8,4,16,'21814000'),
    0x1813e:(3,9,4,16,'23804000'), 0x18152:(4,9,4,16,'23814000')}



def inspect(folder, trace=None):
    folder = Path(folder)
    meta = {k:int(v,0) for k,v in re.findall(r'^(code|data|base)=(\S+)',
                                           (folder/'anchor.txt').read_text(),re.M)}
    memory = (folder/'code.bin').read_bytes()
    code = memory[meta['code']-meta['base']:]
    guards = {0x13b70:'3940df38', 0x13b84:'3f2cdf384267486cc74c4eba01f8504f',
              0x24078:'206f00042248322f000a302f0008600210c051c9fffc20094e75'}
    reads={pc:(axis,8,None,0,'2610' if pc==0x17cfe else '2010') for pc,axis in READS.items()}
    writes={pc:(axis,8,None,0,'2080') for pc,axis in WRITES.items()}
    reads.update(PROJECTED_READS);reads.update(PROJECTION_INPUT_READS)
    writes.update(PROJECTED_WRITES);writes.update(TRANSFORMED_EXTRA_WRITES)
    guards.update({pc:entry[4] for pc,entry in (reads|writes).items()})
    for pc,encoded in guards.items():
        expected=bytes.fromhex(encoded)
        assert code[pc:pc+len(expected)]==expected,hex(pc)
    assert code[0x13d88:0x13d8e]==bytes.fromhex('4ef9')+struct.pack('>I',meta['code']+0x24078)
    epochs=[];active=None;count=None;prefix=0
    trace=trace or barto.load(folder/'trace.bin')
    for field in trace.fields:
        for pc,cost,regs in trace.instructions(field):
            if pc is None:continue
            at=pc-meta['code']
            if at==0x13b70:count=regs[0]&0xffff
            elif at==0x13b92:
                assert count is not None and 0<=count<=255,count
                if active is not None:epochs.append(active)
                active=dict(vertices=count,initialized=[set() for _ in ARRAYS],reads=0,writes=0,read_axes=[0]*len(ARRAYS),write_axes=[0]*len(ARRAYS),sites=set(),field=field.index)
            elif at in reads or at in writes:
                if active is None:prefix+=1;continue
                axis,base_register,index_register,bits,opcode=(reads if at in reads else writes)[at]
                address=regs[base_register]
                if index_register is not None:
                    index_value=regs[index_register]&((1<<bits)-1)
                    if index_value&(1<<(bits-1)):index_value-=1<<bits
                    address=(address+index_value)&0xffffffff
                offset=address-meta['data']-ARRAYS[axis]
                active['sites'].add(at)
                assert offset>=0 and offset%4==0,(hex(at),offset)
                index=offset//4
                assert index<active['vertices'],(hex(at),index,active['vertices'])
                if at in reads:
                    assert index in active['initialized'][axis],f'vertex {index} axis {axis} read before write at {at:#x}'
                    active['reads']+=1;active['read_axes'][axis]+=1
                else:
                    active['initialized'][axis].add(index);active['writes']+=1;active['write_axes'][axis]+=1
    if active is not None:epochs.append(active)
    assert epochs and sum(e['reads'] for e in epochs)>0,'no covered vertex reads'
    for epoch in epochs:
        epoch['initialized']=[sorted(s) for s in epoch['initialized']]
        epoch['sites']=[hex(pc) for pc in sorted(epoch['sites'])]
    return dict(epochs=epochs,covered_reads=sum(e['reads'] for e in epochs),
                covered_writes=sum(e['writes'] for e in epochs),prefix_accesses=prefix,
                scope=__doc__)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path)
    print(json.dumps(inspect(p.parse_args().capture),indent=2))
