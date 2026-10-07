#!/usr/bin/env python3
"""Read LoV world state at successive VBL counter increments; never write guest memory.
Used by fixed_window.sh STATE_FIELDS with the emulator stopped at the tape anchor.
"""
import argparse, contextlib, json, os, re, shutil, socket, tempfile
from pathlib import Path
from lov import SOCK
from lov_report import regions
from lov_timing_state import decode, simulation_symbols, simulation_state

def command(s):
    with socket.socket(socket.AF_UNIX) as c:
        c.connect(SOCK);c.sendall(('gdb '+s).encode());chunks=[]
        while chunk:=c.recv(65536):chunks.append(chunk)
    reply=b''.join(chunks).decode()
    if 'ERROR' in reply:raise RuntimeError(reply)
    return reply

@contextlib.contextmanager
def retained_snapshots(out):
    # This GDB version does not accept quoted/spaced dump filenames. Keep its
    # paths in the system temp directory, then retain even incomplete output.
    with tempfile.TemporaryDirectory(prefix='lov-timing-') as temp:
        try:
            yield temp
        finally:
            for snapshot in Path(temp).glob('*.bin'):
                shutil.move(str(snapshot), out/snapshot.name)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('fields',type=int)
    p.add_argument('out',type=Path);p.add_argument('capture',type=Path)
    p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('--ticks', action='store_true', help='sample completed simulation ticks instead of VBL fields')
    p.add_argument('--initial-point', default='VERIFY tape anchor after VBL counter increment')
    a=p.parse_args()
    if a.fields < 1:p.error('fields must be positive')
    os.environ['SLAVE']=str(a.capture/'slave.slave')
    rr={n:lo for lo,hi,n,o in regions((a.capture/'code.bin').read_bytes(),a.base)}
    h11,h12=rr['h11'],rr['h12'];a.out.mkdir(parents=True,exist_ok=True)
    spans=[('input-mode',h11,h11+8),('active-clock',h11+0x4d6,h11+0x4e2),('clock',h11+0x6000,h11+0x6030),('player',h11+0x8c00,h11+0x8c44),
           ('projectiles',h11+0x90c,h11+0x90c+60*18),('animation',h11+0xdf0,h11+0xe00),('world',h12+0x9700,h12+0xdef0),
           ('periodic',h12+0x27ba,h12+0x27bc),
           ('daily-timers',h11+0x6080,h11+0x60ac),('daily-records',h11+0x4060,h11+0x43e0)]
    symbols=simulation_symbols((a.capture/'slave.lst').read_text(errors='replace'), rr['slave'])
    if symbols:
        spans.append(('simulation', min(symbols.values()), max(symbols.values())+4))
    input_match=re.search(r'^_sim_tick_input\s+00:([0-9A-F]{8})\s*$', (a.capture/'slave.lst').read_text(errors='replace'), re.M)
    input_at=rr['slave']+int(input_match[1],16) if input_match else None
    if input_at is not None:
        spans.append(('tick-input', input_at, input_at+16))
    sample_pc=h12+0x640a
    tick_point='_sim_tick_complete'
    if a.ticks:
        listing=(a.capture/'slave.lst').read_text(errors='replace')
        if not re.search(r'^_sim_tick_complete\s+00:', listing, re.M):
            tick_point='_sim_end_tick'  # Retained pre-clock builds.
        match=re.search(r'^'+tick_point+r'\s+00:([0-9A-F]{8})\s*$', (a.capture/'slave.lst').read_text(errors='replace'), re.M)
        if not match or '_sim_started' not in symbols: p.error('tick sampling requires a simulation build')
        snapshot=(a.capture/'code.bin').read_bytes()
        started=simulation_state(lambda at,n: snapshot[at-a.base:at-a.base+n], symbols)['started']
        if not started: p.error('simulation must be active before tick sampling')
        sample_pc=rr['slave']+int(match[1],16)
    samples=[]
    if list(a.out.glob('[0-9][0-9][0-9][0-9]-*.bin')):
        p.error('sample output already contains snapshots; use a fresh capture directory')
    with retained_snapshots(a.out) as temp:
        # The anchor is inside VBL, after its counter increment. Subsequent samples
        # stop immediately after the next increment, giving exactly N counter fields.
        # Tick mode instead resumes first: the VBL anchor is not a completed tick.
        lines=[f'break *{sample_pc:#x}', 'set $lov_sample_bp = $bpnum']
        guards=[]
        if a.ticks:
            for name in ('_c2p_abort', '_timing_study_watchdog'):
                guard=re.search(r'^'+name+r'\s+00:([0-9A-F]{8})\s*$', listing, re.M)
                if guard:
                    variable=f'$lov_guard_{len(guards)}'
                    lines += [f'break *{rr["slave"]+int(guard[1],16):#x}', f'set {variable} = $bpnum']
                    guards.append(variable)
        lines+=['set $lov_sample = 0']
        lines+=[f'while $lov_sample <= {a.fields}']
        lines+=['continue'] if a.ticks else ['if $lov_sample > 0','continue','end']
        if a.ticks:
            lines += [f'if $pc != {sample_pc:#x}', 'loop_break', 'end']
        for label,lo,hi in spans:
            lines.append(f'eval "dump binary memory {temp}/%04d-{label}.bin {lo:#x} {hi:#x}", $lov_sample')
        lines+=['set $lov_sample = $lov_sample + 1','end',f'if $lov_sample <= {a.fields}',
                'info registers',f'dump binary memory {temp}/stopped-code.bin {a.base:#x} {a.base+len((a.capture/"code.bin").read_bytes()):#x}',
                'end', f'dump binary memory {temp}/final-code.bin {a.base:#x} {a.base+len((a.capture/"code.bin").read_bytes()):#x}',
                'delete $lov_sample_bp']
        lines += [f'delete {variable}' for variable in guards]
        (a.out/'gdb.txt').write_text(command('\n'.join(lines)))
        for i in range(a.fields+1):
            if not all(Path(temp,f'{i:04d}-{label}.bin').exists() for label,lo,hi in spans):
                break
            parts=[(lo,hi,Path(temp,f'{i:04d}-{label}.bin').read_bytes()) for label,lo,hi in spans]
            def read(at,n):
                for lo,hi,b in parts:
                    if lo<=at and at+n<=hi:return b[at-lo:at-lo+n]
                raise ValueError(f'unmapped state address {at:#x}')
            state=decode(read,h11,h12,extended=True)
            if symbols:
                state['simulation']=simulation_state(read,symbols)
                if a.ticks and tick_point == '_sim_tick_complete':
                    state['logical_clock']=state['simulation']['tick_clock']
            if input_at is not None:
                raw=read(input_at,16)
                state['input_sample']=dict(field=int.from_bytes(raw[:4],'big'),
                    x=int.from_bytes(raw[4:6],'big',signed=True), y=int.from_bytes(raw[6:8],'big',signed=True),
                    buttons=int.from_bytes(raw[8:10],'big'),
                    mouse_x=int.from_bytes(raw[10:12],'big'), mouse_y=int.from_bytes(raw[12:14],'big'))
            samples.append(state)
    (a.out/'samples.json').write_text(json.dumps(samples,indent=2)+'\n')
    (a.out/'metadata.json').write_text(json.dumps(dict(h11=h11,h12=h12,requested_intervals=a.fields, complete=len(samples)==a.fields+1,
        sample_unit='completed tick' if a.ticks else 'VBL field',
        initial_sample_point=tick_point+' before completed counter increment' if a.ticks else a.initial_point,
        subsequent_sample_point=tick_point+' before completed counter increment' if a.ticks else 'h12:0640a after VBL counter increment',
        elapsed_counter_fields=((samples[-1]['field']-samples[0]['field']) & 0xffffffff) if samples else None),indent=2)+'\n')
    print(f'{len(samples)} persistent-world samples retained in {a.out}')
    if len(samples) != a.fields+1:
        raise SystemExit('tick observation stopped early; partial snapshots and stopped state retained')
if __name__=='__main__':main()
