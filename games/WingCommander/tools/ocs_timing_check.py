#!/usr/bin/env python3
"""Execute pinned OCS timing owners. Functional results only, never performance."""
import argparse, ctypes as C, json, struct
from timing_audit_check import CPU as SharedCPU, u, ck, P, I, UNICORN_LIBRARY
from ocs_reconstruct import new_output, sha
from variants import ocs

class CPU(SharedCPU):
    def __init__(self, model):
        from ocs_timing_inventory import load, BASES
        memory,layout=load()
        self.h=P();ck(u.uc_open(7,1<<30,C.byref(self.h)))
        ck(u.uc_ctl(self.h,7|(1<<26)|(1<<30),I(model)))
        ck(u.uc_mem_map(self.h,0,0x1000000,7));self.write(0,bytes(memory))
        self.code,self.data=BASES[:2]
        self.initial=self.read(self.data,ocs.HUNKS[1][2])

SCHEDULES={'10Hz':[10], '20Hz':[20], '50Hz':[50], '60Hz':[60],
           '10to50':[5,25], '50to10':[25,5]}
# Every schedule covers one second; two-part schedules cover half a second each.
def check(cpu):
    result={}
    for schedule,parts in SCHEDULES.items():
        n=sum(parts);rows={};cpu.reset()
        cpu.data_value(0x8928,'i',0);cpu.data_value(0x892c,'i',0);cpu.data_value(0x8930,'i',0)
        cpu.data_value(0x94fa,'i',5120);cpu.data_value(0x94fe,'i',-1);cpu.data_value(0x9502,'i',1)
        for _ in range(n):cpu.run(0x7e2c,end=0x7e5c,registers={11:0})
        pos=[cpu.data_value(o,'i') for o in (0x8928,0x892c,0x8930)]
        assert pos==[5120*n,-n,n];rows['position_fixed8']=pos
        cpu.reset();cpu.data_value(0x8d06,'h',100)
        for _ in range(n):cpu.run(0x2a6e0,struct.pack('>I',cpu.data+0x8d06))
        assert cpu.data_value(0x8d06,'h')==100-n;rows['angular_decay']=100-n
        cpu.reset();cpu.data_value(0x914c,'i',5120);cpu.data_value(0x9cda,'i',100000)
        for _ in range(n):cpu.run(0xc8ee,struct.pack('>h',0))
        assert cpu.data_value(0x9cda,'i')==100000-5*n;rows['fuel']=100000-5*n
        cpu.reset();cpu.data_value(0x9e7f,'b',0);cpu.data_value(0x8cd4,'h',0)
        for o in (0x9d02,0x9d04,0xb628,0xb62a):cpu.data_value(o,'h',100)
        for _ in range(n):cpu.run(0xc9ac,struct.pack('>h',0))
        value=cpu.data_value(0x8cd4,'h');assert value==min(100,2*n);rows['gun_energy']=value
        cpu.reset();cpu.data_value(0x9e64,'h',100)
        for _ in range(n):cpu.run(0x2018)
        assert cpu.data_value(0x9e64,'h')==100-n;rows['message_remaining']=100-n
        cpu.reset();cpu.data_value(0xb096,'b',100)
        for _ in range(n):cpu.run(0x7550,end=0x7562,registers={11:0})
        assert cpu.data_value(0xb096,'b')==100-n;rows['missile_remaining']=100-n
        cpu.reset();cpu.data_value(0x6f9a,'I',0x12345678)
        for _ in range(n):cpu.run(0x2bbcc)
        rows['rng']=cpu.data_value(0x6f9a,'I')
        assert rows['rng']=={10:105702712,20:88318456,30:2990193848,50:833375288,60:2949161208}[n]
        cpu.reset();cpu.data_value(0x8f84,'h',0);cpu.data_value(0x9e7f,'b',0)
        cpu.data_value(0x5432,'h',4)
        for o in (0x9d02,0x9d04):cpu.data_value(o,'h',0)
        for o in (0xb628,0xb62a):cpu.data_value(o,'h',100)
        for tick in range(1,n+1):
            cpu.data_value(0x88da,'H',tick);cpu.run(0xc91a,struct.pack('>h',0))
        shields=[cpu.data_value(o,'h') for o in (0x9d02,0x9d04)]
        assert shields==[n//4,n//4];rows['shields']=shields
        cpu.reset();cpu.data_value(0x8c54,'h',100)
        for _ in range(n):cpu.run(0x741e,struct.pack('>h',0))
        assert cpu.data_value(0x8c54,'h')==100-n;rows['object_life']=100-n
        cpu.reset();cpu.write(cpu.data+0xbbc2,bytes([100]*6))
        for _ in range(n):cpu.run(0x15dec)
        assert cpu.read(cpu.data+0xbbc2,6)==bytes([100-n]*6);rows['six_byte_timers']=100-n
        cpu.reset();cpu.data_value(0xb102,'h',100)
        for _ in range(n):cpu.run(0x7b86,end=0x7b94,registers={11:0})
        assert cpu.data_value(0xb102,'h')==100-n;rows['afterburner_timer']=100-n
        cpu.reset();cpu.data_value(0xb860,'h',0)
        for _ in range(n):cpu.run(0x12466,end=0x12474,registers={11:0})
        assert cpu.data_value(0xb860,'h')==n;rows['action_elapsed_steps']=n
        cpu.reset();cpu.data_value(0x3872,'h',-1);eligible=0
        for tick in range(1,n+1):
            cpu.data_value(0x88da,'H',tick);cpu.run(0x873c,end=0x875a,registers={11:1})
            eligible+=bool(cpu.reg(9)&0xffff)
        assert eligible==n//4;rows['ai_decision_opportunities']=eligible
        cpu.reset();cpu.data_value(0x8f84,'h',0)
        cpu.data_value(0x5440,'I',0x180000);cpu.data_value(0x544a,'h',4)
        cpu.write(0x180000,bytes(512));cpu.data_value(0xb664,'h',4);cpu.data_value(0xb6e4,'h',0)
        for _ in range(n):cpu.run(0x2800a,struct.pack('>h',0))
        assert cpu.data_value(0xb6e4,'h')==n//4;rows['effect_script_advances']=n//4
        result[schedule]=rows
    assert result['10Hz']['rng']!=result['50Hz']['rng']
    assert result['10to50']==result['50to10']
    bounds={}
    for initial in (0,1,127,128,255):
        cpu.reset();cpu.data_value(0xb096,'B',initial)
        cpu.run(0x7550,end=0x7562,registers={11:0})
        got=cpu.data_value(0xb096,'B');want=initial-1 if 0<initial<128 else initial
        assert got==want;bounds[str(initial)]=got
    # Real object-overlap routine, controlled active slots and collision mask.
    hits={}
    for x in (-20,0,20):
        cpu.reset();cpu.write(cpu.data+0x8e8c,bytes(122));cpu.write(cpu.data+0x960,bytes(84))
        cpu.data_value(0x8e8c,'h',8);cpu.data_value(0x8e8e,'h',12);cpu.data_value(0x96c,'B',1)
        for o in (0x9288,0x928a):cpu.data_value(o,'h',5)
        cpu.write(cpu.data+0x8928,struct.pack('>6i',x*256,0,0,0,0,0))
        cpu.run(0x156e6,struct.pack('>h',0));hits[str(x)]=cpu.reg(9)&0xffff
    assert hits=={'-20':65535,'0':1,'20':65535},hits
    result['boundary_checks']=dict(signed_byte_lifetime=bounds,point_overlap=hits)
    return result


# Counter-writer slices supplement full-routine checks. They deliberately stop
# before side effects: this proves the clock arithmetic, not the whole mission.
WRITERS = (
    ('cockpit_selection',0x4890,0x4894,0xa8b8,'h',-1),
    ('camera_state_wait',0x699e,0x69a6,0xb03e,'h',1),
    ('ship_death_delay',0xa320,0xa328,0xb65a,'b',-1),
    ('lock_countdown',0xd1f0,0xd1f4,0x3890,'h',-1),
    ('collision_cooldown',0xe41a,0xe422,0xb472,'b',-1),
    ('class1_elapsed',0xe830,0xe83e,0xb880,'h',1),
    ('ai_stagger_delay',0xf81e,0xf826,0xb8b6,'b',-1),
    ('contact_hold',0x107d0,0x107de,0xb8ca,'h',-1),
    ('class1_countdown',0x13ee4,0x13ef2,0xb880,'h',-1),
    ('demo_script_wait',0x18052,0x1805a,0x8cce,'h',-1),
)
ACTION_WRITERS = (
    (0xd0f2,1),(0xda24,1),(0xdae6,1),(0x12472,1),(0x1257a,1),
    (0x125be,1),(0x12678,-1),(0x12772,-1),(0x12870,1),(0x128a8,1),
    (0x12918,1),(0x12a78,1),(0x12b2e,1),(0x130b4,1),(0x136da,1),
    (0x1377c,-1),
)

def extended_check(cpu):
    results={}
    for schedule,parts in SCHEDULES.items():
        n=sum(parts);rows={}
        for name,entry,end,offset,fmt,delta in WRITERS:
            cpu.reset();cpu.data_value(offset,fmt,60)
            for _ in range(n):cpu.run(entry,end=end,registers={11:0})
            value=cpu.data_value(offset,fmt);assert value==60+delta*n,(name,value,n)
            rows[name]=value
        for entry,delta in ACTION_WRITERS:
            cpu.reset();cpu.data_value(0xb860,'h',100)
            for _ in range(n):cpu.run(entry,end=entry+2,registers={1:cpu.data+0xb860})
            assert cpu.data_value(0xb860,'h')==100+delta*n
        rows['action_writer_sites']=len(ACTION_WRITERS)
        # Acceleration writeback plus position integration, real vector routines.
        cpu.reset();cpu.write(cpu.data+0x8928,bytes(12));cpu.write(cpu.data+0x94fa,bytes(12))
        cpu.write(0x180000,struct.pack('>3i',256,0,0))
        for _ in range(n):cpu.run(0x7df0,end=0x7e5c,registers={6:0x180018,11:0})
        assert cpu.data_value(0x94fa,'i')==256*n
        assert cpu.data_value(0x8928,'i')==128*n*(n+1)
        rows['accelerated_position_fixed8']=cpu.data_value(0x8928,'i')
        # Full angular update: controlled orthogonal basis and one active axis.
        cpu.reset()
        for o,v in ((0x98d6,(0,0,-256)),(0xaa3e,(0,256,0)),(0xad3e,(-256,0,0))):
            cpu.write(cpu.data+o,struct.pack('>3i',*v))
        for o in (0x8d06,0x8d86,0x8e06):cpu.data_value(o,'h',0)
        for _ in range(n):
            cpu.data_value(0x8d06,'h',1);cpu.run(0x79fc,struct.pack('>h',0))
        rows['orientation_forward']=list(struct.unpack('>3i',cpu.read(cpu.data+0x98d6,12)))
        # Two native counter masks: mission poll and encounter poll, not seconds.
        masks={}
        for entry,end,mask in ((0x292,0x29a,31),(0x2a6,0x2ae,15),(0x636a,0x6372,3)):
            count=0
            for tick in range(n):
                cpu.data_value(0x88de if mask==3 else 0x88da,'H',tick)
                cpu.run(entry,end=end);count+=cpu.reg(9)==0
            assert count==(n+mask)//(mask+1)
            masks[str(mask+1)]=count
        rows['periodic_opportunities']=masks
        # A fixed-rate VBL producer is independent of the chosen world schedule.
        cpu.reset();cpu.data_value(0x77fe,'I',0)
        for _ in range(50):cpu.run(0x342a6,end=0x342ac)
        assert cpu.data_value(0x77fe,'I')==50;rows['vbl_counter']=50
        # Presentation consumes the same random stream as simulation.
        cpu.reset();cpu.data_value(0x6f9a,'I',0x12345678)
        for _ in range(n//2):cpu.run(0x4162,end=0x416e)
        rows['comms_rng']=cpu.data_value(0x6f9a,'I')
        # Full sampled proximity predicate along one equal-time path. Samples
        # supplied by the harness isolate sampling from integration error.
        cpu.reset();cpu.data_value(0xa1f6,'h',-100);elapsed=0.0;near=0
        for count in parts:
            dt=1.0/len(parts)/count
            for _ in range(count):
                elapsed+=dt
                cpu.data_value(0xb0fe,'h',int(abs(200*(elapsed-0.055))))
                cpu.run(0x115f2,struct.pack('>h',2));near+=bool(cpu.reg(9)&0xffff)
        rows['proximity_samples_inside']=near
        cpu.reset();cpu.data_value(0xa9b8,'H',16384)
        for _ in range(n):cpu.run(0x767a,end=0x7686,registers={11:0})
        assert cpu.data_value(0xa9b8,'H')==16384>>n
        rows['despawn_size']=cpu.data_value(0xa9b8,'H')
        # Landing has its own direct world-counter writer and shrink step.
        cpu.reset();cpu.data_value(0x88da,'H',0);cpu.data_value(0xbf58,'h',200)
        for _ in range(n):cpu.run(0x1a750,end=0x1a758)
        assert cpu.data_value(0x88da,'H')==n
        assert cpu.data_value(0xbf58,'h')==200-2*n
        rows['landing_size']=cpu.data_value(0xbf58,'h')
        # Record actual expiry time, including a rate change halfway through.
        cpu.reset();cpu.data_value(0xb096,'b',20);elapsed=0.0;expired=None
        for count in parts:
            dt=1.0/len(parts)/count
            for _ in range(count):
                cpu.run(0x7550,end=0x7562,registers={11:0});elapsed+=dt
                if expired is None and cpu.data_value(0xb096,'b')==0:expired=round(elapsed,6)
        rows['missile_expiry_seconds']=expired
        results[schedule]=rows
    assert results['10Hz']['proximity_samples_inside']==0
    assert results['20Hz']['proximity_samples_inside']>0
    assert results['10Hz']['comms_rng']!=results['50Hz']['comms_rng']
    assert results['10Hz']['orientation_forward']!=results['50Hz']['orientation_forward']
    assert results['10to50']['missile_expiry_seconds']==0.8
    assert results['50to10']['missile_expiry_seconds']==0.4
    # Per-event bookkeeping has no time argument. Five identical events must
    # remain five, irrespective of an otherwise idle tick schedule.
    event_counts={}
    for schedule in SCHEDULES:
        cpu.reset();cpu.data_value(0x88b4,'h',0)
        for _ in range(5):cpu.run(0xb0fe,end=0xb102,registers={11:1})
        event_counts[schedule]=cpu.data_value(0x88b4,'h')
    assert set(event_counts.values())=={5}
    # Effect script branches: frame, growth, shrink, jump and removal.
    effects={}
    for name,words,size,want_size,want_index in (
        ('frame',(7,),64,64,1),('grow',(0x401,),64,65,1),
        ('grow_fraction',(0x401,),63,63,1),('shrink',(0x801,),64,63,1),
        ('jump',(0x9002,0,7),64,64,3),('remove',(0xa000,),64,64,0)):
        cpu.reset();cpu.data_value(0x8f84,'h',0)
        cpu.data_value(0x5440,'I',0x180000);cpu.data_value(0x544a,'h',1)
        cpu.write(0x180000,struct.pack('>'+'H'*len(words),*words))
        cpu.data_value(0xb664,'h',1);cpu.data_value(0xb6e4,'h',0);cpu.data_value(0xa9b8,'H',size)
        cpu.run(0x2800a,struct.pack('>h',0))
        assert cpu.data_value(0xa9b8,'H')==want_size
        assert cpu.data_value(0xb6e4,'h')==want_index
        if name=='remove':assert cpu.data_value(0xa0f6,'H')==0x8001
        if name in ('frame','jump'):assert cpu.data_value(0xa37a,'H')==7
        effects[name]=dict(size=want_size,index=want_index)
    # Word overflow and a literal sentinel: neither can be safely scaled blindly.
    cpu.reset();cpu.data_value(0xb860,'H',32767)
    cpu.run(0x12466,end=0x12474,registers={11:0})
    assert cpu.data_value(0xb860,'h')==-32768
    cpu.data_value(0x8c54,'h',-1);cpu.run(0x741e,struct.pack('>h',0))
    assert cpu.data_value(0x8c54,'h')==-1
    cpu.data_value(0xb860,'h',100);cpu.data_value(0xb876,'B',5)
    cpu.run(0x11396,struct.pack('>hh',0,13))
    assert cpu.data_value(0xb860,'h')==0 and cpu.data_value(0xb876,'B')==0
    assert cpu.data_value(0xb0e0,'h')==13
    # A deadline test depends on VBL elapsed time, not world iteration count.
    cpu.data_value(0x77fe,'I',50)
    cpu.run(0xdbc,end=0xdc2,registers={11:60})
    assert cpu.reg(9)==10
    # Instrument limitation: report, never treat the high-bit memory-shift
    # discrepancy as a game defect. Positive-size timing checks above are valid.
    cpu.data_value(0xa9b8,'H',0x8000)
    for _ in range(10):cpu.run(0x767a,end=0x7686,registers={11:0})
    shift_probe=dict(logical_expected=32,observed=cpu.data_value(0xa9b8,'H'))
    results['boundaries']=dict(event_counts=event_counts,
                               effect_opcodes=effects,action_reset=True,vbl_deadline_remaining=10,high_bit_shift_probe=shift_probe,word_wrap=-32768,life_sentinel=-1)
    return results


def owner_check(cpu):
    results={}
    # Execute the actual fixed-point HUD operations, including native magnitude
    # and fixed multiplication, rather than inferring units from CD32.
    cpu.reset();cpu.data_value(0x914c,'i',5120)
    cpu.run(0x203a,end=0x2046)
    assert cpu.reg(11)==200
    cpu.write(cpu.data+0x94fa,struct.pack('>3i',5120,0,0))
    cpu.run(0x2062,end=0x2084)
    assert cpu.reg(12)==200
    cpu.run(0x2b930,struct.pack('>I',cpu.data+0x94fa))
    assert cpu.reg(9)==5120
    cpu.write(0x180000,struct.pack('>i',5120))
    cpu.run(0x2e44,end=0x2e4e,registers={6:0x180020})
    assert cpu.data_value(0xa08e,'i')==20
    results['units']=dict(hud_kps=200,displacement_km=20,target_hz=10)
    # Native field handler (original callback stubs are RTS), including rollover
    # and expiry. This is producer semantics, not interrupt-delivery timing.
    cpu.reset();cpu.data_value(0x77fe,'I',0xffffffff);cpu.data_value(0x7802,'h',2)
    for expected in ((0,1),(1,0),(2,0)):
        cpu.run(0x342a2)
        assert (cpu.data_value(0x77fe,'I'),cpu.data_value(0x7802,'h'))==expected
    results['field_wrap_and_countdown']=True
    # OCS has a 64-byte event queue, not CD32's 16-byte previous-pad image.
    queue=cpu.code+0x34568;original=cpu.read(queue,64)
    try:
        cpu.reset();cpu.data_value(0x7808,'h',63);cpu.data_value(0x780a,'h',1)
        cpu.data_value(0x7804,'I',0);cpu.write(queue+63,b'A');cpu.write(queue,b'B')
        got=[]
        for _ in range(3):cpu.run(0x345a8);got.append(cpu.reg(9))
        assert got==[65,66,0xffffffff]
        assert cpu.data_value(0x7808,'h')==1
        results['keyboard_queue_wrap']=got
    finally:cpu.write(queue,original)
    # Field-sampled button state and consume-on-read edge bytes. Polling a held
    # sample twice must not redeliver the two event flags.
    cpu.reset();source=cpu.data+0x77c8;dest=0x180100
    cpu.write(source,bytes((1,0,0,0,1,0,1,1,0,0,0,0)))
    snapshots=[]
    for _ in range(2):
        cpu.run(0x33f42,struct.pack('>hI',1,dest),registers={1:source})
        snapshots.append(list(cpu.read(dest,9)))
    assert snapshots[0][4:8]==[1,0,1,1] and snapshots[1][4:8]==[1,0,0,0]
    results['joystick_edge_consumption']=snapshots
    # VBL-owned button hold/click windows are distinct from world/input polls.
    cpu.reset();cpu.write(source,bytes(12))
    cpu.data_value(0x77d4,'h',3);cpu.data_value(0x77d6,'h',5)
    held=[]
    for pressed in (0,1,1,1,1,1,0):
        cpu.run(0x33fa4,registers={1:source,9:pressed})
        held.append((int.from_bytes(cpu.read(source+10,2),'big'),cpu.read(source+5,1)[0]))
    assert held==[(0,0),(0,0),(1,0),(2,0),(3,0),(3,1),(0,1)]
    cpu.write(source,bytes(12))
    for pressed in (1,1,0):cpu.run(0x33fa4,registers={1:source,9:pressed})
    assert cpu.read(source+7,1)==b'\x01' and cpu.read(source+10,2)==b'\x00\x05'
    for _ in range(5):cpu.run(0x33fa4,registers={1:source,9:0})
    assert cpu.read(source+10,2)==b'\x00\x00'
    results['joystick_field_timers']=held
    # Audio tempo accumulator slices: field-owned subtraction and native 125
    # reload. Actual decoder, DMA and interrupt delivery remain excluded.
    audio={}
    for fields,tempo in ((50,125),(60,104)):
        cpu.reset();cpu.data_value(0x5228,'h',tempo);cpu.data_value(0x522a,'h',125)
        ticks=0
        for _ in range(fields):
            cpu.run(0x26de0,end=0x26de8)
            while cpu.data_value(0x522a,'h')<=0:
                cpu.run(0x26df4,end=0x26dfa);ticks+=1
        assert ticks==fields*tempo//125
        assert cpu.data_value(0x522a,'h')==125-fields*tempo+ticks*125
        audio[str(fields)]=dict(tempo=tempo,steps=ticks,remainder=cpu.data_value(0x522a,'h'))
    results['audio_field_accumulator']=audio
    # Held axes change on each native input call and are clamped; releasing the
    # input damps by two. No OS poll or firing event is stubbed into this test.
    cpu.reset();cpu.write(cpu.data+0xbe52,bytes(0x88))
    cpu.write(cpu.data+0x8e86,bytes(6));cpu.data_value(0x3870,'h',0)
    cpu.data_value(0xbed2,'B',1)
    axes=[]
    for _ in range(12):cpu.run(0x183e4);axes.append(cpu.data_value(0x8e88,'h'))
    assert axes==[-1,-2,-3,-4,-5,-6,-7,-8,-9,-9,-9,-9],axes
    cpu.data_value(0xbed2,'B',0);cpu.run(0x183e4)
    assert cpu.data_value(0x8e88,'h')==-7
    results['held_axis_and_release']=axes+[-7]
    # Score/time arithmetic lives in the drawing path before D2. No formatting
    # callback is executed in this bounded slice.
    scores={}
    for n in (10,50):
        cpu.reset();cpu.data_value(0x890c,'I',0);cpu.data_value(0x8906,'h',100)
        for _ in range(n):cpu.run(0x43a,end=0x44a)
        assert cpu.data_value(0x890c,'I')==n and cpu.data_value(0x8906,'h')==100-n
        scores[str(n)]=dict(score=n,time=100-n)
    results['simulator_score_time']=scores
    # Simulator end countdown reaches the native exit/bonus branch exactly once.
    cpu.reset();cpu.data_value(0xaf4,'h',1);cpu.data_value(0xac,'h',2)
    cpu.data_value(0xaa,'h',0);cpu.data_value(0x386a,'h',-1)
    cpu.data_value(0x8908,'I',123);cpu.data_value(0x890c,'I',0)
    cpu.write(cpu.data+0x8928,bytes(12))
    cpu.run(0x532,end=0x580);assert cpu.data_value(0xaa,'h')==0
    cpu.run(0x532,end=0x580);assert cpu.data_value(0xaa,'h')==1
    assert cpu.data_value(0x890c,'I')==123
    cpu.run(0x532,end=0x580);assert cpu.data_value(0x890c,'I')==123
    results['simulator_exit_once']=True
    # The same life array is a gun cooldown for ship slots. A constructor reload
    # touches that word, not the ship's identity or pose. Cover player and AI.
    reloads=[]
    for slot in (0,1,9):
        cpu.reset();cpu.data_value(0x8c54+2*slot,'h',0)
        before=cpu.read(cpu.data,ocs.HUNKS[1][2])
        cpu.run(0xc614,end=0xc624,registers={12:slot})
        after=cpu.read(cpu.data,len(before))
        expected=bytearray(before);expected[0x8c54+2*slot:0x8c56+2*slot]=struct.pack('>h',12)
        assert after==expected
        cpu.run(0x741e,struct.pack('>h',slot))
        assert cpu.data_value(0x8c54+2*slot,'h')==11
        reloads.append(slot)
    results['gun_reload_is_not_reset']=reloads
    # Fault polling is reached after each ordinary draw. Native RNG advances
    # on the eligible trial and stays unchanged when the subsystem is healthy.
    seeds=[]
    for damage in (0,4):
        cpu.reset();cpu.data_value(0x9e7e,'B',damage)
        cpu.data_value(0x6f9a,'I',0x12345678)
        cpu.run(0xacfa)
        seeds.append(cpu.data_value(0x6f9a,'I'))
    assert seeds[0]!=0x12345678 and seeds[1]==0x12345678
    results['fault_poll_rng']=seeds
    # The draw-based missile-lock trial must be tick-owned after decoupling.
    cpu.reset();opportunities=0
    for draw in range(50):
        cpu.data_value(0x88de,'H',draw);cpu.run(0x3944,end=0x394c)
        opportunities+=cpu.reg(9)==0
    assert opportunities==7
    results['target_draw_mask']=opportunities
    return results


def dispatch_check(cpu):
    from ocs_timing_inventory import load, PROFILE
    from timing_inventory import inventory
    memory,layout=load()
    graph,_=inventory(memory,layout,[0x2be,0x512,0x18d14,0x640,0x1eeb2],PROFILE)
    assert not graph['unresolved'] and not graph['external']
    count=guards=0
    for table in graph['tables']:
        at=int(table['at'].split(':')[1],16)
        for index,dest in enumerate(table['entries']):
            assert dest.startswith('O:');target=int(dest.split(':')[1],16)
            if at==0x13ad6:
                cpu.data_value(0xb0e0,'h',index)
                cpu.run(0x13abc,end=target,registers={11:0})
            elif at==0x30664:cpu.run(at-4,end=target,registers={9:2*index})
            elif at==0x2bae6:cpu.run(at-4,end=target,registers={10:2*index})
            else:cpu.run(at-4,end=target,registers={9:2*index})
            count+=1
        if at not in (0x13ad6,0x30664):
            if at==0x2bae6:cmp_at=0x2bada;reg=10
            else:
                cmp_at=next(at-n for n in (12,14) if cpu.read(cpu.code+at-n,2)==bytes.fromhex('0c40'));reg=9
            branch=cmp_at+4;raw=cpu.read(cpu.code+branch,4)
            disp=struct.unpack('>b',raw[1:2])[0] if raw[1] else struct.unpack('>h',raw[2:4])[0]
            for invalid in (len(table['entries']),65535):
                cpu.run(cmp_at,end=branch+2+disp,registers={reg:invalid});guards+=1
    for invalid in (-1,47):
        cpu.data_value(0xb0e0,'h',invalid)
        cpu.run(0x13a96,end=0x13adc,registers={11:0})
    assert (len(graph['tables']),count,guards)==(72,791,140)
    return dict(tables=72,targets=count,bounds_rejections=guards,action_bounds_rejections=2)


def negative_controls(cpu):
    from ocs_timing_inventory import load, PROFILE
    from timing_inventory import inventory
    memory,layout=load();at=cpu.code+0x78b0
    # Change the bounded switch's CMP register: closure must reject it.
    # Lifecycle switch is at O:78b0 (CD32's address is deliberately not used).
    graph,_=inventory(memory,layout,[0x2be],PROFILE)
    table=next(t for t in graph['tables'] if t['at']=='O:078b0')
    cmp_at=next(at-n for n in (12,14) if memory[at-n:at-n+2]==bytes.fromhex('0c40'))
    memory[cmp_at+1]=0x41
    broken,_=inventory(memory,layout,[0x2be],PROFILE)
    assert any(t['at']==table['at'] for t in broken['unresolved'])
    # Change life decrement to increment and require the independent expected
    # result to disagree; restore the executable image immediately afterwards.
    at=cpu.code+0x7444;original=cpu.read(at,2)
    try:
        cpu.write(at,bytes((0x52,original[1])));cpu.reset();cpu.data_value(0x8c54,'h',100)
        cpu.run(0x741e,struct.pack('>h',0))
        assert cpu.data_value(0x8c54,'h')==101
        assert cpu.data_value(0x8c54,'h')!=99
    finally:cpu.write(at,original)
    return dict(dispatch_mutant_rejected=True,lifetime_mutant_rejected=True)


def main():
    if not __debug__:raise ValueError('assertions required')
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args()
    out=new_output(a.output);out.mkdir(parents=True);results={}
    for model,name in ((1,'68000'),(2,'68020')):
        cpu=CPU(model)
        try:results[name]=dict(schedules=check(cpu),extended=extended_check(cpu),
            ocs_owners=owner_check(cpu),dispatch=dispatch_check(cpu),negative_controls=negative_controls(cpu))
        finally:cpu.close()
    assert results['68000']==results['68020']
    from ocs_timing_map import coverage
    responsibilities=coverage(results['68000'])
    report=dict(responsibilities=responsibilities,passed=True,game_sha256=ocs.GAME_SHA,unicorn_sha256=sha(UNICORN_LIBRARY.read_bytes()),models=results)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=True,models=list(results)),indent=2))

if __name__=='__main__':main()
