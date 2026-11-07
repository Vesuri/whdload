#!/usr/bin/env python3
"""Capture a fixed SOL gameplay window with the VERIFY/CUSTOM5 menu fixture.
Usage: tools/fixed_window.py tmp/prof/base [--fields 100] [--frame 90] [--swaps-only]
The machine is SETUP (an AmigaXDev named setup, default game.conf's); explicit CPU,
CHIP_KB, FAST_KB, SLOW_KB, AMIGA_MODEL and KICKSTART without SETUP select SETUP=custom.
"""
import argparse, os, socket, subprocess, sys, time, struct, json, re
from pathlib import Path
from stellar7 import SOCK
import machines
from stellar7_report import loaded_game_regions

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('out',type=Path)
p.add_argument('--fields',type=int,default=100)
p.add_argument('--frame',type=int,default=90)
p.add_argument('--level',type=int,choices=range(7),help='wait for this level before matching the requested boundary')
p.add_argument('--tick',type=int,help='capture a completed SIM60 tick instead of a legacy frame')
p.add_argument('--session',type=int,help='match this SIM60 session as well as the tick, e.g. after Continue or a level exit')
p.add_argument('--tick-checkpoints',type=int,nargs='*',default=[],help='additional completed SIM60 tick boundaries')
p.add_argument('--checkpoints',type=int,nargs='*',default=[],help='additional simulation frames to snapshot after the trace')
p.add_argument('--swaps-only',action='store_true')
p.add_argument('--state-only',action='store_true')
p.add_argument('--native-events',action='store_true',help='record every native presentation boundary between --frame and --checkpoints; requires --state-only')
p.add_argument('--prebuilt', type=Path, help='capture this retained VERIFY slave instead of rebuilding; caller supplies matching flags/listing')
p.add_argument('--boot-timeout', type=float, default=1800, help='seconds allowed for this boot to expose the loaded game')
p.add_argument('--boundary-timeout', type=float, default=900, help='seconds allowed to reach the requested boundary after boot; above 540 s (tick boundaries) the wait resumes every 3000 fields')
p.add_argument('--latency-listing', type=Path, help='exact VERIFY listing; observe update starts over --fields even with --state-only')
p.add_argument('--presentation-listing', type=Path, help='exact retained SIM60 listing/binary; read-only rendering phase observer')
p.add_argument('--stop-on-inactive', action='store_true', help='stop checkpoints at the first completed tick with inactive gameplay, before death/exit resets')
p.add_argument('--raw-trace', action='store_true', help='retain Barto display/DMA trace without requiring CPU instruction records')
p.add_argument('--shot-windows', type=int, default=0, help='after the boundary, trace this many consecutive --fields windows and keep only each field\'s screenshot, displayed bitplanes and audio DMA/register writes (shots/, shots.json; tools/paula_audio.py)')
p.add_argument('--motion-ticks', type=int, default=0, help='after the tick boundary, record every active actor at each completed tick (before the world recenter) and the tick of each presentation, for this many ticks (motion.txt; tools/motion_check.py)')
p.add_argument('--retain-command', action='store_true', default='--warp_mode=0' in os.environ.get('EXTRA_ARGS','').split(), help='retain the running project emulator command for frontend-option verification (automatic for explicit --warp_mode=0)')
a=p.parse_args()
if a.session is not None and (a.tick is None or a.session < 1):
    p.error('--session requires --tick and a positive session number')
if a.raw_trace and (a.state_only or a.swaps_only or a.latency_listing or a.presentation_listing or a.native_events):
    p.error('--raw-trace cannot be combined with another observer or --state-only')
if a.stop_on_inactive and (a.tick is None or not a.state_only or not a.tick_checkpoints or a.latency_listing or a.presentation_listing):
    p.error('--stop-on-inactive requires --tick, --tick-checkpoints and --state-only without a field observer')
if a.presentation_listing and (a.tick is None or a.latency_listing or a.swaps_only or a.native_events):
    p.error('--presentation-listing requires --tick and no other observer')
