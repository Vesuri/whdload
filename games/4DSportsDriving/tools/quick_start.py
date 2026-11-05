#!/usr/bin/env python3
"""Boot a VERIFY keyboard route and stop at a numbered live-driving frame.

Usage: python3 tools/quick_start.py tmp/prof/run1 --frame 10 [--resume]
The default machine is 68000 / 1 MB chip / 2 MB fast. This first harness
supports fast RAM and A500 chip/slow-memory configurations.
"""
import argparse, hashlib, json, os, socket, struct, subprocess, sys, time, shlex, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
RUN = ROOT / 'tmp/run' / (os.environ.get('INSTANCE') or 'default') / '.run'
SOCK = RUN / 'driving.sock'
# macOS limits a socket path to 104 bytes: a deep checkout connects by the relative path.
if len(str(SOCK)) > 100: SOCK = Path(os.path.relpath(SOCK))

def command(text, timeout=180):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(timeout)
        s.connect(str(SOCK)); s.sendall(text.encode()); result = b''
        while chunk := s.recv(65536): result += chunk
    answer = result.decode()
    if answer.startswith('ERROR'): raise RuntimeError(answer)
    return answer

def stop_old():
    if SOCK.exists():
        try: command('quit', 3)
        except (OSError, RuntimeError): pass
        SOCK.unlink(missing_ok=True)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('output', type=Path)
parser.add_argument('--frame', type=int, default=10)
parser.add_argument('--tick', type=int, help='Stop before native simulation tick N instead of a rendered frame')
parser.add_argument('--detail', type=int, choices=range(5), default=0, help='Expected VERIFY graphics level (default FULL)')
parser.add_argument('--simulation', type=int, choices=(10,20,50), default=10, help='Expected active simulation mode')
parser.add_argument('--opponent',type=int,choices=range(7),default=0,help='Expected native opponent identity; 0 is solo')
parser.add_argument('--min-modal-resumes',type=int,default=0,help='Require completed live modal pauses')
parser.add_argument('--min-history-resets',type=int,default=0,help='Require this many native history resets before the checkpoint')
parser.add_argument('--resume', action='store_true')
parser.add_argument('--screenshot', action='store_true', help='Save a cockpit image; advances one PAL field beyond the anchor')
parser.add_argument('--early-tick', action='store_true', help='Break directly at the requested physics tick before waiting for a configured render')
a = parser.parse_args()
assert not a.early_tick or a.tick is not None
assert a.frame >= 1
assert a.tick is None or 0 <= a.tick < 30000
out = a.output.resolve()
assert out.is_relative_to(ROOT / 'tmp'), 'Outputs must stay under harness tmp/'
out.mkdir(parents=True, exist_ok=False)
slave = Path(os.environ.get('SLAVE') or ROOT / 'tmp/build/4DSportsDriving-verify.slave').resolve()
assert b'4DTAPE!!' in slave.read_bytes(), 'Build with VERIFY=1 first'
subprocess.run([sys.executable,'tools/check_inputs.py'], check=True)
(out / 'slave.slave').write_bytes(slave.read_bytes())
listing=slave.with_suffix('.lst')
build=slave
if listing.exists() and build.read_bytes()==slave.read_bytes():
    (out/'slave.lst').write_bytes(listing.read_bytes())
env = dict(os.environ, SLAVE=str(out/'slave.slave'), WARP=os.environ.get('WARP','1'), DETERMINISTIC='1', JOY0='none', JOY0_MODE='nothing')
for name in ('BOOT_BREAK','BOOT_CONDITION','BOOT_IGNORE'): env.pop(name, None)
fast = int(env.get('BENCH_MEMORY_KB',env.get('FAST_KB','2048')))
if fast:
    base = int(env.get('BENCH_MEMORY_BASE','0x200000'),0)
    end = base + fast * 1024
