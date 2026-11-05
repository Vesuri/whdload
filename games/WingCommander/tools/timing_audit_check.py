#!/usr/bin/env python3
"""Native original-code timing reproductions; Unicorn is not a performance instrument."""
import argparse, ctypes as C, hashlib, json, os, struct
from pathlib import Path
from cd32_runtime import ROOT, BASE, locate

P=C.c_void_p; I=C.c_int; Q=C.c_uint64; Z=C.c_size_t
UNICORN_LIBRARY=Path(os.environ['AMIGA_UNICORN'])/'lib/libunicorn.2.dylib'
u=C.CDLL(str(UNICORN_LIBRARY))
for name,args in {'uc_open':[I,I,C.POINTER(P)],'uc_ctl':[P,C.c_uint32],
 'uc_mem_map':[P,Q,Q,C.c_uint32],'uc_mem_write':[P,Q,P,Z],'uc_mem_read':[P,Q,P,Z],
 'uc_reg_write':[P,I,P],'uc_reg_read':[P,I,P],'uc_emu_start':[P,Q,Q,Q,Z],
 'uc_close':[P]}.items():
    getattr(u,name).argtypes=args;getattr(u,name).restype=I
u.uc_strerror.argtypes=[I];u.uc_strerror.restype=C.c_char_p

def ck(e):
    if e:raise RuntimeError(u.uc_strerror(e).decode())

class CPU:
    def __init__(self,memory,layout,model):
        self.h=P();ck(u.uc_open(7,1<<30,C.byref(self.h)))
        ck(u.uc_ctl(self.h,7|(1<<26)|(1<<30),I(model)))
        ck(u.uc_mem_map(self.h,0,0x1000000,7));self.write(BASE,memory)
        self.code=layout['hunks'][0];self.data=layout['hunks'][1]
        self.initial=memory[self.data-BASE:self.data-BASE+0xfda0]
        self.reset()
    def write(self,a,b):ck(u.uc_mem_write(self.h,a,b,len(b)))
    def read(self,a,n):
        b=C.create_string_buffer(n);ck(u.uc_mem_read(self.h,a,b,n));return b.raw
    def reg(self,r,v=None):
        x=C.c_uint32(v or 0);ck(u.uc_reg_read(self.h,r,C.byref(x)) if v is None else u.uc_reg_write(self.h,r,C.byref(x)));return x.value
    def data_value(self,o,fmt,value=None):
        if value is not None:self.write(self.data+o,struct.pack('>'+fmt,value))
        return struct.unpack('>'+fmt,self.read(self.data+o,struct.calcsize('>'+fmt)))[0]
    def reset(self):self.write(self.data,self.initial)
    def run(self,entry,args=b'',end=None,registers=None):
        for r in range(1,17):self.reg(r,0)
        self.reg(17,0x2700);self.reg(5,self.data+0x7ffe);self.reg(8,0x1f0000)
        self.write(0x1f0000,struct.pack('>I',0x1000)+args)
        for r,v in (registers or {}).items():self.reg(r,v)
        stop=self.code+end if end is not None else 0x1000
        # Unicorn caches blocks containing an earlier stop address. Different
        # slice endpoints require a fresh translation, not a different oracle.
        ck(u.uc_ctl(self.h,10|(1<<30)))
        e=u.uc_emu_start(self.h,self.code+entry,stop,1000000,200000)
        if e:raise RuntimeError(f'{u.uc_strerror(e).decode()} at E:{self.reg(18)-self.code:05x}, entry {entry:x}')
        if self.reg(18)!=stop:raise ValueError(f'native execution budget exceeded: entry={entry:x}, expected={stop-self.code:x}, pc={self.reg(18)-self.code:x}')
    def close(self):ck(u.uc_close(self.h))

SCHEDULES={'10Hz':[10], '20Hz':[20], '50Hz':[50], '60Hz':[60],
           '10to50':[5,25], '50to10':[25,5]}
