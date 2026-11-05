"""Road Rash A-series checks. Race-field scheduling; no boot-field input timings."""
import hashlib,json,os,re,struct,time,tempfile
from pathlib import Path
from drive import Session,rd,ROOT

def read_bytes(s,start,size):
    with tempfile.TemporaryDirectory(prefix='rr-read-',dir=ROOT/'tmp') as tmp:
        p=Path(tmp)/'read.bin'
        reply=s.cmd(f'dump binary memory {p} {start:#x} {start+size:#x}')
        if not p.exists():raise RuntimeError(f'memory dump failed: {reply}')
        data=p.read_bytes()
    if len(data)!=size:raise RuntimeError('short memory read')
    return data

def field(s):return rd(s,0xa5d4c)

def advance(s,target):
    current=field(s)
    if target<current:raise ValueError(f'passed race field {target}: {current}')
    while current<target:
        gap=target-current
        if gap==1:
            raise ValueError('single-field advance unavailable; schedule checkpoints at least two fields apart')
        s.cmd(f'monitor fields {min(gap,6000)-1}',timeout=120)
        new=field(s)
        if new<=current or new>target:raise RuntimeError(f'race clock did not advance correctly: {current} -> {new}, target {target}')
        current=new

def route(s):
    for attempt in range(500):
        if os.environ.get('RR_PAD'):s.input('JOY2_CD32_PLAY',0)
        # Some 030/MMU boots stop before the Chip mapping is established. An
        # unreadable hook at that startup stage is not a game exception.
        try:hook=rd(s,0xa5916)
        except (ValueError,IndexError):hook=0
        if hook==0x87040:break
        s.input('JOY2_FIRE_BUTTON',1)
        s.cmd('monitor fields 4',timeout=120)
        s.input('JOY2_FIRE_BUTTON',0)
        s.cmd('monitor fields 14',timeout=120)
    else:
        s.shot('route-failure.png')
        raise RuntimeError('race not reached within 10000 boot fields; see route-failure.png')
    current=field(s)
    if current==99:raise RuntimeError('route reached race too late for exact settle checkpoint')
    advance(s,100)
    return snapshot(s)

def stats_address(s):
    if rd(s,0x871dc,2)!=0x4eb9:raise RuntimeError('VERIFY frame hook missing')
    target=rd(s,0x871de)
    data=read_bytes(s,target,1024)
    offset=data.find(b'RRA1STAT')
    if offset<0:raise RuntimeError('VERIFY marker missing')
    address=target+offset
    raw=read_bytes(s,address,320)
    if struct.unpack_from('>II',raw,32)!=(1,320):raise RuntimeError('unsupported VERIFY ABI')
    return address

def counters(s,address):
    b=read_bytes(s,address,320)
    u=lambda off:struct.unpack_from('>I',b,off)[0]
    return dict(start_cacr=u(8),race_cacr=u(12),field=u(16),frames=u(24),
                dma_start=struct.unpack_from('>H',b,20)[0],dma_frame=struct.unpack_from('>H',b,22)[0],
                hash_field=u(52),state_hash=u(56),mmu_tc=u(40),attn_flags=u(44),flags=u(60),histogram=list(struct.unpack_from('>64I',b,64)))