else:
    slow=512
    for arg in shlex.split(env.get('EXTRA_ARGS','')):
        if arg.startswith('--slow_memory='): slow=int(arg.split('=',1)[1])
    assert slow>0, 'A500 profile requires expansion slow memory'
    raw=slave.read_bytes();header=raw.index(b'WHDLOADS')-4
    required=struct.unpack_from('>I',raw,header+32)[0]
    assert slow*1024>=required, f'Slave requires {required//1024} KB expansion memory; configured {slow} KB'
    base,end=0,0xc00000+slow*1024
settings = {k:env.get(k) for k in ('CPU','AMIGA_MODEL','KICKSTART','CHIP_KB','FAST_KB','EXTRA_ARGS','WHD_ARGS','GAME','WHDLOAD_BINARY')}
if env.get('FSUAE'):
    settings['FSUAE']=env['FSUAE']
    settings['FSUAE_SHA256']=hashlib.sha256(Path(env['FSUAE']).read_bytes()).hexdigest()
    settings['FSUAE_NATIVE_PROFILE_SHA256']=env.get('FSUAE_NATIVE_PROFILE_SHA256')
key = hashlib.sha256(slave.read_bytes()+json.dumps(settings,sort_keys=True).encode()).hexdigest()
cache = ROOT/'tmp/cache'/('driving-'+key+'.json'); cache.parent.mkdir(exist_ok=True)
start = time.monotonic()
server = None

