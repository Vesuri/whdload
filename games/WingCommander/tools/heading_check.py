#!/usr/bin/env python3
"""C3 native forecast/isolation and retained full-tick trajectory regression.

The original motion routine is an independent arithmetic oracle; recorded next
states measure unpredictable controller changes too. Neither is an FPS tool.
Player slot 0 is C2-owned and is reported separately from world ships.
"""
import argparse, hashlib, json, math, re, statistics, struct
from pathlib import Path
from timing_audit_check import CPU
from timing_scene_check import S, trunc
from timing_scene_report import unpack, percentile
from cd32_runtime import ROOT


def stats(values):
    assert values, 'empty forecast comparison'
    return dict(count=len(values), median=statistics.median(values),
                p95=percentile(values,.95), maximum=max(values))


def check(build, run, model, sabotage=False):
    meta=json.loads((run/'result.json').read_text()); oldsy=meta['symbols']
    blob=(build/'payload.bin').read_bytes()
    sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(build/'slave.lst').read_text(),re.M)}
    memory=(run/'start-fast.bin').read_bytes()
    c=CPU(memory,meta,model); ref=CPU(memory,meta,model)
    c.write(S,blob);c.write(S+sy['timing_game'],struct.pack('>I',c.code))
    c.write(c.code+0x807a,struct.pack('>HI',0x4ef9,S+sy['translation_velocity']))
    if sabotage:c.write(S+sy['timing_scene_velocity'],b'\x4e\x75')
    def put(n,fmt,v):c.write(S+sy[n],struct.pack('>'+fmt,v))
    def own(n):c.run(S+sy[n]-c.code)
    def vec(data,off,i):return unpack(data,off+12*i,'3i')
    rows=[];checked=0;changed=0;fallback=0
    for name in meta['scene_samples']:
        data=(run/(name+'-restored.bin')).read_bytes()
        old=(run/(name+'-slave.bin')).read_bytes()
        mask=old[oldsy['timing_scene_predictable']:oldsy['timing_scene_predictable']+64]
        c.write(c.data,data);put('timing_active','H',1);put('timing_scene_valid','H',0)
        put('translation_active','H',0);put('timing_hz','I',60)
        own('timing_scene_snapshot');own('timing_scene_snapshot')
        c.write(S+sy['timing_scene_predictable'],mask)
        # release_predict adds one display field; select exactly one world tick.
        c.data_value(0x7f02,'I',100);c.write(S+sy['timing_clock'],struct.pack('>II',100,50))
        own('timing_player_camera');before=c.read(c.data,0xfda0)
        own('timing_scene_begin');shown=c.read(c.data,0xfda0)
        assert int.from_bytes(c.read(S+sy['timing_scene_fraction'],4),'big')==60
        predicted={}
        for slot in range(1,61):
            kind=unpack(data,0x96fe+2*slot,'h')[0]
            if not mask[0] or not mask[slot] or kind<3 or kind==7:continue
            pos=vec(data,0x919a,slot);vel=vec(data,0x9d6c,slot)
            eligible=(slot<10 and kind>=11 and (unpack(data,0x9564+2*slot,'h')[0]==-1 or
                      (unpack(data,0x9564+2*slot,'h')[0] in (1,3) and unpack(data,0xbb14+2*slot,'h')[0]>1))
                      and unpack(data,0xba52+2*slot,'h')[0]!=1)
            expected=tuple(p+v for p,v in zip(pos,vel))
            if eligible:
                ref.write(ref.data,data)
                for axis,entry in enumerate((0x2acb2,0x2acf2,0x2ad32)):
                    angle=unpack(old,oldsy['timing_scene_angles']+128*axis+2*slot,'h')[0]
                    if angle:ref.run(entry,struct.pack('>hh',angle,slot))
                ref.run(0x7d1a,struct.pack('>h',slot))
                expected=vec(ref.read(ref.data,0xfda0),0x919a,slot)
            else:fallback+=1
            got=vec(shown,0x919a,slot)
            assert got==expected,('forecast oracle',name,slot,got,expected)
            checked+=1;changed+=got!=tuple(p+v for p,v in zip(pos,vel))
            predicted[slot]=got
        own('timing_scene_end')
        assert c.read(c.data,0xfda0)==before,('render leak',name)
        rows.append((data,mask,predicted))
    errors=[];old_errors=[];constant=[];uncontrolled=[]
    for (prior,mask,pred),(data,nextmask,_) in zip(rows,rows[1:]):
        if (unpack(data,0x914c,'H')[0]-unpack(prior,0x914c,'H')[0])&65535!=1:continue
        for slot,forecast in pred.items():
            kind=unpack(data,0x96fe+2*slot,'h')[0]
            if not nextmask[slot] or kind!=unpack(prior,0x96fe+2*slot,'h')[0]:continue
            actual=vec(data,0x919a,slot);pos=vec(prior,0x919a,slot);vel=vec(prior,0x9d6c,slot)
            e=math.dist(forecast,actual)/256
            if kind>=11:
                errors.append(e);old_errors.append(math.dist(tuple(p+v for p,v in zip(pos,vel)),actual)/256)
                if e>1:uncontrolled.append(dict(slot=slot,error_km=e,
                    set_speed_before=unpack(prior,0x99be+4*slot,'i')[0],set_speed_after=unpack(data,0x99be+4*slot,'i')[0]))
            elif kind in (3,4,5,8):constant.append(e)
    c.close();ref.close()
    assert checked and changed and fallback
    assert max(constant,default=0)==0, 'constant-velocity class diverged'
    result=dict(model=model,run=run.name,oracle_cases=checked,changed_forecasts=changed,
        constant_or_fallback_cases=fallback,ships_km=stats(errors),old_ships_km=stats(old_errors),
        constant_velocity_km=stats(constant),residuals_over_1km=uncontrolled)
    # Require >50% p95 and >25% max reduction from the phase-10 gate, without
    # excluding AI speed changes. These thresholds are regression limits, not
    # promises for arbitrary future controller changes or longer horizons.
    assert result['ships_km']['p95']<4.357/2 and result['ships_km']['maximum']<8.982*.75
    return result


