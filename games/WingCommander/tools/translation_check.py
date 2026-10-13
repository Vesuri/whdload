#!/usr/bin/env python3
"""C2 native field integration against the original acceleration routine."""
import argparse,json,re,struct,math
from pathlib import Path
from timing_audit_check import CPU
from cd32_runtime import ROOT,locate
S=0x180000
POS=0x919a;VEL=0x9d6c

def trunc(n,d):return (abs(n)//d)*(-1 if n<0 else 1)
def vec(c,off):return struct.unpack('>3i',c.read(c.data+off,12))
def putvec(c,off,v):c.write(c.data+off,struct.pack('>3i',*v))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    if a.output.exists() or (ROOT/'tmp').resolve() not in a.output.resolve().parents:p.error('fresh tmp output required')
    memory=(ROOT/'tmp/phase7-combat-controls/start-fast.bin').read_bytes();layout=locate(memory)
    blob=(a.build/'payload.bin').read_bytes();sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)}
    rows=[];fields=0
    for model in (2,4):
      for hz in (50,60):
       for name,initial,target,action,turn in [('steady',5120,5120,-1,False),('ramp',0,7680,-1,False),('brake',5120,0,-1,False),('brake-action',5120,5120,3,False),('turn',5120,5120,-1,True),('burn',5120,5120,1,False),('burn-turn',5120,5120,1,True)]:
        c=CPU(memory,layout,model);oracle=CPU(memory,layout,model);native=CPU(memory,layout,model)
        for q in (c,oracle,native):
            q.data_value(0x3896,'h',0);q.data_value(0xae4,'h',0);q.data_value(0x96fe,'h',12);q.data_value(0x9564,'h',action)
            q.data_value(0xbb14,'h',15);q.data_value(0xbb28,'I',0);q.data_value(0xa7cc,'i',1000000);q.data_value(0x99be,'i',target)
            putvec(q,POS,(0,0,0));putvec(q,VEL,(0,0,initial));putvec(q,0xa148,(0,0,256));putvec(q,0xb450,(0,256,0));putvec(q,0xb750,(256,0,0))
        c.write(S,blob)
        def put(label,fmt,value):c.write(S+sy[label],struct.pack('>'+fmt,value))
        def own(label):c.run(S+sy[label]-c.code)
        put('timing_game','I',c.code);put('timing_hz','I',hz);put('timing_active','H',1)
        for off,label in ((0x807a,'translation_velocity'),(0x80b6,'translation_position')):c.write(c.code+off,struct.pack('>HI',0x4ef9,S+sy[label]))
        rem=[0]*6;max_speed=0;max_pos=0;max_fuel=0;max_native_step=0;ticks=0
        for field in range(hz*2):
            if turn:
                for q in (c,native):q.run(0x2acf2,struct.pack('>hh',1,0))
            before=c.read(c.data,0xfda0);oldv=vec(c,VEL);oldp=vec(c,POS)
            oracle.write(oracle.data,before)
            # Preview freezes the current action until the real tick; prevent
            # the oracle's timer side effect from selecting the expiry branch.
            if oracle.data_value(0x9564,'h') in (1,3) and oracle.data_value(0xbb14,'h')==1:oracle.data_value(0xbb14,'h',2)
            oracle.run(0x7d1a,struct.pack('>h',0))
            delta=[x-y for x,y in zip(vec(oracle,VEL),oldv)]
            newv=[];newp=[]
            for axis in range(3):
                value=delta[axis]*10+rem[axis];step=trunc(value,hz);rem[axis]=value-step*hz
                newv.append(oldv[axis]+step)
                value=newv[-1]*10+rem[axis+3];step=trunc(value,hz);rem[axis+3]=value-step*hz
                newp.append(oldp[axis]+step)
            own('translation_field')
            assert vec(c,VEL)==tuple(newv),(model,hz,name,field,'velocity',vec(c,VEL),newv,delta)
            assert vec(c,POS)==tuple(newp),(model,hz,name,field,'position',vec(c,POS),newp)
            assert c.read(S+sy['translation_remainders'],24)==struct.pack('>6i',*rem)
            expected=bytearray(before);expected[POS:POS+12]=struct.pack('>3i',*newp);expected[VEL:VEL+12]=struct.pack('>3i',*newv)
            assert c.read(c.data,0xfda0)==expected,(name,field,'field wrote non-motion state')
            if (field+1)%(hz//10)==0:
                own('timing_player_camera');camera=c.read(c.data+POS+61*12,12);pv=c.read(c.data+POS,12)+c.read(c.data+VEL,12)
                oracle.write(oracle.data,c.read(c.data,0xfda0))
                put('timing_in_world','H',1);c.run(0x7d1a,struct.pack('>h',0));put('timing_in_world','H',0)
                oracle.run(0x7d1a,struct.pack('>h',0))
                want=bytearray(oracle.read(oracle.data,0xfda0))
                want[POS:POS+12]=c.read(c.data+POS,12);want[VEL:VEL+12]=c.read(c.data+VEL,12)
                assert c.read(c.data,0xfda0)==want,'native world bookkeeping changed'
                assert pv==c.read(c.data+POS,12)+c.read(c.data+VEL,12),'world moved controlled player again'
                own('timing_player_camera');assert c.read(c.data+POS+61*12,12)==camera,'camera correction at world tick'
                c.run(0xcb78,struct.pack('>h',0))
                native_velocity=vec(native,VEL)
                native.run(0x7d1a,struct.pack('>h',0));native.run(0xcb78,struct.pack('>h',0))
                max_native_step=max(max_native_step,math.dist(vec(native,VEL),native_velocity)*10/256)
                assert c.data_value(0xbb14,'h')==native.data_value(0xbb14,'h') and c.data_value(0x9564,'h')==native.data_value(0x9564,'h')
                max_speed=max(max_speed,abs(math.dist(vec(c,VEL),(0,0,0))-math.dist(vec(native,VEL),(0,0,0)))*10/256)
                max_pos=max(max_pos,math.dist(vec(c,POS),vec(native,POS))/256)
                max_fuel=max(max_fuel,abs(c.data_value(0xa7cc,'i')-native.data_value(0xa7cc,'i')));ticks+=1
            fields+=1
        model_index=c.data_value(0x97f6,'h')
        burn_kps=(2*c.data_value(0x53a4+104*model_index+22,'h')+40)*10
        envelope=max(initial*10/256,target*10/256,burn_kps if action==1 else 0)
        # Action-3 expiry resumes normal thrust at the world boundary. The
        # field integrator has consumed that interval under braking, so allow
        # one native acceleration step at this discrete action transition, plus
        # at most one velocity LSB per sampled field for fixed8 rounding.
        speed_budget=max(envelope*.05,max_native_step+hz*2*10/256) if action==3 else envelope*.05
        assert max_speed<=speed_budget and max_pos<=envelope*2*.10 and max_fuel==0,(name,max_speed,max_pos,max_fuel)
        rows.append(dict(speed_budget_kps=speed_budget,max_native_step_kps=max_native_step,position_budget_km=envelope*2*.10,model=model,hz=hz,case=name,fields=hz*2,ticks=ticks,max_speed_difference_kps=max_speed,max_position_difference_km=max_pos,max_fuel_difference=max_fuel))
        for q in (c,oracle,native):q.close()
    a.output.write_text(json.dumps(dict(fields=fields,cases=rows,zero_tick_corrections=True,field_nonmotion_state_unchanged=True),indent=2)+'\n')
    print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