# Every schedule covers one second; two-part schedules cover half a second each.
def check(cpu):
    result={}
    for schedule,parts in SCHEDULES.items():
        n=sum(parts);rows={};cpu.reset()
        cpu.data_value(0x919a,'i',0);cpu.data_value(0x919e,'i',0);cpu.data_value(0x91a2,'i',0)
        cpu.data_value(0x9d6c,'i',5120);cpu.data_value(0x9d70,'i',-1);cpu.data_value(0x9d74,'i',1)
        for _ in range(n):cpu.run(0x80b6,end=0x80e6,registers={11:0})
        pos=[cpu.data_value(o,'i') for o in (0x919a,0x919e,0x91a2)]
        assert pos==[5120*n,-n,n];rows['position_fixed8']=pos
        cpu.reset();cpu.data_value(0x9578,'h',100)
        for _ in range(n):cpu.run(0x2b66c,struct.pack('>I',cpu.data+0x9578))
        assert cpu.data_value(0x9578,'h')==100-n;rows['angular_decay']=100-n
        cpu.reset();cpu.data_value(0x99be,'i',5120);cpu.data_value(0xa7cc,'i',100000)
        for _ in range(n):cpu.run(0xcb78,struct.pack('>h',0))
        assert cpu.data_value(0xa7cc,'i')==100000-5*n;rows['fuel']=100000-5*n
        cpu.reset();cpu.data_value(0xa971,'b',0);cpu.data_value(0x9546,'h',0)
        for o in (0xa7f4,0xa7f6,0xc03a,0xc03c):cpu.data_value(o,'h',100)
        for _ in range(n):cpu.run(0xcc36,struct.pack('>h',0))
        value=cpu.data_value(0x9546,'h');assert value==min(100,2*n);rows['gun_energy']=value
        cpu.reset();cpu.data_value(0xa956,'h',100)
        for _ in range(n):cpu.run(0x22a0)
        assert cpu.data_value(0xa956,'h')==100-n;rows['message_remaining']=100-n
        cpu.reset();cpu.data_value(0xbaa8,'b',100)
        for _ in range(n):cpu.run(0x77da,end=0x77ec,registers={11:0})
        assert cpu.data_value(0xbaa8,'b')==100-n;rows['missile_remaining']=100-n
        cpu.reset();cpu.data_value(0x6f18,'I',0x12345678)
        for _ in range(n):cpu.run(0x2cb56)
        rows['rng']=cpu.data_value(0x6f18,'I')
        assert rows['rng']=={10:105702712,20:88318456,30:2990193848,50:833375288,60:2949161208}[n]
        cpu.reset();cpu.data_value(0x97f6,'h',0);cpu.data_value(0xa971,'b',0)
        cpu.data_value(0x53b0,'h',4)
        for o in (0xa7f4,0xa7f6):cpu.data_value(o,'h',0)
        for o in (0xc03a,0xc03c):cpu.data_value(o,'h',100)
        for tick in range(1,n+1):
            cpu.data_value(0x914c,'H',tick);cpu.run(0xcba4,struct.pack('>h',0))
        shields=[cpu.data_value(o,'h') for o in (0xa7f4,0xa7f6)]
        assert shields==[n//4,n//4];rows['shields']=shields
        cpu.reset();cpu.data_value(0x94c6,'h',100)
        for _ in range(n):cpu.run(0x76a8,struct.pack('>h',0))
        assert cpu.data_value(0x94c6,'h')==100-n;rows['object_life']=100-n
        cpu.reset();cpu.write(cpu.data+0xc4f4,bytes([100]*6))
        for _ in range(n):cpu.run(0x16084)
        assert cpu.read(cpu.data+0xc4f4,6)==bytes([100-n]*6);rows['six_byte_timers']=100-n
        cpu.reset();cpu.data_value(0xbb14,'h',100)
        for _ in range(n):cpu.run(0x7e10,end=0x7e1e,registers={11:0})
        assert cpu.data_value(0xbb14,'h')==100-n;rows['afterburner_timer']=100-n
        cpu.reset();cpu.data_value(0xc272,'h',0)
        for _ in range(n):cpu.run(0x126f0,end=0x126fe,registers={11:0})
        assert cpu.data_value(0xc272,'h')==n;rows['action_elapsed_steps']=n
        cpu.reset();cpu.data_value(0x3898,'h',-1);eligible=0
        for tick in range(1,n+1):
            cpu.data_value(0x914c,'H',tick);cpu.run(0x89c6,end=0x89e4,registers={11:1})
            eligible+=bool(cpu.reg(9)&0xffff)
        assert eligible==n//4;rows['ai_decision_opportunities']=eligible
        cpu.reset();cpu.data_value(0x97f6,'h',0)
        cpu.data_value(0x53be,'I',0x180000);cpu.data_value(0x53c8,'h',4)
        cpu.write(0x180000,bytes(512));cpu.data_value(0xc076,'h',4);cpu.data_value(0xc0f6,'h',0)
        for _ in range(n):cpu.run(0x28f96,struct.pack('>h',0))
        assert cpu.data_value(0xc0f6,'h')==n//4;rows['effect_script_advances']=n//4
        result[schedule]=rows
    assert result['10Hz']['rng']!=result['50Hz']['rng']
    assert result['10to50']==result['50to10']
    bounds={}
    for initial in (0,1,127,128,255):
        cpu.reset();cpu.data_value(0xbaa8,'B',initial)
        cpu.run(0x77da,end=0x77ec,registers={11:0})
        got=cpu.data_value(0xbaa8,'B');want=initial-1 if 0<initial<128 else initial
        assert got==want;bounds[str(initial)]=got
    # Real object-overlap routine, controlled active slots and collision mask.
    hits={}
    for x in (-20,0,20):
        cpu.reset();cpu.write(cpu.data+0x96fe,bytes(122));cpu.write(cpu.data+0x946,bytes(84))
        cpu.data_value(0x96fe,'h',8);cpu.data_value(0x9700,'h',12);cpu.data_value(0x952,'B',1)
        for o in (0x9afa,0x9afc):cpu.data_value(o,'h',5)
        cpu.write(cpu.data+0x919a,struct.pack('>6i',x*256,0,0,0,0,0))
        cpu.run(0x1597e,struct.pack('>h',0));hits[str(x)]=cpu.reg(9)&0xffff
    assert hits=={'-20':65535,'0':1,'20':65535},hits
    result['boundary_checks']=dict(signed_byte_lifetime=bounds,point_overlap=hits)
    return result


# Counter-writer slices supplement full-routine checks. They deliberately stop
# before side effects: this proves the clock arithmetic, not the whole mission.
WRITERS = (
    ('encounter_hold',0x169e,0x16a2,0xec,'h',-1),
    ('cockpit_selection',0x4b16,0x4b1a,0xb2aa,'h',-1),
    ('camera_state_wait',0x6c28,0x6c30,0xba50,'h',1),
    ('ship_death_delay',0xa5aa,0xa5b2,0xc06c,'b',-1),
    ('lock_countdown',0xd47a,0xd47e,0x38b6,'h',-1),
    ('collision_cooldown',0xe6a4,0xe6ac,0xbe84,'b',-1),
    ('class1_elapsed',0xeaba,0xeac8,0xc292,'h',1),
    ('ai_stagger_delay',0xfaa8,0xfab0,0xc2c8,'b',-1),
    ('contact_hold',0x10a5a,0x10a68,0xc2dc,'h',-1),
    ('class1_countdown',0x1416e,0x1417c,0xc292,'h',-1),
    ('demo_script_wait',0x18918,0x18920,0x9540,'h',-1),
)
ACTION_WRITERS = (
    (0xd37c,1),(0xdcae,1),(0xdd70,1),(0x126fc,1),(0x12804,1),
    (0x12848,1),(0x12902,-1),(0x129fc,-1),(0x12afa,1),(0x12b32,1),
    (0x12ba2,1),(0x12d02,1),(0x12db8,1),(0x1333e,1),(0x13964,1),
    (0x13a06,-1),
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
            cpu.reset();cpu.data_value(0xc272,'h',100)
            for _ in range(n):cpu.run(entry,end=entry+2,registers={1:cpu.data+0xc272})
            assert cpu.data_value(0xc272,'h')==100+delta*n
        rows['action_writer_sites']=len(ACTION_WRITERS)
        # Acceleration writeback plus position integration, real vector routines.
        cpu.reset();cpu.write(cpu.data+0x919a,bytes(12));cpu.write(cpu.data+0x9d6c,bytes(12))
        cpu.write(0x180000,struct.pack('>3i',256,0,0))
        for _ in range(n):cpu.run(0x807a,end=0x80e6,registers={6:0x180018,11:0})
        assert cpu.data_value(0x9d6c,'i')==256*n
        assert cpu.data_value(0x919a,'i')==128*n*(n+1)
        rows['accelerated_position_fixed8']=cpu.data_value(0x919a,'i')
        # Full angular update: controlled orthogonal basis and one active axis.
        cpu.reset()
        for o,v in ((0xa148,(0,0,-256)),(0xb450,(0,256,0)),(0xb750,(-256,0,0))):
            cpu.write(cpu.data+o,struct.pack('>3i',*v))
        for o in (0x9578,0x95f8,0x9678):cpu.data_value(o,'h',0)
        for _ in range(n):
            cpu.data_value(0x9578,'h',1);cpu.run(0x7c86,struct.pack('>h',0))
        rows['orientation_forward']=list(struct.unpack('>3i',cpu.read(cpu.data+0xa148,12)))
        # Two native counter masks: mission poll and encounter poll, not seconds.
        masks={}
        for entry,end,mask in ((0x27c,0x284,31),(0x290,0x298,15),(0x65f4,0x65fc,3)):
            count=0
            for tick in range(n):
                cpu.data_value(0x9150 if mask==3 else 0x914c,'H',tick)
                cpu.run(entry,end=end);count+=cpu.reg(9)==0
            assert count==(n+mask)//(mask+1)
            masks[str(mask+1)]=count
        rows['periodic_opportunities']=masks
        # A fixed-rate VBL producer is independent of the chosen world schedule.
        cpu.reset();cpu.data_value(0x7f02,'I',0)
        for _ in range(50):cpu.run(0x34166,end=0x3416c)
        assert cpu.data_value(0x7f02,'I')==50;rows['vbl_counter']=50
        # Presentation consumes the same random stream as simulation.
        cpu.reset();cpu.data_value(0x6f18,'I',0x12345678)
        for _ in range(n//2):cpu.run(0x43e8,end=0x43f4)
        rows['comms_rng']=cpu.data_value(0x6f18,'I')
        # Full sampled proximity predicate along one equal-time path. Samples
        # supplied by the harness isolate sampling from integration error.
        cpu.reset();cpu.data_value(0xac68,'h',-100);elapsed=0.0;near=0
        for count in parts:
            dt=1.0/len(parts)/count
            for _ in range(count):
                elapsed+=dt
                cpu.data_value(0xbb10,'h',int(abs(200*(elapsed-0.055))))
                cpu.run(0x1187c,struct.pack('>h',2));near+=bool(cpu.reg(9)&0xffff)
        rows['proximity_samples_inside']=near
        cpu.reset();cpu.data_value(0xb3ca,'H',16384)
        for _ in range(n):cpu.run(0x7904,end=0x7910,registers={11:0})
        assert cpu.data_value(0xb3ca,'H')==16384>>n
        rows['despawn_size']=cpu.data_value(0xb3ca,'H')
        # Landing has its own direct world-counter writer and shrink step.
        cpu.reset();cpu.data_value(0x914c,'H',0);cpu.data_value(0xc768,'h',200)
        for _ in range(n):cpu.run(0x1b498,end=0x1b4a0)
        assert cpu.data_value(0x914c,'H')==n
        assert cpu.data_value(0xc768,'h')==200-2*n
        rows['landing_size']=cpu.data_value(0xc768,'h')
        # Record actual expiry time, including a rate change halfway through.
        cpu.reset();cpu.data_value(0xbaa8,'b',20);elapsed=0.0;expired=None
        for count in parts:
            dt=1.0/len(parts)/count
            for _ in range(count):
                cpu.run(0x77da,end=0x77ec,registers={11:0});elapsed+=dt
                if expired is None and cpu.data_value(0xbaa8,'b')==0:expired=round(elapsed,6)
        rows['missile_expiry_seconds']=expired
        results[schedule]=rows
    assert results['10Hz']['proximity_samples_inside']==0
    assert results['20Hz']['proximity_samples_inside']>0
    assert results['10Hz']['comms_rng']!=results['50Hz']['comms_rng']
    assert results['10Hz']['orientation_forward']!=results['50Hz']['orientation_forward']
    assert results['10to50']['missile_expiry_seconds']==0.8
    assert results['50to10']['missile_expiry_seconds']==0.4
    # Input edge predicate versus holding an unchanged previous sample across
    # multiple world ticks. This reproduces duplicate delivery at that boundary.
    edge_counts={}
    for latch_once in (False,True):
        cpu.reset();cpu.data_value(0xc6c8,'B',1);cpu.data_value(0xc6d8,'B',0);count=0
        for _ in range(5):
            cpu.run(0x19130,end=0x19144);count+=bool(cpu.reg(9))
            if latch_once:cpu.run(0x19334,end=0x19344)
        edge_counts['latched' if latch_once else 'reused']=count
    assert edge_counts=={'reused':5,'latched':1}
    # Per-event bookkeeping has no time argument. Five identical events must
    # remain five, irrespective of an otherwise idle tick schedule.
    event_counts={}
    for schedule in SCHEDULES:
        cpu.reset();cpu.data_value(0x9128,'h',0)
        for _ in range(5):cpu.run(0xb388,end=0xb38c,registers={11:1})
        event_counts[schedule]=cpu.data_value(0x9128,'h')
    assert set(event_counts.values())=={5}
    # Effect script branches: frame, growth, shrink, jump and removal.
    effects={}
    for name,words,size,want_size,want_index in (
        ('frame',(7,),64,64,1),('grow',(0x401,),64,65,1),
        ('grow_fraction',(0x401,),63,63,1),('shrink',(0x801,),64,63,1),
        ('jump',(0x9002,0,7),64,64,3),('remove',(0xa000,),64,64,0)):
        cpu.reset();cpu.data_value(0x97f6,'h',0)
        cpu.data_value(0x53be,'I',0x180000);cpu.data_value(0x53c8,'h',1)
        cpu.write(0x180000,struct.pack('>'+'H'*len(words),*words))
        cpu.data_value(0xc076,'h',1);cpu.data_value(0xc0f6,'h',0);cpu.data_value(0xb3ca,'H',size)
        cpu.run(0x28f96,struct.pack('>h',0))
        assert cpu.data_value(0xb3ca,'H')==want_size
        assert cpu.data_value(0xc0f6,'h')==want_index
        if name=='remove':assert cpu.data_value(0xa45c,'H')==0x8001
        if name in ('frame','jump'):assert cpu.data_value(0xadec,'H')==7
        effects[name]=dict(size=want_size,index=want_index)
    # Word overflow and a literal sentinel: neither can be safely scaled blindly.
    cpu.reset();cpu.data_value(0xc272,'H',32767)
    cpu.run(0x126f0,end=0x126fe,registers={11:0})
    assert cpu.data_value(0xc272,'h')==-32768
    cpu.data_value(0x94c6,'h',-1);cpu.run(0x76a8,struct.pack('>h',0))
    assert cpu.data_value(0x94c6,'h')==-1
    cpu.data_value(0xc272,'h',100);cpu.data_value(0xc288,'B',5)
    cpu.run(0x11620,struct.pack('>hh',0,13))
    assert cpu.data_value(0xc272,'h')==0 and cpu.data_value(0xc288,'B')==0
    assert cpu.data_value(0xbaf2,'h')==13
    # A deadline test depends on VBL elapsed time, not world iteration count.
    cpu.data_value(0x7f02,'I',50)
    cpu.run(0xe82,end=0xe88,registers={11:60})
    assert cpu.reg(9)==10
    # Instrument limitation: report, never treat the high-bit memory-shift
    # discrepancy as a game defect. Positive-size timing checks above are valid.
    cpu.data_value(0xb3ca,'H',0x8000)
    for _ in range(10):cpu.run(0x7904,end=0x7910,registers={11:0})
    shift_probe=dict(logical_expected=32,observed=cpu.data_value(0xb3ca,'H'))
    results['boundaries']=dict(input_edges=edge_counts,event_counts=event_counts,
                               effect_opcodes=effects,action_reset=True,vbl_deadline_remaining=10,high_bit_shift_probe=shift_probe,word_wrap=-32768,life_sentinel=-1)
    return results


def dispatch_check(cpu,memory,layout):
    from timing_inventory import inventory
    graph,_=inventory(memory,layout,[0x2a8]);count=0;guards=0
    assert not graph['unresolved'],graph['unresolved']
    assert set(graph['external'])=={'S:016fc','S:0176a'}
    for table in graph['tables']:
        at=int(table['at'].split(':')[1],16)
        for index,dest in enumerate(table['entries']):
            if not dest.startswith('E:'):raise ValueError('unexpected cross-hunk switch')
            target=int(dest.split(':')[1],16)
            if at==0x13d60:
                cpu.data_value(0xbaf2,'h',index)
                cpu.run(0x13d46,end=target,registers={11:0})
            elif at==0x2fdde:cpu.run(0x2fdda,end=target,registers={9:2*index})
            else:cpu.run(at-4,end=target,registers={9:2*index})
            count+=1
        if at not in (0x13d60,0x2fdde):
            cmp_at=next(at-n for n in (12,14) if cpu.read(cpu.code+at-n,2)==bytes.fromhex('0c40'))
            branch=cmp_at+4;raw=cpu.read(cpu.code+branch,4)
            disp=struct.unpack('>b',raw[1:2])[0] if raw[1] else struct.unpack('>h',raw[2:4])[0]
            for invalid in (len(table['entries']),65535):
                cpu.run(cmp_at,end=branch+2+disp,registers={9:invalid});guards+=1
    assert (len(graph['tables']),count,guards)==(54,625,104)
    return dict(tables=len(graph['tables']),entries=count,bounds_rejections=guards)


def negative_controls(cpu,memory,layout):
    from timing_inventory import inventory
    # Corrupt one switch signature in a private memory copy, never on disk.
    bad=bytearray(memory);bad[cpu.code-BASE+0x7b2f]=0x41
    graph,_=inventory(bad,layout,[0x2a8])
    assert any(x['at']=='E:07b3a' for x in graph['unresolved'])
    # Turn a lifetime decrement into an increment in the private Unicorn image.
    at=cpu.code+0x76ce;original=cpu.read(at,2)
    try:
        cpu.write(at,bytes((0x52,original[1])))
        cpu.reset();cpu.data_value(0x94c6,'h',100)
        cpu.run(0x76a8,struct.pack('>h',0))
        assert cpu.data_value(0x94c6,'h')==101
        assert cpu.data_value(0x94c6,'h')!=99,'defect oracle accepted mutant'
    finally:cpu.write(at,original)
    return dict(broken_dispatch_rejected=True,lifetime_mutant_rejected=True)


def main():
    if not __debug__:raise ValueError('run without Python -O: assertions are the test oracle')
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run');p.add_argument('--output',required=True);a=p.parse_args()
    out=(ROOT/a.output).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('fresh tmp output required')
    memory=(ROOT/a.run/'start-fast.bin').read_bytes();layout=locate(memory);results={}
    for model,name in [(0,'68000'),(4,'68040')]:
        c=CPU(memory,layout,model)
        try:
            results[name]=check(c)
            results[name]['extended']=extended_check(c)
            results[name]['dispatch']=dispatch_check(c,memory,layout)
            results[name]['negative_controls']=negative_controls(c,memory,layout)
        finally:c.close()
    assert results['68000']==results['68040'],'CPU models disagree'
    out.mkdir(parents=True);report=dict(dump_sha256=hashlib.sha256(memory).hexdigest(),unicorn_library_sha256=hashlib.sha256(UNICORN_LIBRARY.read_bytes()).hexdigest(),cpu_models=results,pass_=True)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