def boot(bootenv, label):
    global server
    stop_old()
    log = out/(label+'.log')
    with log.open('w') as f:
        server = subprocess.Popen([sys.executable,'tools/driving.py','serve'],env=bootenv,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    next_report = time.monotonic()+60
    while True:
        if SOCK.exists() and 'serving on' in log.read_text(): return
        if server.poll() is not None: raise RuntimeError(log.read_text())
        if time.monotonic() >= next_report:
            print(f'{label}: test server PID {server.pid} is still running; waiting for the driving checkpoint',flush=True)
            next_report = time.monotonic()+60
        time.sleep(.2)

def dump(name):
    target = out/name
    if fast:
        for stop_attempt in range(5):
            answer = command(f'gdb dump binary memory {target.relative_to(ROOT)} {base:#x} {end:#x}')
            if target.exists(): break
            if 'target is running' not in answer: raise RuntimeError(answer)
            command('stop')
            time.sleep(.2)
        if not target.exists(): raise RuntimeError(answer)
    else:
        combined=bytearray(end)
        for bank,lo,hi in [('chip',0,int(env.get('CHIP_KB','1024'))*1024),('slow',0xc00000,end)]:
            part=out/(name+'.'+bank)
            answer=command(f'gdb dump binary memory {part.relative_to(ROOT)} {lo:#x} {hi:#x}')
            assert part.exists(),answer
            blob=part.read_bytes();assert len(blob)==hi-lo
            combined[lo:hi]=blob;part.unlink()
        target.write_bytes(combined)
    return target.read_bytes()

def marker(mem):
    check=0
    while (check:=mem.find(b'4DPERF!!',check))>=0:
        game,failure=struct.unpack_from('>I',mem,check+8)[0],struct.unpack_from('>I',mem,check+16)[0]
        if base<=game<end and game and failure:
            raise RuntimeError(f'VERIFY failure {failure}; inspect saved calibration memory')
        check+=8
    found = []
    at = 0
    while (at := mem.find(b'4DTAPE!!',at)) >= 0:
        values = struct.unpack_from('>6I',mem,at+8)
        game = values[0]
        if base <= game < end-0x3a04c and mem[game-base:game-base+2] == b'\x4e\xf9':
            found.append((base+at,values))
        at += 1
    assert len(found)==1, f'Expected one live marker, found {len(found)}'
    return found[0]

try:
    if cache.exists(): game = json.loads(cache.read_text())['game']; ready = json.loads(cache.read_text())['marker']+32
    else:
        boot(env, 'calibration')
        for attempt in range(60):
            command('wait 0.5'); command('stop')
            mem = dump('calibration-memory.bin')
            try: mark,values = marker(mem); game=values[0]; ready=mark+32; break
            except AssertionError: command('cont')
        else: raise RuntimeError('Live slave/game marker not found')
        cache.write_text(json.dumps({'game':game,'marker':ready-32}))
        stop_old()
        (out/'calibration-memory.bin').unlink()
    anchor_offset = 0xe5f8 if a.tick is not None else 0x7500
    tick_condition = f' && *(unsigned short *)($a4-0x940)=={a.tick}' if a.tick is not None else ''
    if a.min_history_resets or a.min_modal_resumes:
        symbols={name:int(value,16) for name,value in re.findall(r'^([\w.]+)\s+00:([0-9A-Fa-f]+)\s*$',(out/'slave.lst').read_text(encoding='latin1'),re.M)}
        slave_base=ready-32+8-symbols['tape_game']
        if a.min_history_resets:
            reset_address=slave_base+symbols['sim_schedule_resets']
            tick_condition+=f' && *(unsigned int *){reset_address:#x}>={a.min_history_resets}'
        if a.min_modal_resumes:
            modal_address=slave_base+symbols['sim_schedule_modal_resumes']
            tick_condition+=f' && *(unsigned int *){modal_address:#x}>={a.min_modal_resumes}'
    targetenv = dict(env, BOOT_BREAK=hex(game+(0x7500 if a.tick is not None and not a.early_tick else anchor_offset)),
        BOOT_CONDITION=f'*(unsigned char *)($a4+0x45)==0 && *(unsigned char *)($a4-0x16d8)==0 && *(unsigned int *){ready:#x}==1 && *(unsigned short *)($a4-0x15fa)=={a.simulation}'+(tick_condition if a.tick is None or a.early_tick else ''),
        BOOT_IGNORE=str(a.frame-1 if a.tick is None else 0))
    # Do not ask remote GDB to reject every pre-configuration frame. Stop at
    # the tape's publication first, then count the same live frame anchors.
    listing_text=(out/'slave.lst').read_text(encoding='latin1')
    published=re.search(r'lea tape_configured\(pc\),a0\n00:([0-9A-Fa-f]+)[^\n]*move.l #1,\(a0\)',listing_text)
    if published and a.tick is None:
        symbols={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)\s*$',listing_text,re.M)}
        slave_base=ready-32+8-symbols['tape_game']
        configured_pc=slave_base+int(published[1],16)+6
        boot(dict(env,BOOT_BREAK=hex(configured_pc)),'serve')
        answer=command('gdb delete\nbreak *'+hex(game+anchor_offset)+'\ncondition $bpnum '+targetenv['BOOT_CONDITION']+'\nignore $bpnum '+targetenv['BOOT_IGNORE']+'\ncontinue\ndelete')
        (out/'frame-anchor.log').write_text(answer)
    else:
        boot(targetenv,'serve')
    if a.tick is not None and not a.early_tick:
        # Avoid trapping the tight pre-start physics loop throughout the menu
        # route. A configured render boundary comes first, then the exact tick.
        initial = command('gdb p /u *(unsigned short *)($a4-0x940)')
        current = int(re.search(r'\$\d+ = (\d+)',initial)[1])
        assert current <= a.tick, ('Tick passed before configured render boundary',current,a.tick)
        condition = targetenv['BOOT_CONDITION']+tick_condition
        command(f'gdb delete\ntbreak *{game+anchor_offset:#x} if {condition}\ncontinue')
    mem = dump('memory.bin')
    address,values = marker(mem)
    live,fields,frames,a4,first,events=values
    assert live==game and (a.tick is not None or frames==a.frame), (values,a.frame)
    # Follow the live LoadSeg BPTR chain, not WHDLoad's cached original executable.
    data = struct.unpack_from('>I',mem,game-base-4)[0]*4+4
    assert a4-data==0x7ffe
    state = mem[data-base:data-base+0xa77c]
    assert state[0x7ffe-0x7708] == a.detail, ('Requested graphics level was not selected',a.detail,state[0x7ffe-0x7708])
    assert struct.unpack_from('>H',state,0x7ffe-188)[0] == a.simulation, 'Selected simulation does not match requested mode'
    assert struct.unpack_from('>H',state,0x7ffe-0x15fa)[0] == a.simulation, 'Active simulation does not match requested mode'
    assert state[0x7ffe-0x173a] == a.simulation, 'Race simulation byte does not match requested mode'
    assert state[0x7ffe-0x174a] == a.opponent, ('Opponent selection mismatch',state[0x7ffe-0x174a],a.opponent)
    if a.tick is not None:
        assert struct.unpack_from('>H',state,0x7ffe-0x940)[0] == a.tick
    (out/'state.bin').write_bytes(state)
    registers = command('gdb info registers')
    (out/'registers.txt').write_text(registers)
    stopped_pc = int(re.search(r'^pc\s+0x([0-9a-f]+)',registers,re.M)[1],16)
    assert stopped_pc == game+anchor_offset, ('Not at requested checkpoint',hex(stopped_pc),hex(game+anchor_offset))
    result={'game_base':game,'data_base':data,'marker':address,'frame':frames,'memory_base':base,'memory_size':end-base,
            'first_driving_field':first,'tape_fields':fields,'input_events':events,
            'wall_seconds_including_calibration':round(time.monotonic()-start,2),
            'slave_sha256':hashlib.sha256((out/'slave.slave').read_bytes()).hexdigest(),'settings':settings,
            'anchor_code_offset':hex(anchor_offset),'simulation_tick':a.tick,'a4_bias':'0x7ffe',
            'screenshot_advances_one_field':a.screenshot,'graphics':'FULL' if a.detail==0 else f'level {a.detail}','graphics_level':a.detail,'simulation':{10:'Normal',20:'A2500',50:'A4000 development prototype'}[a.simulation],'opponent':a.opponent,'active_simulation_word':struct.unpack_from('>H',state,0x7ffe-0x15fa)[0],'race_simulation_byte':state[0x7ffe-0x173a]}
    symbols={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)\s*$',(out/'slave.lst').read_text(encoding='latin1'),re.M)}
    perf=next(i for i in range(len(mem)) if mem.startswith(b'4DPERF!!',i) and struct.unpack_from('>I',mem,i+8)[0]==game)
    actual_slave_base=base+perf+8-symbols['perf_game']
    result['slave_base']=actual_slave_base
    result['clock_symbols']={n:actual_slave_base+symbols[n] for n in ('sim_clock_fields','sim_time_field_hz','sim_schedule_read','sim_schedule_write','sim_schedule_overflow','sim_schedule_ticks','sim_schedule_active','perf_failure') if n in symbols}
    if a.min_history_resets:
        result['history_resets']=struct.unpack_from('>I',mem,reset_address-base)[0]
        assert result['history_resets']>=a.min_history_resets
    if a.min_modal_resumes:
        result['modal_resumes']=struct.unpack_from('>I',mem,modal_address-base)[0]
        assert result['modal_resumes']>=a.min_modal_resumes
    (out/'anchor.json').write_text(json.dumps(result,indent=2)+'\n')
    if a.screenshot: command('shot '+str(out/'cockpit.png'))
    print(json.dumps(result,indent=2))
    print('Live driving reached; emulator '+('running' if a.resume else 'paused for profiling')+'.')
    if a.resume: command('cont')
except TimeoutError:
    # A socket observation timeout is not evidence that the guest or server
    # stopped. Keep the owned process and socket for explicit inspection.
    if server is not None and server.poll() is None:
        print(f'Observation timed out; preserving live test server PID {server.pid} and {SOCK}',flush=True)
    raise
except BaseException:
    stop_old()
    if server is not None and server.poll() is None: server.terminate()
    subprocess.run([str(ROOT/'../../common/run.sh'),'stop'],cwd=ROOT,check=False)
    raise