def contracts(build, run):
    meta=json.loads((run/'result.json').read_text())
    memory=(run/'start-fast.bin').read_bytes();blob=(build/'payload.bin').read_bytes()
    sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(build/'slave.lst').read_text(),re.M)}
    count=0
    for model in (2,4):
        c=CPU(memory,meta,model);ref=CPU(memory,meta,model)
        c.write(S,blob);c.write(S+sy['timing_game'],struct.pack('>I',c.code))
        c.write(c.code+0x807a,struct.pack('>HI',0x4ef9,S+sy['translation_velocity']))
        for action,timer,stage in ((-1,100,0),(1,100,0),(3,100,0),(1,1,0),(3,1,0),(5,100,0),(-1,100,1)):
            for hz in (50,60):
                for fraction in (0,1,hz//2,hz,hz+20):
                    c.reset();c.data_value(0x9700,'h',12);c.data_value(0x9566,'h',action)
                    c.data_value(0xbb16,'h',timer);c.data_value(0xba54,'h',stage)
                    before=c.read(c.data,0xfda0);ref.write(ref.data,before)
                    vel=unpack(before,0x9d78,'3i')
                    eligible=action in (-1,1,3) and (action==-1 or timer>1) and stage!=1
                    if eligible:
                        ref.run(0x7d1a,struct.pack('>h',1))
                        future=unpack(ref.read(ref.data,0xfda0),0x9d78,'3i')
                        want=tuple(v+trunc((n-v)*fraction,hz) for v,n in zip(vel,future))
                    else:want=vel
                    c.run(S+sy['timing_scene_velocity']-c.code,registers={13:1,14:12,15:fraction,16:hz})
                    expected=bytearray(before);struct.pack_into('>3i',expected,0x9d78,*want)
                    assert c.read(c.data,0xfda0)==expected,('velocity or side effect',model,action,timer,stage,hz,fraction)
                    assert [c.reg(r) for r in (13,14,15,16)]==[1,12,fraction,hz]
                    count+=1
        c.close();ref.close()
    return count


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path)
    p.add_argument('--run',type=Path,default=ROOT/'tmp/phase10-isolated-turn-ntsc')
    p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    if a.output.exists() or (ROOT/'tmp').resolve() not in a.output.resolve().parents:p.error('fresh tmp output required')
    contract_count=contracts(a.build,a.run)
    rows=[check(a.build,a.run,m) for m in (2,4)]
    try:check(a.build,a.run,2,True)
    except AssertionError as e:
        assert 'forecast oracle' in str(e);negative=str(e)
    else:raise AssertionError('disabled heading solver escaped oracle')
    a.output.write_text(json.dumps(dict(runs=rows,contract_cases=contract_count,negative_control=negative,
        build_sha256=hashlib.sha256((a.build/'payload.bin').read_bytes()).hexdigest()),indent=2)+'\n')
    print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
