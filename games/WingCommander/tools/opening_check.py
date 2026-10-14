#!/usr/bin/env python3
"""Native opening clock/zoom semantics and exact hunk-3 installation checks.

Synthetic field/input sources exercise PAL/NTSC, delayed fields, wrap and skip.
These are functional checks, not emulator or hardware performance measurements.
"""
import argparse
import json
import re
from pathlib import Path
from cd32_static import HunkReader
from ocs_display_check import Native, CODE, DATA, BSS, STARTUP, STOP, u, ck, long, word
from ocs_reconstruct import ROOT, new_output, require
from opening_source import specification
from variants import get


def check(build, variant):
    v=get(variant)
    if variant=='ocs':
        sy=json.loads((build/'build.json').read_text())['symbols']
        payload=(build/'WingCommander.Slave').read_bytes()[32:-4]
    else:
        sy={name:int(off,16) for off,name in re.findall(r'^([0-9A-F]{8}) (\S+)$',(build/'slave.lst').read_text(),re.M)}
        payload=(build/'payload.bin').read_bytes()
    slave=0x500000
    c=Native(ROOT/'tmp/originals/ocs/WingCommander/data/Wing.english',model=2)
    try:
        # Load and relocate each variant independently, including its segment chain.
        reader=HunkReader();require(reader.read_file(str(ROOT/v.GAME))==0,reader.error_string)
        bases=(CODE,DATA,BSS,STARTUP);index=-1
        for record in reader.hunks:
            if record['type_name'] in ('HUNK_CODE','HUNK_DATA','HUNK_BSS'):
                index+=1
                if 'data' in record:c.write(bases[index],record['data'])
            for target,offsets in record.get('reloc',{}).items():
                for off in offsets:c.write(bases[index]+off,long(c.get(bases[index]+off,4)+bases[target]))
        c.write(slave,payload)
        run=lambda name,registers=None:c.run(slave-CODE+sy[name],registers=registers)
        before=c.read(STARTUP,v.HUNKS[3][1])
        run('opening_guard',{1:CODE})
        require(c.read(STARTUP,len(before))==before,'guard wrote hunk')
        stages,patches,nops=specification(variant)
        rejected=[]
        def reject():
            rejected.append(True);c.reg(18,STOP);ck(u.uc_emu_stop(c.h))
        c.intercept(slave+sy['opening_bad'],reject)
        guards=[(off,width) for off,width,_,_ in patches]+nops
        for off,width in guards:
            for at in range(off,off+width,2):
                c.write(STARTUP+at,word(int.from_bytes(before[at:at+2],'big')^1))
                previous=len(rejected)
                run('opening_guard',{1:CODE})
                require(len(rejected)==previous+1,'damaged opening instruction accepted')
                c.write(STARTUP+at,before[at:at+2])
        run('opening_install',{1:CODE})
        stages,patches,nops=specification(variant)
        want=bytearray(before)
        for off,width,label,op in patches:
            want[off:off+width]=word(op)+long(slave+sy[label])+bytes.fromhex('4e71')*((width-6)//2)
        for off,width in nops:want[off:off+width]=bytes.fromhex('4e71')*(width//2)
        require(c.read(STARTUP,len(before))==want,'unexpected hunk-3 changes')
        for off,width,name in stages:
            resume=slave+sy['opening_resume_'+name]
            require(c.read(resume-width,width)==before[off:off+width],'displaced instructions changed')
            require(c.get(resume+2,4)==STARTUP+off+width,'incorrect entry resume')
        field=DATA+0x7ffe+v.A4['field_clock']
        count=DATA+0x7ffe+(-32592 if variant=='ocs' else -32624)
        c.write(slave+sy['timing_rate'],bytes.fromhex('70324e75'))
        polls=[0];skip=[False]
        def input_poll():
            polls[0]+=1
            c.write(field,long(c.get(field,4)+1))
            c.return_call(1 if skip[0] else 0)
        c.intercept(slave+sy['opening_input_native'],input_poll)
        cases=[]
        for hz in (50,60):
            c.write(slave+sy['timing_rate'],word(0x7000+hz)+bytes.fromhex('4e75'))
            for epoch in (0,0xfffffff0):
                c.write(field,long(epoch));run('opening_begin')
                require(c.get(slave+sy['opening_active'])==1,'opening inactive')
                for step in range(1,21):
                    run('opening_tick_input')
                    require(c.get(field,4)==(epoch+step*(hz//10))&0xffffffff,'animation cadence')
                    require(c.get(count)==1,'animation countdown not armed')
                # A skipped display interval retains all pending native steps.
                c.write(field,long(epoch+23*(hz//10)))
                for step in range(21,24):
                    run('opening_tick_input')
                    require(c.get(slave+sy['opening_cursor'],4)==(epoch+step*(hz//10))&0xffffffff,'lost animation debt')
                skip[0]=True;polls[0]=0;run('opening_tick_input');skip[0]=False
                require(c.reg(9)==1 and polls[0]==1,'skip delayed')
                c.write(field,long(epoch));run('opening_rebase')
                samples=[]
                for elapsed in range(1,hz*2+1):
                    c.write(field,long(epoch+elapsed));run('opening_separation_sample')
                    steps,frac=divmod(elapsed*10,hz);value=1
                    for _ in range(steps):
                        value+=value//4+1
                        if value>=120:break
                    if value<120:value+=(value//4+1)*frac//hz
                    require(c.reg(11)&65535==value,'separation trajectory')
                    samples.append(value)
                require(len(set(samples))>20,'zoom remains at 10 Hz')
                c.write(field,long(epoch));run('opening_rebase')
                for elapsed in range(1,hz*4+2):
                    c.write(field,long(epoch+elapsed));run('opening_flight_sample')
                    delta=min(4001,elapsed*1000//hz)
                    y=57-delta//50 if delta<=1900 else 19+(delta-1900)//50
                    require(c.reg(12)&65535==5000-delta,'flight depth')
                    require(c.reg(11)&65535==y,'flight vertical trajectory')
                run('opening_end');require(c.get(slave+sy['opening_active'])==0,'opening remains active')
                cases.append(dict(hz=hz,wrap=bool(epoch),separation_positions=len(set(samples))))
        return dict(passed=True,variant=variant,cases=cases,exact_hunk3=True,guard_rejections=len(rejected))
    finally:c.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path);p.add_argument('--output',required=True)
    a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
    result=check(a.build,a.variant)
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
