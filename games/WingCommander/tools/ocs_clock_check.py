#!/usr/bin/env python3
"""D2 scheduler/owner contracts on native M68000 and M68020; no cost claims."""
from runtime_buffers import load as load_slave
import argparse, json, struct
from pathlib import Path
from ocs_display_check import Native, CODE, DATA, word, long
from ocs_reconstruct import ROOT, new_output, require
from ocs_c2p import assemble

SLAVE=0x500000

def machine(build, model):
    b=json.loads((build/'build.json').read_text());sy=b['symbols']
    c=Native(ROOT/'tmp/game/WingCommander/data/Wing.english',model=model)
    c.write(SLAVE,load_slave((build/'WingCommander.Slave').read_bytes()))
    for pos in b['fixups']:c.write(SLAVE+pos,long(CODE+(c.get(SLAVE+pos,4)&0xfffffff)))
    for off,label,op in b['hooks']:c.write(CODE+off,word(op)+long(SLAVE+sy[label]))
    for off in (0x440,0x6370,0x4896):c.write(CODE+off,word(0x4e71))
    return c,sy


def check(build,out,model):
    # Execute real native lifecycle, RNG and integration instructions in a
    # bounded world fixture. Display/assets/device calls are explicit stubs;
    # full-game equality is a separate live gate, not inferred from this fixture.
    body=''' section code,code
 move.w #0,-(sp)
 jsr $10741e
 addq.l #2,sp
 jsr $12bbcc
 moveq #0,d2
'''
    game=(ROOT/'tmp/game/WingCommander/data/Wing.english').read_bytes()
    body+=' dc.b '+','.join(f'${x:02x}' for x in game[44+0x7e2c:44+0x7e56])+'\n jsr $12a816\n lea 12(sp),sp\n rts\n'
    fixture,_=assemble(out,f'world-{model}',body)
    results=[]
    for hz in (50,60):
      for schedule in ((1,), (2,3,1), (5,), (12,1,19,2), (150,)):
        c,sy=machine(build,model)
        try:
          def call(name):c.run(SLAVE-CODE+sy[name])
          def value(name):return c.get(SLAVE+sy[name],4)
          # World is original arithmetic, not a host transliteration.
          c.write(0x180000,fixture)
          c.write(CODE+0x2be,word(0x4ef9)+long(0x180000))
          for off in (0x18d14,0x290fa,0x27cfa,0x281c0,0x2837a,0x9618,0x2018,0x3908,0xacfa):
            c.intercept(CODE+off,lambda:c.return_call(0))
          c.write(DATA+0xaf4,word(1));c.write(DATA+0x8906,word(1000));c.write(DATA+0x890c,long(0))
          c.write(DATA+0x8c54,word(1000));c.write(DATA+0x94fa,struct.pack('>iii',5120,-1,1))
          c.write(DATA+0x8928,bytes(12));c.write(DATA+0x6f9a,long(0x12345678))
          c.write(SLAVE+sy['ocs_clock_hz'],long(hz))
          start=0xfffffff0;c.write(DATA+0x77fe,long(start));call('ocs_clock_rebase')
          elapsed=0;j=0
          while elapsed<hz*3:
            elapsed=min(hz*3,elapsed+schedule[j%len(schedule)]);j+=1
            c.write(DATA+0x77fe,long(start+elapsed))
            while True:
              before=value('ocs_clock_completed');call('ocs_clock_batch')
              require(value('ocs_clock_completed')-before<=4,'unbounded catch-up')
              if c.get(SLAVE+sy['ocs_clock_state'],4)==((start+elapsed)&0xffffffff):break
          got=dict(ticks=value('ocs_clock_completed'),life=c.get(DATA+0x8c54),
                   position=list(struct.unpack('>iii',c.read(DATA+0x8928,12))),seed=c.get(DATA+0x6f9a,4),score=c.get(DATA+0x890c,4),time=c.get(DATA+0x8906))
          require(got['score']==30 and got['time']==970,'simulator event cadence')
          require(got['ticks']==30 and got['life']==970 and got['position']==[153600,-30,30],str(got))
          require(c.get(SLAVE+sy['ocs_clock_state']+16,4)==0,'discarded active time')
          # Modal return rebases a large gap, preserving completed time and pose.
          c.write(DATA+0x77fe,long(start+elapsed+100000));call('ocs_clock_rebase');call('ocs_clock_batch')
          require(value('ocs_clock_completed')==30,'modal catch-up')
          results.append(dict(hz=hz,schedule=schedule,result=got,max_backlog=value('ocs_clock_backlog_max')))
        finally:c.close()
    require(all(r['result']==results[0]['result'] for r in results),'equal-time disagreement')
    return results


