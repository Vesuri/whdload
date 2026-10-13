#!/usr/bin/env python3
"""Native modal wrapper contracts with controlled elapsed modal time."""
import argparse,json,re,struct
from pathlib import Path
from timing_audit_check import CPU
from cd32_runtime import ROOT,locate
S=0x180000

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    out=a.output.resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('new tmp output required')
    memory=(ROOT/'tmp/phase7-combat-controls/start-fast.bin').read_bytes();layout=locate(memory)
    blob=(a.build/'payload.bin').read_bytes();sym={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)}
    cases=[]
    for model in (2,4):
        for name in ('pause','autopilot'):
            for active in (0,1):
                c=CPU(memory,layout,model);c.write(S,blob)
                def put(n,f,v):c.write(S+sym[n],struct.pack('>'+f,v))
                def get(n,f):return struct.unpack('>'+f,c.read(S+sym[n],struct.calcsize('>'+f)))[0]
                put('timing_hz','I',50);put('timing_active','H',active);put('timing_replay','H',active)
                c.write(S+sym['timing_clock'],struct.pack('>6IHH',100,20,0,0,0,0,1,0))
                c.data_value(0x7f02,'I',110);put('timing_input_head','H',8)
                c.write(S+sym['timing_angle_remainder'],struct.pack('>3i',1,-2,3))
                # Replace only the modal body in this CPU-only fixture. It
                # observes producer ownership, advances emulated field state,
                # and returns a distinct D0/CCR for the wrapper to preserve.
                stub=bytes.fromhex('33f9')+struct.pack('>II',S+sym['timing_active'],0x1e9000)
                stub+=bytes.fromhex('297c000001f4ff04') # clock=500
                stub+=bytes.fromhex('701544fc00154e75') # D0=21, CCR=$15
                c.write(S+sym['timing_'+name+'_original'],stub)
                c.run(S+sym['timing_'+name]-c.code)
                assert c.read(0x1e9000,2)==bytes(2)
                assert get('timing_active','H')==active and get('timing_replay','H')==0
                assert get('timing_clock','I')==500
                assert c.read(S+sym['timing_clock']+4,4)==bytes(4)
                assert get('timing_input_tail','H')==8 and get('timing_abort','H')==1
                assert get('timing_input_dropped_fields','I')==10*active
                assert c.read(S+sym['timing_angle_remainder'],12)==bytes(12)
                assert c.reg(9)==21 and c.reg(17)&31==21 and c.reg(8)==0x1f0004
                # First resumed field contributes only one field, not modal time.
                c.run(S+sym['timing_advance']-c.code,registers={1:S+sym['timing_clock'],9:501,10:50,11:1})
                assert c.reg(9)==0 and c.read(S+sym['timing_clock']+4,4)==struct.pack('>I',10)
                cases.append(dict(model=model,modal=name,active=active));c.close()
    out.mkdir(parents=True);(out/'report.json').write_text(json.dumps(dict(cases=cases,paused_time_excluded=True,return_contract=True),indent=2)+'\n')
    print('PASS: eight native pause/autopilot ownership, rebase and return-contract cases')
if __name__=='__main__':main()
