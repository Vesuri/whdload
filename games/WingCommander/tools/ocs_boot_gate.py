#!/usr/bin/env python3
"""P13A3 OCS original/reconstructed boots, with native input and state waits.
No host game-code patches or CD32 layout assumptions. Optional host observations
and data-triggered diagnostics in explicitly selected candidate builds.
"""
import argparse
import hashlib
import json
import os
import re
import signal
import struct
from pathlib import Path
import subprocess
import time
import _amigaxdev
from amigaxdev.gdbserve import Server
from amigaxdev import barto
from ocs_runtime import BASE, LENGTH, SIZES, ROOT, locate


def main():
    global LENGTH
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    p.add_argument('--layout', help='calibrated layout.json from the same slave build')
    p.add_argument('--calibrate', action='store_true')
    p.add_argument('--simulator', action='store_true', help='continue from the menu to the first name prompt')
    p.add_argument('--baseline', choices=('on', 'off'), help='P13A4 two short field-bounded native windows')
    p.add_argument('--teardown-build', help='build.json directory of a diagnostic --exit-probe candidate')
    p.add_argument('--view-fields', type=int, choices=(20,40,100), default=40)
    p.add_argument('--views', action='store_true', help='C5 diagnostic native view transitions (simulator disables view keys)')
    p.add_argument('--ownership', action='store_true', help='C4 candidate transition gate')
    p.add_argument('--clock-build',help='D2 candidate build directory')
    p.add_argument('--intro-cycle',action='store_true',help='D4 full 15-page cycle and repeat before simulator')
    p.add_argument('--prediction-mode',choices=('auto','off','on'),default='auto')
    p.add_argument('--draw-every',type=int,choices=(1,2,5),default=1)
    p.add_argument('--cpu', choices=('68000','68020'), default='68000')
    p.add_argument('--fast-kib', type=int, choices=(1024,2048,4096), default=4096)
    a = p.parse_args()
    if not a.ownership and (a.cpu != '68000' or a.fast_kib != 4096):
        p.error('machine overrides require --ownership')
    if a.intro_cycle and not (a.clock_build and a.baseline and a.simulator):p.error('intro cycle requires clock build, baseline and simulator')
    if a.clock_build and not a.ownership:p.error('clock gate requires ownership')
    if a.clock_build and a.views:p.error('clock view probes belong to the D3 gate')
    if a.draw_every!=1 and not a.clock_build:p.error('draw schedule requires a clock build')
    if a.views and not (a.ownership and a.baseline and a.teardown_build):p.error('view gate requires ownership, baseline and diagnostic build')
    if a.teardown_build and not a.ownership:p.error('teardown requires --ownership')
    LENGTH = a.fast_kib*1024
    out = (ROOT/a.output).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():
        raise ValueError('choose a new output below tmp/')
    if not a.calibrate and not a.ownership and (os.environ.get('WARP','0') != '0' or os.environ.get('AMIGA_SETUP','a500') != 'a500'):
        raise ValueError('P13A3 gate requires real-speed A500/Fast')
    if any(c.isspace() for c in str(out.relative_to(ROOT))):
        raise ValueError('GDB requires a scratch directory name without whitespace')
    if os.environ.get('EXTRA_ARGS'):
        raise ValueError('EXTRA_ARGS is not allowed in the fixed P13A3 gate')
    if os.environ.get('NTSC', '0') != '0' or os.environ.get('WHD_ARGS'):
        raise ValueError('P13A3 requires PAL and the original default options')
    for option in ('INTRO_STOCK_CLOCK', 'WC_NOMMU_CORE', 'WC_BASELINE_CACHE_MODEL',
                   'WC_CPU_SPEED', 'WC_INSTANT_BLITTER'):
        if os.environ.get(option, '0') not in ('', '0'):
            raise ValueError('diagnostic override not allowed: '+option)
    if not os.environ.get('FSUAE'):
        raise ValueError('set FSUAE to the local --ocs-pixels debugger build')
    out.mkdir(parents=True)
    os.chdir(ROOT)
    run = '../'+str(out.relative_to(ROOT))+'/run'
    env = dict(os.environ, FSUAE_RUN=run, WARP=os.environ.get('WARP','0') if a.calibrate or a.ownership else '0', WINDOW='front',
               JOY0='none', JOY1='none',
               DETERMINISTIC=os.environ.get('DETERMINISTIC', '1') if a.calibrate else '1',
               AMIGA_SETUP='a500', WC_VARIANT='ocs', WHD_ARGS='', OCS_STOCK_CLOCK='1' if a.baseline or a.ownership else '0')
    if a.ownership:
        env['EXTRA_ARGS']=f'--uae_cpu_model={a.cpu} --fast_memory={a.fast_kib}'
    if a.clock_build and a.layout:
        candidate=json.loads((ROOT/a.clock_build/'build.json').read_text())
        if candidate.get('prediction'):
            location=json.loads((ROOT/a.layout).read_text())['slave'];symbols=candidate['symbols']
            env['WC_OCS_PREDICTION_FIELDS']=','.join(f'{location+symbols[n]:x}' for n in ('ocs_target_field','release_render_time','ocs_prediction_queued'))
    server = Server('wc-gate',root=str(ROOT),run_dir='amiga/'+run,profile_window=False)
    g = None
    actions = []
    def command(text, timeout=60):
        answer = g.cmd(text,timeout=timeout)
        if any(x in answer for x in ('Invalid hex','Protocol error','Cannot access','Error')):
            raise RuntimeError(answer)
        return answer
    def dump(name, start, end):
        path = out/name
        command(f'dump binary memory {path.relative_to(ROOT)} {start:#x} {end:#x}')
        data = path.read_bytes()
        if len(data) != end-start: raise ValueError('incomplete dump')
        return data
    def until(address,label, condition=None):
        command(f'break *{address:#x}')
        if condition:
            command('condition $bpnum '+condition)
        print('waiting for '+label,flush=True)
        try:
            answer = command('continue',timeout=120 if a.ownership else 600)
        except TimeoutError:
            # Synchronous continue does not set Gdb.running. Interrupt this
            # owned debugger and consume its pending reply before diagnostics.
            g.p.send_signal(signal.SIGINT)
            g.read_until(g.sent,30)
            raise
        g.running = False
        command('delete')
        pc = command('info registers pc')
        if int(pc.split()[1],16) != address or 'Breakpoint' not in answer:
            raise ValueError('checkpoint was not reached: '+answer+' '+pc)
        actions.append({'checkpoint':label,'pc':address})
        print('reached '+label,flush=True)
    def key(state, code='45'):
        command(f'monitor key {code} {state}')
        actions.append({'key':code,'pressed':state})
    try:
        g = server.boot(env)
        if a.calibrate:
            for attempt in range(90):
                g.cont(); time.sleep(1); g.stop()
                try: memory = dump(f'calibration-{attempt}.bin',BASE,BASE+LENGTH)
                except RuntimeError: continue
                try: layout = locate(memory)
                except ValueError: continue
                (out/'layout.json').write_text(json.dumps(layout,indent=2)+'\n')
                print('calibrated live patched segment chain',flush=True)
                return
            raise TimeoutError('game segments did not load')
        if not a.layout: raise ValueError('--layout or --calibrate is required')
        layout = json.loads((ROOT/a.layout).read_text())
        h0 = layout['hunks'][0]
        if 'key-raw-v1' not in g.cmd('monitor inputcaps'):
            raise ValueError('native key route unavailable; build the local debugger or supply a capable FSUAE')
        def capture(label):
            memory = dump(label+'-fast.bin', BASE, BASE+LENGTH)
            actual = locate(memory)
            if actual != layout:
                raise ValueError('calibrated layout changed')
            a4 = int(command('info registers a4').split()[1], 16)
            if a4 != layout['a4']:
                raise ValueError('live A4 differs from startup relocation')
            for n, (base, size) in enumerate(zip(layout['hunks'], SIZES)):
                (out/f'{label}-h{n}.bin').write_bytes(memory[base-BASE:base-BASE+size])
            dump(label+'-chip.bin', 0, 0x80000)
            (out/(label+'-registers.txt')).write_text(command('info registers'))
            trace = out/(label+'-screen.bin')
            command(f'monitor profile {3 if label == "teardown" else 2 if label == "name" else 1} "" "{trace}"', timeout=120)
            shot = barto.load(str(trace)).fields[-1].shot
            if not shot or not shot.startswith(b'\x89PNG\r\n\x1a\n'):
                raise ValueError('lossless screenshot required; use build_debugger.py --ocs-pixels')
            (out/(label+'.png')).write_bytes(shot)
            print('captured '+label, flush=True)

        def baseline(label, fields=250):
            path = out/(label+'-events.txt')
            print(f'measuring {label} ({fields} fields)', flush=True)
            command(f'monitor ocs-window {fields} {int(a.baseline == "on")} {h0:x} {layout["hunks"][1]:x} "{path}"', timeout=180)
            capture(label)

        # Leave the Origin animation running to its input poll, then use its
        # native Escape handling. The world title/credits run is not skipped
        # until the first completed credit picture has been captured.
        until(h0+0x180c8, 'Origin input poll O:180c8')
        capture('origin')
        key(1)
        until(h0+0x1edde, 'world intro entry O:1edde')
        key(0)
        intro_build=json.loads((ROOT/a.clock_build/'build.json').read_text()) if a.clock_build else {}
        if intro_build.get('intro'):
            if hashlib.sha256(Path(env['SLAVE']).read_bytes()).hexdigest()!=intro_build['sha256']:
                raise ValueError('intro build differs from booted slave')
            ib=layout['slave'];isy=intro_build['symbols']
            if a.prediction_mode!='auto':
                path=out/'intro-prediction-mode.bin';path.write_bytes(struct.pack('>H',1 if a.prediction_mode=='off' else 2))
                command(f'monitor ocs-load {ib+isy["ocs_prediction_mode"]:x} "{path}"')
            until(ib+isy['intro_world_done'], 'title update 100', '$d2 == 99')
        else:
            if a.intro_cycle:raise ValueError('intro cycle requires D4 build')
            until(h0+0x1efb0, 'title update 100 O:1efb0', '$d2 == 100')
        capture('title')
        until(h0+0x1f03c, 'credit picture submitted O:1f03c')
        capture('credits')
        if a.baseline: baseline('asteroids')
        if a.intro_cycle:
            pages=[]
            for page in range(15):
                if page:
                    until(h0+0x1f03c,f'credit page {page}',f'$d5 == {page}')
                capture(f'page{page}')
                raw=(out/f'page{page}-h1.bin').read_bytes()
                regs=command('info registers d4 d5')
                pages.append(dict(page=page,field=int.from_bytes(raw[0x77fe:0x7802],'big'),registers=regs))
            until(h0+0x1eeb2,'intro cycle repeat')
            capture('repeat')
            until(ib+isy['intro_world_done'],'repeated title update 100','$d2 == 99')
            capture('repeat-title')
            until(h0+0x1f03c,'repeated credits first picture')
            capture('repeat-credits')
            (out/'intro-pages.json').write_text(json.dumps(pages,indent=2)+'\n')
        key(1)
        until(h0+0x1f396, 'campaign menu entry O:1f396')
        key(0)
        until(h0+0x1f43c, 'menu ready O:1f43c')
        capture('menu')
        if a.simulator or a.baseline:
            # OCS starts at (159,99), over the absent Secret Missions option.
            # Native Up moves the pointer into Vega's rectangle (45,51)-(279,89).
            key(1, '4c')
            until(h0+0x1f43c, 'pointer over Vega O:1f43c', '*(short*)($a4+0x19e) <= 80')
            key(0, '4c')
            key(1, '44')
            until(h0+0x1f44e, 'menu selection accepted O:1f44e')
            key(0, '44')
            if int(command('info registers d2').split()[1], 16) != 0:
                raise ValueError('Vega campaign was not selected')
            until(h0+0x0694, 'simulator flight loop O:0694')
            if a.clock_build:
                build=json.loads((ROOT/a.clock_build/'build.json').read_text())
                if not build.get('clock') or hashlib.sha256(Path(env['SLAVE']).read_bytes()).hexdigest()!=build['sha256']:
                    raise ValueError('clock build differs from booted slave')
                sy=build['symbols'];sb=layout['slave']
                path=out/'clock-schedule.bin';path.write_bytes(struct.pack('>I',a.draw_every))
                command(f'monitor ocs-load {sb+sy["ocs_clock_draw_every"]:x} "{path}"')
                if a.prediction_mode!='auto':
                    if not build.get('prediction'):raise ValueError('prediction mode requires D3 build')
                    path=out/'prediction-mode.bin';path.write_bytes(struct.pack('>H',1 if a.prediction_mode=='off' else 2))
                    command(f'monitor ocs-load {sb+sy["ocs_prediction_mode"]:x} "{path}"')
                clock_samples=[]
                for tick in ((2,51) if build.get('prediction') and a.cpu=='68000' else (2,41,51) if build.get('prediction') else (2,11,21,31)):
                    until(sb+sy['ocs_clock_tick_done'],f'completed clock tick {tick}',
                          f'*(unsigned int*){sb+sy["ocs_clock_completed"]:#x} == {tick}')
                    dump(f'tick{tick}-data.bin',layout['hunks'][1],layout['hunks'][1]+SIZES[1])
                    dump(f'tick{tick}-clock.bin',sb+sy['ocs_clock_state'],sb+sy['ocs_clock_cancel']+2)
                    field=int.from_bytes(dump(f'tick{tick}-field.bin',layout['hunks'][1]+0x77fe,layout['hunks'][1]+0x7802),'big')
                    clock_samples.append(dict(tick=tick,field=field))
                    if build.get('prediction') and ((tick==2 and a.cpu=='68000') or (tick==41 and a.cpu!='68000')):
                        command('monitor trace-window-all')
                        command(f'monitor profile 10 "" "{out}/prediction-cost.bin"',timeout=120)
                    if tick==2 and build.get('prediction') and a.baseline:
                        if a.cpu!='68000':key(1,'40')
                        baseline('fire',200 if a.cpu=='68000' else 150)
                        if a.cpu!='68000':key(0,'40')
                (out/'clock-samples.json').write_text(json.dumps(dict(samples=clock_samples,draw_every=a.draw_every,prediction_mode=a.prediction_mode,build_sha256=build['sha256']),indent=2)+'\n')
                if not (build.get('prediction') and a.cpu=='68000'):
                    until(sb+sy['ocs_clock_iteration'],'clock picture completed')
            else:
                until(h0+0x06c2, 'simulator first iteration O:06c2')
            capture('simulator')
            if a.views:
                build=json.loads((ROOT/a.teardown_build/'build.json').read_text())
                if hashlib.sha256(Path(env['SLAVE']).read_bytes()).hexdigest()!=build['sha256']:
                    raise ValueError('view probe build differs from booted slave')
                for view in (2,1,3,0):
                    address=layout['slave']+build['symbols']['view_probe_request']
                    path=out/f'view{view}-trigger.bin';path.write_bytes(struct.pack('>I',view+1))
                    command(f'monitor ocs-load {address:x} "{path}"')
                    if dump(f'view{view}-trigger-readback.bin',address,address+4)!=path.read_bytes():
                        raise ValueError('view request not stored')
                    until(h0+0x06c2, f'diagnostic native view {view} active', f'*(short*)($a4-18318) == {view}')
                    baseline(f'view{view}',a.view_fields)
            if a.baseline and not (a.clock_build and build.get('prediction')):
                key(1, '40')  # Native Space: fire, no artificial game writes.
                baseline('fire',150 if a.clock_build and build.get('prediction') else 100 if a.clock_build else 250)
                key(0, '40')
            # A fast run can enter the prompt during the final capture. Its
            # recurring input loop is a reliable endpoint even then.
            until(h0+0x16992, 'name input loop O:16992')
            flag = command(f'x/bx {h0+0x3291c:#x}')
            if int(flag.rsplit(':', 1)[1].strip(), 16):
                until(h0+0x32e2c, 'name conversion published O:32e2c')
                until(h0+0x16992, 'name input after publication O:16992')
            capture('name')
            if a.teardown_build:
                build=json.loads((ROOT/a.teardown_build/'build.json').read_text())
                if not build.get('exit_probe'):raise ValueError('no diagnostic teardown trigger')
                if hashlib.sha256(Path(env['SLAVE']).read_bytes()).hexdigest()!=build['sha256']:
                    raise ValueError('teardown build differs from booted slave')
                # Installed before first execution; toggling data avoids stale
                # instruction-cache lines and unsupported GDB register writes.
                address=layout['slave']+build['symbols']['exit_probe_trigger']
                path=out/'teardown-trigger.bin';path.write_bytes(struct.pack('>I',1))
                command(f'monitor ocs-load {address:x} "{path}"')
                if dump('teardown-trigger-readback.bin',address,address+4)!=path.read_bytes():
                    raise ValueError('teardown trigger not stored')
                until(layout['slave']+build['symbols']['exit_probe_done'],
                      'native source/display teardown completed')
                capture('teardown')
        logfile = out/'run/fsuae/Cache/Logs/fs-uae.log.txt'
        options = dict(re.findall(r'Set option (\w+) = "([^"]*)"', logfile.read_text(errors='replace')))
        expected = dict(cpu_model=a.cpu, chipset='ocs', chipmem_size='1', fastmem_size=str(a.fast_kib//1024),
                        bogomem_size='0', cpu_speed='real', cpu_frequency='0' if a.baseline or a.ownership else '7093790',
                        cpu_cycle_exact='true', cpu_memory_cycle_exact='true', blitter_cycle_exact='true')
        for name, value in expected.items():
            if options.get(name) != value:
                raise ValueError('effective machine differs: '+name)
        boot = next((out/'run').glob('boot.*'))
        slave = (boot/'dh1/WingCommander/WingCommander.Slave').read_bytes()
        metadata = dict(layout, actions=actions, slave_sha256=hashlib.sha256(slave).hexdigest(),
                        whd_args=env['WHD_ARGS'], fsuae_sha256=hashlib.sha256(Path(env['FSUAE']).read_bytes()).hexdigest(),
                        machine=f'{a.cpu}-ocs-512k-chip-{a.fast_kib}k-fast', warp=env['WARP']=='1', variant='ocs', effective=expected,
                        checkpoints=['origin', 'title', 'credits', 'menu'] +
                        (['simulator', 'name'] if a.simulator or a.baseline else []))
        if a.intro_cycle:
            metadata['checkpoints'] += [f'page{i}' for i in range(15)]+['repeat','repeat-title','repeat-credits']
        if a.teardown_build and (a.simulator or a.baseline):
            metadata['checkpoints'].append('teardown')
        if a.views:
            metadata['checkpoints'] += ['view2','view1','view3','view0']
            metadata['view_fields']=a.view_fields
        if a.baseline:
            metadata.update(baseline=a.baseline, fields_per_window=250, fire_fields=(200 if a.cpu=='68000' else 150) if a.clock_build and build.get('prediction') else 100 if a.clock_build else 250, flight_input='coast' if a.clock_build and build.get('prediction') and a.cpu=='68000' else 'held fire')
            metadata['checkpoints'] += ['asteroids', 'fire']
        (out/'result.json').write_text(json.dumps(metadata, indent=2)+'\n')
    except Exception:
        if g:
            try:
                if g.running:
                    g.stop()
                (out/'failure-registers.txt').write_text(g.cmd('info registers', timeout=10))
                trace = out/'failure-screen.bin'
                g.cmd(f'monitor profile 1 "" "{trace}"', timeout=30)
                (out/'failure.png').write_bytes(barto.load(str(trace)).fields[-1].shot)
            except Exception:
                pass
        raise
    finally:
        (out/'actions.json').write_text(json.dumps(actions,indent=2)+'\n')
        if g: g.p.kill()
        subprocess.run(['/bin/bash',str(ROOT/'amiga/run.sh'),'stop'],env=env,check=True)

if __name__ == '__main__': main()