def snapshot(s):
    # All 35 128-byte records, including player, racers and traffic; raw state is
    # compared exactly only for repeated identical configurations, not across CPUs.
    actors=read_bytes(s,0xa5d60,0x1180)
    clock=read_bytes(s,0xa5d4c,20)
    ranks=read_bytes(s,0xa7220,8)+read_bytes(s,0xa59f4,2)
    pointers=struct.unpack('>36I',read_bytes(s,0x909cc,144))
    active=[]
    for p in pointers:
        if p==0xffffffff:break
        if not 0xa5d60<=p<0xa6ee0:raise RuntimeError(f'invalid actor pointer {p:x}')
        active.append(p)
    # Stored positions of inactive riders are stale: this legacy order is NOT
    # native race order. Preserve it only for old capture compatibility.
    racers=[]
    for p in [0xa5d60]+list(range(0xa5e60,0xa6560,0x80)):
        off=p-0xa5d60
        racers.append(dict(address=hex(p),position=struct.unpack_from('>I',actors,off+4)[0],rider=actors[off+0x71]))
    def inactive(address):
        raw=read_bytes(s,address,66)
        count=struct.unpack_from('>H',raw)[0]
        if count>16:raise RuntimeError('invalid inactive rider count')
        return list(struct.unpack_from('>'+str(count)+'I',raw,2))
    ahead,behind=inactive(0x90946),inactive(0x90988)
    race_addresses={int(a['address'],16) for a in racers}
    partition=[p for p in ahead+behind+active if p!=0xa5de0]
    if len(partition)!=15 or set(partition)!=race_addresses:
        raise RuntimeError('native rider lists do not partition all 15 racers')
    positions={int(a['address'],16):a['position'] for a in racers}
    player_position=positions[0xa5d60]
    reconstructed=1+sum(p!=0xa5de0 for p in ahead)
    reconstructed+=sum(p!=0xa5de0 and positions[p]>player_position for p in active[1:])
    packed=struct.unpack('>H',ranks[-2:])[0]
    # A field stop can interrupt between movement and rank publication. Equality
    # is authoritative only immediately after $89366's rank store.
    ranking=dict(ahead=[hex(p) for p in ahead],behind=[hex(p) for p in behind],
                 reconstructed=reconstructed,displayed=10*(packed>>4)+(packed&15),
                 observation='field boundary; may be mid-simulation')
    return dict(field=struct.unpack_from('>I',clock)[0],position=struct.unpack_from('>I',actors,4)[0],
                native_ranking=ranking,rank_displayed=ranking['displayed'],
                rank=struct.unpack('>H',ranks[-2:])[0],
                order=[x['address'] for x in sorted(racers,key=lambda x:(-x['position'],x['address']))],
                actors=racers,active_actors=[hex(p) for p in active],player_flags=actors[0x68:0x6a].hex(),
                lateral=struct.unpack_from('>h',actors,0)[0],speed=struct.unpack_from('>H',actors,0x12)[0],
                crash_state=struct.unpack_from('>b',actors,0x6e)[0],
                state_sha256=hashlib.sha256(actors+clock+ranks).hexdigest())

def provenance(slave,s=None):
    def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    actual={}
    if s:
        for line in (s.run/'fsuae/Cache/Logs/debug.uae').read_text().splitlines():
            if '=' in line:
                k,v=line.split('=',1)
                if k in ('cpu_model','cpu_frequency','cpu_cycle_exact','cpu_data_cache','cpu_memory_cycle_exact','mmu_model','chipmem_size','fastmem_size','bogomem_size','uaeboard'):actual[k]=v
        tested=s.run/'dh1/RoadRash.slave'
        (s.out/'tested.slave').write_bytes(tested.read_bytes())
    else:tested=slave
    return dict(slave=str(slave),slave_sha256=sha(tested),emulator_sha256=sha(os.environ.get('FSUAE',ROOT/'tmp/emulator/fs-uae')),
                effective_configuration=actual,deterministic=True,
                configuration={k:v for k,v in os.environ.items() if k in ('AMIGA_SETUP','CPU','CHIP_KB','FAST_KB','SLOW_KB','EXTRA_ARGS','WHD_ARGS')})

def b_counters(s):
    target=rd(s,0x875be)
    data=read_bytes(s,target,1024);offset=data.find(b'RRBSTAT1')
    if offset<0:raise RuntimeError('missing B diagnostic marker')
    data=read_bytes(s,target+offset,96)
    return dict(gates=struct.unpack_from('>I',data,8)[0],closed=struct.unpack_from('>I',data,12)[0],drains=struct.unpack_from('>I',data,16)[0],max_drain=struct.unpack_from('>I',data,20)[0],deltas=list(struct.unpack_from('>16I',data,32)))