if a.shot_windows and (a.raw_trace or a.state_only or a.swaps_only or a.latency_listing or a.presentation_listing or a.native_events or a.tick_checkpoints or a.checkpoints):
    p.error('--shot-windows replaces the trace; use it without another observer or checkpoints')
if a.motion_ticks and (a.tick is None or a.shot_windows or a.raw_trace or a.swaps_only or a.latency_listing or a.presentation_listing or a.native_events or a.tick_checkpoints):
    p.error('--motion-ticks requires --tick and replaces the trace; use it without another observer or checkpoints')
if a.motion_ticks < 0:
    p.error('--motion-ticks must not be negative')
if a.shot_windows < 0:
    p.error('--shot-windows must not be negative')
if a.boot_timeout <= 0:
    p.error('--boot-timeout must be positive')
if not 1 <= a.fields <= 100:
    p.error('--fields must be 1..100 (Barto capture limit); use checkpoints for longer runs')
if a.tick is not None and (a.tick < 1 or a.checkpoints):
    p.error('--tick must be positive; legacy --checkpoints cannot be combined with it')
if a.tick_checkpoints and (a.tick is None or a.tick_checkpoints != sorted(set(a.tick_checkpoints)) or any(x <= a.tick for x in a.tick_checkpoints)):
    p.error('--tick-checkpoints require --tick and unique increasing tick numbers after it')
if a.checkpoints != sorted(set(a.checkpoints)) or any(x <= a.frame for x in a.checkpoints):
    p.error('--checkpoints must be unique increasing simulation steps after --frame')
if a.native_events and (a.tick is not None or not a.state_only or a.swaps_only or a.latency_listing or not a.checkpoints):
    p.error('--native-events requires native --frame/--checkpoints and --state-only, without another field observer')
root=Path(__file__).resolve().parent.parent
# common/run.sh runs each instance in tmp/run/<INSTANCE>/.
RUN=root/'tmp/run'/(os.environ.get('INSTANCE') or 'default')/'.run'
os.chdir(root)
out=a.out.resolve(); out.relative_to(root/'tmp')
assert ' ' not in str(out.relative_to(root)), 'capture subdirectory must not contain spaces (gdb limitation)'
if out.exists() and any(out.iterdir()):
    p.error('capture directory is not empty; choose a new path to preserve previous measurements')
out.mkdir(parents=True,exist_ok=True)
def cmd(text, timeout=900):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(timeout);s.connect(SOCK);s.sendall(text.encode());reply=b''
        while part:=s.recv(65536):reply+=part
    result=reply.decode()
    if 'ERROR' in result:raise RuntimeError(result)
    return result
try:cmd('quit',5)
except (OSError,RuntimeError):pass
if a.prebuilt is None:
    subprocess.run(['make','-s','verify','VARIANT=Stellar7'],check=True)
    selected_slave = Path('tmp/build/verify/Stellar7.Slave')
else:
    selected_slave = a.prebuilt
(out/'slave.slave').write_bytes(selected_slave.read_bytes())
env=dict(os.environ,SLAVE=str(out/'slave.slave'),WHD_ARGS='CUSTOM5=1 '+os.environ.get('WHD_ARGS',''),JOY0='none',JOY1='none',DETERMINISTIC='1',WARP='1')
os.environ['SLAVE']=env['SLAVE']
ntsc_mode = int(env.get('NTSC', '1'))
if ntsc_mode not in (0, 1):
    raise ValueError('NTSC must be 0 or 1')
field_hz = 60 if ntsc_mode else 50
setup = machines.effective(env)
if setup:
    if any(env.get(key) for key in machines.SELECTORS):
        p.error('give either SETUP or explicit machine variables, not both')
    for key in machines.SETTINGS:
        env.pop(key, None)
    machine = machines.resolve(setup, ntsc_mode)
    cpu, chip, fast, slow = machine['cpu'], machine['chip_kb'], machine['fast_kb'], machine['slow_kb']
    setup_args = machine['args']
