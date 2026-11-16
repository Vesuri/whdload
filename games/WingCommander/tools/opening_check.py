#!/usr/bin/env python3
"""Native opening clock/zoom semantics and exact hunk-3 installation checks.

Synthetic field/input sources exercise PAL/NTSC, delayed fields, wrap and skip.
These are functional checks, not emulator or hardware performance measurements.
"""
from runtime_buffers import load as load_slave
import argparse
import json
import re
from pathlib import Path
from cd32_static import HunkReader
from ocs_display_check import Native, CODE, DATA, BSS, STARTUP, STOP, u, ck, long, word
from ocs_reconstruct import ROOT, new_output, require
from opening_source import specification, code_patches, renderer
from variants import get


def check(build, variant):
    v=get(variant)
    if variant=='ocs':
        sy=json.loads((build/'build.json').read_text())['symbols']
        payload=load_slave((build/'WingCommander.Slave').read_bytes())
    else:
        sy={name:int(off,16) for off,name in re.findall(r'^([0-9A-F]{8}) (\S+)$',(build/'slave.lst').read_text(),re.M)}
        payload=(build/'payload.bin').read_bytes()
    slave=0x500000
    c=Native(ROOT/'tmp/game/WingCommander/data/Wing.english',model=2)
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
        guards=[(STARTUP,off,width) for off,width,_,_ in patches]+[(STARTUP,off,width) for off,width in nops]
        guards+=[(CODE,off,width) for off,width,_,_ in code_patches(variant)]
        for base,off,width in guards:
            for at in range(off,off+width,2):
                was=c.read(base+at,2)
                c.write(base+at,word(int.from_bytes(was,'big')^1))
                previous=len(rejected)
                run('opening_guard',{1:CODE})
                require(len(rejected)==previous+1,'damaged opening instruction accepted')
                c.write(base+at,was)
        run('opening_install',{1:CODE})
        stages,patches,nops=specification(variant)
        want=bytearray(before)
        for off,width,label,op in patches:
            want[off:off+width]=word(op)+long(slave+sy[label])+bytes.fromhex('4e71')*((width-6)//2)
        for off,width in nops:want[off:off+width]=bytes.fromhex('4e71')*(width//2)
        require(c.read(STARTUP,len(before))==want,'unexpected hunk-3 changes')
        for off,width,label,op in code_patches(variant):
            require(c.read(CODE+off,width)==word(op)+long(slave+sy[label])+bytes.fromhex('4e71')*((width-6)//2),'renderer patch')
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
                # Orchestra: three PAL fields, four NTSC, retaining debt and skip.
                fields=3 if hz==50 else 4
                c.write(field,long(epoch));run('opening_rebase')
                for step in range(1,21):
                    run('opening_orchestra_input')
                    require(c.get(field,4)==(epoch+step*fields)&0xffffffff,'orchestra cadence')
                    require(c.get(count)==1,'orchestra countdown not armed')
                c.write(field,long(epoch+23*fields))
                for step in range(21,24):
                    run('opening_orchestra_input')
                    require(c.get(slave+sy['opening_cursor'],4)==(epoch+step*fields)&0xffffffff,'lost orchestra debt')
                skip[0]=True;polls[0]=0;run('opening_orchestra_input');skip[0]=False
                require(c.reg(9)==1 and polls[0]==1,'orchestra skip delayed')
                c.write(field,long(epoch));run('opening_rebase')
                for step in range(1,21):
                    run('opening_fireworks_input')
                    require(c.get(field,4)==(epoch+step*3)&0xffffffff,'fireworks cadence')
                    require(c.get(count)==1,'fireworks countdown')
                skip[0]=True;polls[0]=0;run('opening_fireworks_input');skip[0]=False
                require(c.reg(9)==1 and polls[0]==1,'fireworks skip delayed')
                c.write(field,long(epoch));run('opening_rebase')
                samples=[];fines=[]
                require(c.get(slave+sy['opening_sep_s'])==0,'separation s not reset to 0')
                for elapsed in range(1,hz*2+1):
                    c.write(field,long(epoch+elapsed));run('opening_separation_sample')
                    steps,frac=divmod(elapsed*10,hz);value=1
                    first=steps==0;steps=max(0,steps-1)  # one tick from s = 0 first
                    for _ in range(steps):
                        value+=value//4+1
                        if value>=120:break
                    if value<120 and not first:value+=(value//4+1)*frac//hz
                    require(c.reg(11)&65535==value,'separation trajectory')
                    samples.append(value)
                    # Fractional s (1/128) for the piece positions and scale.
                    steps,frac=divmod(elapsed*10,hz);whole=1
                    for _ in range(max(0,steps-1)):
                        if whole>=120:break
                        whole+=whole//4+1
                    if steps==0:fine=(frac<<7)//hz
                    else:fine=whole<<7 if whole>=120 else (whole<<7)+(((whole//4+1)<<7)*frac)//hz
                    require(c.get(slave+sy['opening_sep_s'])==fine,('fractional separation',elapsed,fine))
                    fines.append(fine)
                require(len(set(samples))>20,'zoom remains at 10 Hz')
                # From the very first field the pieces move: s rises every field.
                require(all(a<b for a,b in zip(fines,fines[1:40])),('separation start still steps',fines[:12]))
                # The hooked multiplies: exact native s*v on whole steps, fractional between.
                record=0x180000
                for vx,vy in ((7,-3),(-12,5),(0,1)):
                    c.write(record,word(0)+word(0)+word(vx&0xffff)+word(vy&0xffff))
                    for fine in (128,192,640,1000,15232):
                        c.write(slave+sy['opening_sep_s'],word(fine))
                        for name,vel,shift_ in (('opening_sep_x',vx,7),('opening_sep_y',vy,7),('opening_sep_scale',vy,5)):
                            run(name,{3:record})
                            want=(fine*vel)>>shift_
                            require(c.reg(9)&0xffff==want&0xffff,(name,fine,vel,c.reg(9)))
                            native=(fine>>7)*vel*(4 if shift_==5 else 1)
                            if fine%128==0:require(want==native,'whole step differs from native')
                # The draw wrapper hands the renderer 8.8 x/y from the fractional
                # s; other callers keep the native integer loads.
                entry,load,xarg=renderer(variant)
                after=load+16
                exit_=0x2f476 if variant=='ocs' else 0x2ed84
                image=0x188000
                if variant=='ocs':
                    c.write(image,long(0x544d3500)+bytes(4)+word(4)+bytes(110-10)+long(200)*4)
                    c.write(image+200,word(1))
                else:
                    c.write(image,long(0x544d3600)+bytes(2)+word(4)+bytes(8)+long(200)*4)
                seen=[]
                def at_load():
                    seen.append((c.reg(11),c.reg(12)));c.reg(18,CODE+exit_)
                c.intercept(CODE+after,at_load)
                def args(x,y):return long(0x18c000)+word(x&0xffff)+word(y&0xffff)+long(image)+word(1)+word(300)
                c.write(record,word(58)+word(94)+word(0xffff)+word(1))  # piece 0: x 58, y 94, v (-1, 1)
                for fine in (0,25,64,128,1000):
                    c.write(slave+sy['opening_sep_s'],word(fine))
                    seen.clear();c.run(slave-CODE+sy['opening_sep_draw'],args(1,2),{3:record})
                    fx,fy=(58<<8)-2*fine,(94<<8)+2*fine
                    require(set(seen)=={(fx&0xffffffff,fy)},('subpixel draw',fine,seen))
                    require(c.reg(3)==record and c.get(slave+sy['opening_sep_on'])==0,'draw wrapper state')
                    if fine%128==0:require((fx,fy)==((58-fine//128)<<8,(94+fine//128)<<8),'whole step differs from native')
                seen.clear();c.run(entry,args(-7,40))
                require(set(seen)=={((-7<<8)&0xffffffff,40<<8)},('native renderer loads',seen))
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