def owners(build,model,corrupt=False):
    c,sy=machine(build,model)
    try:
        if corrupt:
            at=SLAVE+sy['ocs_clock_emission'];raw=c.read(at,80);pos=raw.index(bytes.fromhex('302c08dc'))
            c.write(at+pos+2,word(0x08e0))
        def call(name):c.run(SLAVE-CODE+sy[name])
        def field(off,value,size=2):c.write(DATA+off,word(value) if size==2 else long(value))
        c.write(SLAVE+sy['ocs_clock_active'],word(1))
        field(0xaf4,1);field(0xac,2);field(0x8908,123,4);field(0x890c,0,4);field(0x386a,-1)
        call('ocs_clock_sim_draw');require(c.get(DATA+0xac)==2,'draw consumed simulator tail')
        call('ocs_clock_sim_native');require(c.get(DATA+0xac)==1,'tick did not consume simulator tail')
        call('ocs_clock_sim_native');require(c.get(DATA+0x890c,4)==123 and c.get(DATA+0xaa)==1,'bonus/exit event')
        call('ocs_clock_sim_native');require(c.get(DATA+0x890c,4)==123,'duplicate bonus')
        field(0x8906,100);field(0x890c,0,4)
        call('ocs_clock_score_draw');require(c.get(DATA+0x8906)==100 and c.get(DATA+0x890c,4)==0,'draw consumed score')
        call('ocs_clock_score');require(c.get(DATA+0x8906)==99 and c.get(DATA+0x890c,4)==1,'missing score tick')
        field(0x88da,8);field(0x88de,3);call('ocs_clock_emission');require(c.reg(9)==0,'emission uses draws')
        # Native pause consumes one queued key then drains to -1. Its full
        # LINK/JSR prologue and modal return run, including the relocated call.
        queue=[65,0xffffffff]
        c.intercept(CODE+0x33f02,lambda:c.return_call())
        def key():
            field(0x77fe,100000,4);c.return_call(queue.pop(0))
        c.intercept(CODE+0x345a8,key)
        call('ocs_clock_modal_pause')
        require(not queue and c.get(SLAVE+sy['ocs_clock_active'])==1,'pause did not restore ownership')
        require(c.get(SLAVE+sy['ocs_clock_state'],4)==100000 and c.get(SLAVE+sy['ocs_clock_state']+4,4)==0,'pause retained modal debt')
        require(c.get(SLAVE+sy['ocs_clock_cancel'])==1,'pause failed to cancel pending tick')
        return dict(simulator_bonus_once=True,score_world_only=True,emission_world_counter=True,native_pause_rebased=True)
    finally:c.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);p.add_argument('--output',required=True)
    a=p.parse_args()
    require(not json.loads((a.build/'build.json').read_text()).get('prediction'),
            'D2-only world fixture; use ocs_prediction_check.py for input-aware D3/E1 builds')
    out=new_output(a.output);out.mkdir(parents=True)
    results={str(m):check(a.build,out,m) for m in (1,2)}
    owner_checks={str(m):owners(a.build,m) for m in (1,2)}
    require(results['1']==results['2'],'CPU disagreement')
    try:owners(a.build,1,corrupt=True)
    except ValueError as error:
        require(str(error)=='emission uses draws','unexpected rejecting control')
    else:raise ValueError('draw-driven emission corruption survived')
    (out/'report.json').write_text(json.dumps(dict(passed=True,models=results,owners=owner_checks,rejected=['draw-driven emission']),indent=2)+'\n')
    print('PAL/NTSC varied schedules, wrap, retained debt and modal rebases pass on both CPUs')
if __name__=='__main__':main()