else:
    cpu = env.get('CPU','68000')
    fast=int(env.get('FAST_KB','0')); chip=int(env.get('CHIP_KB','512'))
    slow_match = re.search(r'--slow_memory=(\d+)', env.get('EXTRA_ARGS', ''))
    slow = int(slow_match[1]) if slow_match else int(env.get('SLOW_KB', '1536'))
    setup_args = []
env['SETUP'] = setup or 'custom'
env.pop('AMIGA_SETUP', None)
base = 0x200000 if fast else 0xc00000 if slow else 0
size = (fast or slow or chip)*1024
log=(out/'serve.log').open('w')
server=subprocess.Popen([sys.executable,'tools/stellar7.py','serve'],stdout=log,stderr=subprocess.STDOUT,env=env)
def dump(destination=out):
    destination.mkdir(parents=True,exist_ok=True)
    code=str((destination/'code.bin').relative_to(root)); cb=str((destination/'chip.bin').relative_to(root))
    cmd(f'gdb dump binary memory {code} {base:#x} {base+size:#x}\ndump binary memory {cb} 0 {chip*1024:#x}')
    return (destination/'code.bin').read_bytes(),(destination/'chip.bin').read_bytes()
try:
    deadline=time.monotonic()+120
    while 'serving on' not in (out/'serve.log').read_text():
        if server.poll() is not None:raise RuntimeError((out/'serve.log').read_text())
        if time.monotonic()>deadline:raise TimeoutError('server startup')
        time.sleep(.2)
    print('Booting to loaded game...',flush=True)
    boot_deadline = time.monotonic()+a.boot_timeout
    while time.monotonic() < boot_deadline:
        cmd('wait 0.1');cmd('stop');mem,ch=dump()
        try:r={n:lo for lo,hi,n,o in loaded_game_regions(mem,base,ch)}
        except ValueError:continue
        if 's7' not in r:
            continue
        if a.tick is not None:
            # LoadSeg exposes the original hunk before the slave finishes its
            # guarded installation/AllocMem. Do not mistake that interval for
            # a failed SIM60 patch; keep observing this same boot.
            hook = mem[r['s7']-base+0x2af6:r['s7']-base+0x2afc]
            if hook[:2] != bytes.fromhex('4ef9'):
                continue
            entry = struct.unpack_from('>I', hook, 2)[0]
            if mem[entry-base+4:entry-base+8] != b'S760':
                continue
        break
    else:raise TimeoutError(f'game/SIM60 patch not ready after {a.boot_timeout:g} seconds in this boot')
    h=r['s7']; data=r['s7-data']; anchor=h+0x2c16
    counter=data+0x1e96; counter_type='unsigned short'; requested=a.frame
    if a.tick is not None:
        entry=struct.unpack_from('>I',mem,h-base+0x2af8)[0]
        assert mem[h-base+0x2af6:h-base+0x2af8] == bytes.fromhex('4ef9'), 'SIM60 entry is not installed'
        assert mem[entry-base+4:entry-base+8] == b'S760', 'SIM60 ABI not found'
        anchor=entry+struct.unpack_from('>H',mem,entry-base+44)[0]
        counter=entry+16; counter_type='unsigned int'; requested=a.tick
    def boundary_count(memory):
        return struct.unpack_from('>I' if a.tick is not None else '>H',memory,counter-base)[0]
    def level_matches(memory):
        return (a.level is None or struct.unpack_from('>H',memory,data-base+0x46a0)[0] == a.level) and (a.session is None or struct.unpack_from('>I',memory,entry-base+100)[0] == a.session)
    level_condition = '' if a.level is None else f' && *(unsigned short*){data+0x46a0:#x} == {a.level}'
    if a.session is not None:
        from sim60_state import decode_version
        assert decode_version(struct.unpack_from('>H',mem,entry-base+50)[0])[0] >= 17
        session=struct.unpack_from('>I',mem,entry-base+100)[0]
        if session>a.session:raise RuntimeError(f'Already passed session {a.session}: {session}')
        level_condition += f' && *(unsigned int*){entry+100:#x} == {a.session}'
    count=boundary_count(mem)
    if level_matches(mem) and count>requested:raise RuntimeError(f'Already passed boundary {requested}: {count}')
    print(f'Waiting for gameplay {"tick" if a.tick is not None else "frame"} {requested}...',flush=True)
    wait=f'gdb break *{anchor:#x}\ncondition $bpnum *({counter_type}*){counter:#x} >= {requested}{level_condition}'
    if a.boundary_timeout <= 540 or a.tick is None:
        reply=cmd(wait+'\ncontinue\ndelete', a.boundary_timeout)
    else:
        # One server gdb command may run 600 s. For longer routes (native level loads,
        # menus) also stop on SIM60's per-field callback every 3000 fields, which runs
        # outside gameplay too, and resume until the boundary is reached.
        listing=(root/'tmp/build/verify/Stellar7.lst').read_text(encoding='latin1')
        symbol=lambda name:int(re.search(r'^'+name+r'\s+00:([0-9A-F]+)',listing,re.M)[1],16)
        watch=entry+symbol('s60_history_field')-symbol('s60_entry')
        field=data+0x24a8
        cmd(wait+f'\nbreak *{watch:#x}\ncondition $bpnum *(unsigned int*){field:#x} >= $limit')
        deadline=time.monotonic()+a.boundary_timeout;reply=''
        while True:
            if time.monotonic()>deadline:raise TimeoutError(f'boundary not reached in {a.boundary_timeout:g} s')
            reply=cmd(f'gdb set $limit = *(unsigned int*){field:#x} + 3000\ncontinue',600)
            pc=re.findall(r'^Breakpoint \d+, (0x[0-9a-f]+)',reply,re.M)
            if pc and int(pc[-1],16)==anchor:break
            if not pc or int(pc[-1],16)!=watch:raise RuntimeError('unexpected stop: '+reply[-500:])
        cmd('gdb delete')
    (out/'boundary-gdb.txt').write_text(reply)
    mem,ch=dump()
    count=boundary_count(mem)
    assert count==requested and level_matches(mem),(count,requested,a.level)
    exec_base=struct.unpack_from('>I',ch,4)[0]
    exec_memory,exec_offset=(ch,exec_base) if exec_base < len(ch) else (mem,exec_base-base)
    observed_hz=exec_memory[exec_offset+530] # ExecBase.VBlankFrequency (NDK)
    if observed_hz not in (50,60):
        raise RuntimeError(f'Unsupported Exec clock frequency: {observed_hz}')
    if observed_hz != field_hz:
        raise RuntimeError(f'Requested {field_hz} Hz display but Exec reports {observed_hz}; verify scan timing before reporting FPS')
    legacy_count=struct.unpack_from('>H',mem,data-base+0x1e96)[0]
    (out/'anchor.txt').write_text(reply+f'\nframe={legacy_count}\ntick={a.tick}\ncode={h:#x}\ndata={data:#x}\nbase={base:#x}\n')
    (out/'metadata.json').write_text(json.dumps(dict(code_base=h,data_base=data,base=base,frame=struct.unpack_from('>H',mem,data-base+0x1e96)[0],tick=a.tick,level_filter=a.level,session_filter=a.session,fields=a.fields,setup=env['SETUP'],setup_args=setup_args,cpu=cpu,chip_kb=chip,fast_kb=fast,slow_kb=slow,extra_args=env.get('EXTRA_ARGS',''),whd_args=env['WHD_ARGS'],verify_flags=env.get('VERIFY_FLAGS',''),ntsc_mode=ntsc_mode,field_hz=field_hz,observed_exec_hz=observed_hz),indent=2)+'\n')
    (out/'state.bin').write_bytes(mem[data-base:data-base+0x823c])
    if a.retain_command:
        pid=int((RUN/'fsuae.pid').read_text().strip())
        actual=subprocess.run(['ps','-ww','-p',str(pid),'-o','command='],capture_output=True,text=True,check=True).stdout.strip()
        assert actual and Path(actual.split()[0]).name.startswith('fs-uae'), 'recorded pid is not the project emulator'
        (out/'emulator-command.txt').write_text(actual+'\n')
    print(f'At {"tick" if a.tick is not None else "frame"} {count}; capturing {a.fields} fields...',flush=True)
    if a.motion_ticks:
        # Read-only breakpoints. At s60_recenter entry this tick's movement and
        # collisions are complete and the player still holds its displacement since
        # the previous recenter, so world positions can be rebuilt across ticks.
        # $6a0a is the native presentation entry: the frame shows the current tick.
        listing=(a.prebuilt.with_suffix('.lst') if a.prebuilt else root/'tmp/build/verify/Stellar7.lst').read_text(encoding='latin1')
        symbol=lambda name:int(re.search(r'^'+name+r'\s+00:([0-9A-F]+)',listing,re.M)[1],16)
        recenter=entry+symbol('s60_recenter')-symbol('s60_entry')
        actor=('printf "A %x %d %d %d %d %d %d %d %d %d %d %d %d %u %d %x\\n", $o, *(short*)($o+2), '
               '*(int*)($o+8), *(int*)($o+12), *(int*)($o+16), *(short*)($o+20), *(short*)($o+22), *(short*)($o+24), '
               '*(short*)($o+64), *(short*)($o+52), *(short*)($o+54), *(short*)($o+56), '
               '*(signed char*)($o+0x55), *(unsigned char*)($o+0x54), *(int*)($o+4), *(unsigned int*)($o+106)')
        cmd(f'''gdb break *{recenter:#x}
commands
silent
set $p = *(unsigned int*){data+0x43c0:#x}
printf "T %u %u %d %u %x %d %d\\n", *(unsigned int*){counter:#x}, *(unsigned int*){entry+100:#x}, *(short*){data+0x46a0:#x}, *(unsigned int*){data+0x24a8:#x}, $p, *(int*)($p+8), *(int*)($p+12)
set $o = $p
{actor.replace('"A ', '"P ', 1)}
set $i = 0
while $i < *(short*){data+0x43b2:#x} && $i < 256
set $o = *(unsigned int*)({data+0x3fb2:#x}+4*$i)
{actor}
set $i = $i + 1
end
continue
end
break *{h+0x6a0a:#x}
commands
silent
printf "R %u %u\\n", *(unsigned int*){counter:#x}, *(unsigned int*){data+0x24a8:#x}
continue
end
break *{anchor:#x}
condition $bpnum *(unsigned int*){counter:#x} >= $motion_end''')
        lines=[f'# motion trace: field_hz={field_hz} substeps from VERIFY_FLAGS; T tick session level field player px pz; P/A ptr type x z y pitch bank yaw speed vpitch vbank vyaw health flags radius owner (P is the player); R tick field at each presentation']
        done=requested
        while done < requested+a.motion_ticks:
            target=min(done+300, requested+a.motion_ticks)
            reply=cmd(f'gdb set $motion_end = {target}\ncontinue', 600)
            lines+=[x for x in reply.splitlines() if x[:2] in ('T ', 'P ', 'A ', 'R ')]
            pc=re.findall(r'^Breakpoint \d+, (0x[0-9a-f]+)',reply,re.M)
            if not pc or int(pc[-1],16)!=anchor:raise RuntimeError('unexpected stop: '+reply[-500:])
            done=target
        cmd('gdb delete')
        (out/'motion.txt').write_text('\n'.join(lines)+'\n')
    elif a.shot_windows:
        from amigaxdev import barto
        shots=out/'shots';shots.mkdir();summary=[]
        for window in range(a.shot_windows):
            cmd(f'profile {a.fields} {out}/window.bin')
            t=barto.load(out/'window.bin')
            if len(t.fields) != a.fields:raise RuntimeError(f'Requested {a.fields} fields, captured {len(t.fields)}')
            for field in t.fields:
                index=len(summary)
                (shots/f'{index:05d}.png').write_bytes(field.shot)
                # Lowest fetched address per bitplane register: the displayed bitmap.
                # Audio: Paula DMA fetches (type 4) and CPU writes to the audio registers.
                # CPU (type 2) and blitter (type 5) accesses are kept by address for the displayed check.
                planes={};fetches=[];writes=[];access=[]
                for at in range(0,len(field.dma),field.dma_size):
                    kind=struct.unpack_from('<h',field.dma,at+29)[0]
                    if kind not in (2,4,5,6):continue
                    reg,value,_,address=struct.unpack_from('<HQHI',field.dma,at)
                    slot=at//field.dma_size
                    if kind in (2,5) and address<0x200000:access.append((slot,kind,reg,address))
                    if kind==6:planes[reg]=min(planes.get(reg,address),address)
                    elif kind==4:fetches.append([slot,(reg-0xaa)//16,value&0xffff,address])
                    elif reg==0x1102 and 0xdff096<=address<0xdff0e0:writes.append([slot,address&0x1fe,value&0xffff])
                # Accesses inside the bitmap this field displays: count and first beam slot per (type, reg).
                shown=[(v,v+8000) for v in planes.values()];hits={}
                for slot,kind,reg,address in access:
                    if any(lo<=address<hi for lo,hi in shown):
                        key=f'{kind}:{reg:#x}';n,first=hits.get(key,(0,slot));hits[key]=(n+1,first)
                summary.append(dict(field=index,window=window,slots=len(field.dma)//field.dma_size,displayed_access=hits,
                                    planes={f'{k:#x}':v for k,v in sorted(planes.items())},audio_fetches=fetches,audio_writes=writes))
            (out/'window.bin').unlink()
        (out/'shots.json').write_text(json.dumps(dict(fields=summary))+'\n')
    elif a.presentation_listing:
        subprocess.run([sys.executable,'tools/presentation_fields.py',str(a.out),'--listing',str(a.presentation_listing),'--fields',str(a.fields)],check=True,env=env)
    elif a.latency_listing:
        symbols = a.latency_listing.read_text(encoding='latin1')
        match = re.search(r'^s60_update\s+00:([0-9A-F]+)', symbols, re.M)
        if a.tick is None or match is None:
            raise ValueError('--latency-listing requires a SIM60 tick capture and matching symbols')
        # Offset is relative to the slave code hunk; s60_entry is not offset zero.
        entry_symbol = int(re.search(r'^s60_entry\s+00:([0-9A-F]+)', symbols, re.M)[1],16)
        update_offset = int(match[1],16)-entry_symbol
        subprocess.run([sys.executable,'tools/swap_fields.py',str(a.fields),str(out),
                        str(out/'code.bin'),hex(base),str(out/'chip.bin'),
                        '--field-hz',str(field_hz),'--update-offset',str(update_offset)],check=True,env=env)
    elif a.state_only:pass
    elif a.swaps_only:
        subprocess.run([sys.executable,'tools/swap_fields.py',str(a.fields),str(out),str(out/'code.bin'),hex(base),str(out/'chip.bin'),'--field-hz',str(field_hz)],check=True,env=env)
    else:
        cmd(f'profile {a.fields} {out}/trace.bin')
        from amigaxdev import barto
        t=barto.load(out/'trace.bin')
        if len(t.fields) != a.fields:raise RuntimeError(f'Requested {a.fields} fields, captured {len(t.fields)}')
        (out/'first.png').write_bytes(t.fields[0].shot);(out/'last.png').write_bytes(t.fields[-1].shot)
        for tool,target in ([] if a.raw_trace else [('stellar7_report.py','report.txt'),('frames.py','frames.txt')]):
            args=[sys.executable,'tools/'+tool,str(out/'trace.bin'),str(out/'code.bin')]
            args+=['--base',hex(base)] if tool=='stellar7_report.py' else [hex(base),'--field-hz',str(field_hz)]
            with (out/target).open('w') as f:subprocess.run(args,stdout=f,env=env,check=True)
    native_events = []
    if a.native_events:
        native_events.append(dict(frame=count, field=struct.unpack_from('>I',mem,data-base+0x24a8)[0]))
    previous_boundary = requested
    for checkpoint in (a.tick_checkpoints if a.tick is not None else a.checkpoints):
        if a.native_events:
            # Debugger variables only. Observing every presentation anchor proves
            # that frame deltas contain no skipped draws or counter resets.
            previous = native_events[-1]['frame']
            reply=cmd(f'''gdb break *{anchor:#x}
set $s7_native_frame = {previous}
set $s7_native_valid = 1
while $s7_native_frame < {checkpoint} && $s7_native_valid
continue
set $s7_native_next = *(unsigned short*){counter:#x}
if $s7_native_next != $s7_native_frame + 1
set $s7_native_valid = 0
end
set $s7_native_frame = $s7_native_next
printf "S7NATIVE %u %u\\n", $s7_native_frame, *(unsigned int*){data+0x24a8:#x}
end
delete''')
            observed=[dict(frame=int(frame),field=int(field)) for frame,field in
                      re.findall(r'^S7NATIVE (\d+) (\d+)$',reply,re.M)]
            (out/f'native-events-{checkpoint}.txt').write_text(reply)
            assert [e['frame'] for e in observed] == list(range(previous+1,checkpoint+1)), 'Native frame reset or skipped presentation'
            native_events.extend(observed)
            (out/'native-events.json').write_text(json.dumps(dict(field_hz=field_hz,anchor_offset='0x2c16',events=native_events),indent=2)+'\n')
        else:
            stop_condition = f' || *(unsigned char*){data+0x1e53:#x} == 0' if a.stop_on_inactive else ''
            reply=cmd(f'gdb break *{anchor:#x}\ncondition $bpnum ((*({counter_type}*){counter:#x} >= {checkpoint}{level_condition}){stop_condition})\ncontinue\ndelete')
        folder=out/'checkpoints'/str(checkpoint)
        mem,ch=dump(folder)
        count=boundary_count(mem)
        inactive = a.stop_on_inactive and mem[data-base+0x1e53] == 0
        if inactive:
            assert level_matches(mem), 'inactive boundary is outside requested level/session'
            assert previous_boundary < count <= checkpoint, 'inactive boundary reset or skipped'
        if not inactive and (count != checkpoint or not level_matches(mem)):raise RuntimeError(f'Expected checkpoint {checkpoint} in level {a.level}, stopped at {count}')
        legacy_count=struct.unpack_from('>H',mem,data-base+0x1e96)[0]
        captured_tick=checkpoint if a.tick is not None else None
        (folder/'anchor.txt').write_text(reply+f'\nframe={legacy_count}\ntick={captured_tick}\ncode={h:#x}\ndata={data:#x}\nbase={base:#x}\n')
        (folder/'state.bin').write_bytes(mem[data-base:data-base+0x823c])
        if inactive:
            (out/'terminal.json').write_text(json.dumps(dict(requested_tick=checkpoint, actual_tick=count, reason='inactive gameplay', checkpoint=str(checkpoint)),indent=2)+'\n')
            # Anchor reports the actual completed tick, even for a terminal snapshot.
            anchor_text=(folder/'anchor.txt').read_text().replace(f'tick={checkpoint}\n',f'tick={count}\n')
            (folder/'anchor.txt').write_text(anchor_text)
            break
        previous_boundary=checkpoint
    # Retain the emulator configuration log for comparison with observed state.
    emulator_log = RUN/'fsuae/Cache/Logs/fs-uae.log.txt'
    if emulator_log.exists():
        with emulator_log.open(errors='replace') as source:
            settings = [line for line in source if 'Set option ' in line or
                        re.match(r'^(chip_memory|slow_memory|fast_memory|cpu|ntsc_mode|uae_ntsc) = ', line)]
        (out/'emulator-settings.log').write_text(''.join(settings))
        effective=emulator_log.parent/'debug.uae'
        if effective.exists():
            (out/'emulator-effective.uae').write_bytes(effective.read_bytes())
    print('Saved '+str(a.out),flush=True)
finally:
    try:cmd('quit',5)
    except (OSError,RuntimeError):pass
    try:server.wait(timeout=5)
    except subprocess.TimeoutExpired:server.terminate()
    log.close()
