#!/usr/bin/env python3
"""Capture a fixed SOL gameplay window with the VERIFY/CUSTOM5 menu fixture.
Usage: tools/fixed_window.py tmp/prof/base [--fields 100] [--frame 90] [--swaps-only]
CPU, CHIP_KB, FAST_KB, EXTRA_ARGS, AMIGA_MODEL and KICKSTART remain overridable.
"""
import argparse, os, socket, subprocess, sys, time, struct, json, re
from pathlib import Path
from stellar7 import SOCK
from stellar7_report import loaded_game_regions

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('out',type=Path)
p.add_argument('--fields',type=int,default=100)
p.add_argument('--frame',type=int,default=90)
p.add_argument('--level',type=int,choices=range(7),help='wait for this level before matching the requested boundary')
p.add_argument('--tick',type=int,help='capture a completed SIM60 tick instead of a legacy frame')
p.add_argument('--tick-checkpoints',type=int,nargs='*',default=[],help='additional completed SIM60 tick boundaries')
p.add_argument('--checkpoints',type=int,nargs='*',default=[],help='additional simulation frames to snapshot after the trace')
p.add_argument('--swaps-only',action='store_true')
p.add_argument('--state-only',action='store_true')
p.add_argument('--native-events',action='store_true',help='record every native presentation boundary between --frame and --checkpoints; requires --state-only')
p.add_argument('--prebuilt', type=Path, help='capture this retained VERIFY slave instead of rebuilding; caller supplies matching flags/listing')
p.add_argument('--boot-timeout', type=float, default=1800, help='seconds allowed for this boot to expose the loaded game')
p.add_argument('--latency-listing', type=Path, help='exact VERIFY listing; observe update starts over --fields even with --state-only')
a=p.parse_args()
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
    subprocess.run(['make','-s','-C','whdload','verify'],check=True)
    selected_slave = Path('whdload/Stellar7.Slave')
else:
    selected_slave = a.prebuilt
(out/'slave.slave').write_bytes(selected_slave.read_bytes())
env=dict(os.environ,SLAVE=str(out/'slave.slave'),WHD_ARGS='CUSTOM5=1 '+os.environ.get('WHD_ARGS',''),JOY0='none',JOY1='none',DETERMINISTIC='1',WARP='1')
os.environ['SLAVE']=env['SLAVE']
ntsc_mode = int(env.get('NTSC_MODE', '1'))
if ntsc_mode not in (0, 1):
    raise ValueError('NTSC_MODE must be 0 or 1')
field_hz = 60 if ntsc_mode else 50
fast=int(env.get('FAST_KB','0')); chip=int(env.get('CHIP_KB','512'))
slow_match = re.search(r'--slow_memory=(\d+)', env.get('EXTRA_ARGS', ''))
slow = int(slow_match[1]) if slow_match else 1536
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
        return a.level is None or struct.unpack_from('>H',memory,data-base+0x46a0)[0] == a.level
    level_condition = '' if a.level is None else f' && *(unsigned short*){data+0x46a0:#x} == {a.level}'
    count=boundary_count(mem)
    if level_matches(mem) and count>requested:raise RuntimeError(f'Already passed boundary {requested}: {count}')
    print(f'Waiting for gameplay {"tick" if a.tick is not None else "frame"} {requested}...',flush=True)
    reply=cmd(f'gdb break *{anchor:#x}\ncondition $bpnum *({counter_type}*){counter:#x} >= {requested}{level_condition}\ncontinue\ndelete')
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
    (out/'metadata.json').write_text(json.dumps(dict(code_base=h,data_base=data,base=base,frame=struct.unpack_from('>H',mem,data-base+0x1e96)[0],tick=a.tick,level_filter=a.level,fields=a.fields,cpu=env.get('CPU','68000'),chip_kb=chip,fast_kb=fast,slow_kb=slow,extra_args=env.get('EXTRA_ARGS',''),whd_args=env['WHD_ARGS'],verify_flags=env.get('VERIFY_FLAGS',''),ntsc_mode=ntsc_mode,field_hz=field_hz,observed_exec_hz=observed_hz),indent=2)+'\n')
    (out/'state.bin').write_bytes(mem[data-base:data-base+0x823c])
    print(f'At {"tick" if a.tick is not None else "frame"} {count}; capturing {a.fields} fields...',flush=True)
    if a.latency_listing:
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
        import barto
        t=barto.load(out/'trace.bin')
        if len(t.fields) != a.fields:raise RuntimeError(f'Requested {a.fields} fields, captured {len(t.fields)}')
        (out/'first.png').write_bytes(t.fields[0].shot);(out/'last.png').write_bytes(t.fields[-1].shot)
        for tool,target in [('stellar7_report.py','report.txt'),('frames.py','frames.txt')]:
            args=[sys.executable,'tools/'+tool,str(out/'trace.bin'),str(out/'code.bin')]
            args+=['--base',hex(base)] if tool=='stellar7_report.py' else [hex(base),'--field-hz',str(field_hz)]
            with (out/target).open('w') as f:subprocess.run(args,stdout=f,env=env,check=True)
    native_events = []
    if a.native_events:
        native_events.append(dict(frame=count, field=struct.unpack_from('>I',mem,data-base+0x24a8)[0]))
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
            reply=cmd(f'gdb break *{anchor:#x}\ncondition $bpnum *({counter_type}*){counter:#x} >= {checkpoint}{level_condition}\ncontinue\ndelete')
        folder=out/'checkpoints'/str(checkpoint)
        mem,ch=dump(folder)
        count=boundary_count(mem)
        if count != checkpoint or not level_matches(mem):raise RuntimeError(f'Expected checkpoint {checkpoint} in level {a.level}, stopped at {count}')
        legacy_count=struct.unpack_from('>H',mem,data-base+0x1e96)[0]
        captured_tick=checkpoint if a.tick is not None else None
        (folder/'anchor.txt').write_text(reply+f'\nframe={legacy_count}\ntick={captured_tick}\ncode={h:#x}\ndata={data:#x}\nbase={base:#x}\n')
        (folder/'state.bin').write_bytes(mem[data-base:data-base+0x823c])
    print('Saved '+str(a.out),flush=True)
finally:
    try:cmd('quit',5)
    except (OSError,RuntimeError):pass
    try:server.wait(timeout=5)
    except subprocess.TimeoutExpired:server.terminate()
    log.close()
