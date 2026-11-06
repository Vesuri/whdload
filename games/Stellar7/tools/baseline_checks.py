#!/usr/bin/env python3
"""Step 7 regression checks on the validation machines (docs/open-work.md).

Each check captures serially under the shared tmp/rate-matrix.lock, selects its machines
by named setup (tools/machines.py) and writes PREFIX/<check>/validation.json:

  input      recorded-controls and native key-queue fixtures on every setup; a1200-fast
             and a1200-060 mapped state compared at the same rate
  delayed    SLOW_DRAW=20 on a1200-fast against the rate matrix's cells (MATRIX): N=3
             SOL, boss and heavy combat against a500-1.5m, N=12 heavy against a1200-fast
  lifecycle  death/Continue, declining Continue, normal and early level exit at N=3
             (a500-1.5m against delayed a1200-fast) and N=12 (a1200-060 against delayed
             a1200-fast), plus the CUSTOM1-off preservation check per rate
  buffers    displayed-buffer reuse on a1200-060: scanout stability and draw ordering
             with BUFFER_REUSE=1, the BUFFER_REUSE=0 control recorded beside it
  buffers_normal  the same two builds (after buffers) over 100 normal-speed fields
  builds     release bytes against a reference revision, the off switches, diagnostic
             exclusion and the release hook audits

Completed captures are reused; an incomplete one stops the run. Mapped-state
comparisons admit only deferred projection scratch.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import audit_hooks
import check_disabled
import death_state
import input_history_state
import level_state
import machines
import presentation_buffers
import presentation_report
import rate_matrix
import rate_matrix_report
import sim60_state
import simulation_rate
import simulation_state

ROOT = Path(__file__).resolve().parent.parent
VARIANTS = ('Stellar7', 'Stellar7-Sim60', 'Stellar7-Sim68000')


def rel(path):
    return os.path.relpath(path, ROOT)


def substeps(setup):
    return 3 if machines.resolve(setup)['cpu'] in ('68000', '68010') else 12


def base_flags(setup, n):
    """The playable build at rate N for this machine's CPU path."""
    flags = f'-DSIM60=1 -DS60_SUBSTEPS={n}'
    if machines.resolve(setup)['cpu'] in ('68000', '68010'):
        flags += ' -DPOLYGON_BLIT_IRQ=1'
    return flags


def capture(out, name, setup, flags, window, whd_args='CUSTOM1=1 CUSTOM3=1', prebuilt=None, extra_args=None):
    """One fixed_window.py capture, reused when complete; returns the capture folder."""
    folder, listing = out/name, out/(name+'.lst')
    done = folder/'done'
    if done.exists():
        return folder
    if folder.exists() and any(folder.iterdir()):
        raise ValueError(f'incomplete capture retained: {rel(folder)}; move it aside')
    if prebuilt is None:
        flags += ' -L '+rel(listing)
    env = dict(machines.env(setup), WHD_ARGS=whd_args, VERIFY_FLAGS=flags)
    if extra_args:
        env['EXTRA_ARGS'] = extra_args
    command = [sys.executable, 'tools/fixed_window.py', rel(folder), '--boot-timeout', '1800', *window]
    if prebuilt is not None:
        command += ['--prebuilt', rel(prebuilt)]
    print('Capturing '+rel(folder), flush=True)
    with (out/(name+'.log')).open('w') as log:
        subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    if prebuilt is None:
        listing.with_suffix('.slave').write_bytes((folder/'slave.slave').read_bytes())
    meta = json.loads((folder/'metadata.json').read_text())
    assert meta.get('setup') == setup, (name, meta.get('setup'), setup)
    rate_matrix_report.settings(folder, meta)
    done.touch()
    return folder


def compare(a, b):
    """Mapped gameplay, HUD, reticle and fresh projection state must match."""
    diffs = list(simulation_state.differences(simulation_state.snapshot(a, True, True),
                                              simulation_state.snapshot(b, True, True)))
    unexpected = [x for x in diffs if not x.startswith('projection_scratch')]
    assert not unexpected, (rel(a), rel(b), unexpected)
    return dict(reference=rel(a), candidate=rel(b), deferred_scratch_differences=diffs)


def history(folder):
    result = input_history_state.read(folder)
    assert not result['missing_ticks'] and not result['queue_drops'], (rel(folder), result)
    return result


def check_input(out, args):
    results, comparisons = {}, []
    for setup in machines.MACHINES:
        n = substeps(setup)
        folder = capture(out, setup, setup, base_flags(setup, n)+' -DHISTORY_TEST=1 -DHISTORY_QUEUE_TEST=1',
                         ['--tick', '200', '--tick-checkpoints', '220', '--state-only', '--fields', '1'],
                         whd_args='CUSTOM1=1')
        listing = out/(setup+'.lst')
        fixture = input_history_state.fixture(folder/'checkpoints/220')
        assert fixture['native_assertions'] is not None, 'native key-queue fixture missing'
        results[setup] = dict(substeps=n, fixture=fixture, hooks=audit_hooks.installed(folder, listing))
    for point in ('', 'checkpoints/220'):
        comparisons.append(compare(out/'a1200-fast'/point, out/'a1200-060'/point))
    return dict(results=results, same_rate=comparisons)


def check_delayed(out, args):
    matrix = args.matrix.resolve()
    results = {}
    for n, route, reference in ((3, 'sol', 'a500-1.5m'), (3, 'boss', 'a500-1.5m'),
                                (3, 'type10-heavy', 'a500-1.5m'), (12, 'type10-heavy', 'a1200-fast')):
        start, end, fixture, points = rate_matrix.route_window(route, n)
        cell = matrix/(reference+'-'+route)
        config = json.loads((matrix/(cell.name+'.json')).read_text())['config']
        assert config['substeps'] == n and config['start'] == start and config['checkpoints'] == points, (cell, config)
        name = f'n{n}-{route}'
        window = ['--tick', str(start), '--tick-checkpoints', *map(str, points), '--state-only', '--fields', '1']
        if route.startswith('type10'):
            window += ['--level', '6']
        folder = capture(out, name, 'a1200-fast', base_flags('a1200-fast', n)+' -DSLOW_DRAW=20 '+fixture, window)
        pairs = [(cell, folder)]+[(cell/'checkpoints'/str(t), folder/'checkpoints'/str(t)) for t in points]
        comparisons = []
        for a, b in pairs:
            history(b)
            comparisons.append(compare(a, b))
        results[name] = dict(reference=rel(cell), comparisons=comparisons,
                             hooks=audit_hooks.installed(folder, out/(name+'.lst')))
    return results


def check_lifecycle(out, args):
    results, comparisons = {}, []
    for n, plain in ((3, 'a500-1.5m'), (12, 'a1200-060')):
        scale = lambda tick: (tick*n+11)//12
        trigger = scale(201)-1
        for scene in ('death-continue', 'death-decline', 'exit-normal', 'exit-early'):
            flags = f'-DDEATH_TEST={trigger}' if scene.startswith('death') else f'-DLEVEL_TEST={trigger} -DLEVEL_LAST=6'
            if scene == 'death-decline':
                flags += ' -DDEATH_DECLINE=1'
            if scene == 'exit-early':
                flags += ' -DLEVEL_EARLY=1'
            window = ['--tick', str(scale(600)), '--tick-checkpoints', str(scale(1500)), '--state-only', '--fields', '1']
            if scene.startswith('exit'):
                window += ['--level', '6']
            pair = []
            for setup, extra in ((plain, ''), ('a1200-fast', ' -DSLOW_DRAW=20')):
                name = f'n{n}-{scene}-{setup}'+('-delayed' if extra else '')
                folder = capture(out, name, setup, base_flags(setup, n)+extra+' '+flags, window)
                assert sim60_state.read(folder)['substeps'] == n
                result = dict(input_history=history(folder),
                              installed=audit_hooks.installed(folder, out/(name+'.lst')))
                if scene.startswith('death'):
                    result['death'] = death_state.read(folder, decline='decline' in scene)
                    death_state.validate(result['death'], decline='decline' in scene)
                else:
                    result['level'] = level_state.read(folder)
                    level_state.validate(result['level'])
                results[name] = result
                pair.append(folder)
            comparisons += [compare(*pair), compare(*[x/'checkpoints'/str(scale(1500)) for x in pair])]
        # CUSTOM1 off: the simulation stays out of the game; native code preserved.
        setup = 'a500-1.5m' if n == 3 else 'a1200-fast'
        name = f'n{n}-disabled-{setup}'
        folder = capture(out, name, setup, base_flags(setup, n), ['--frame', '90', '--state-only', '--fields', '1'],
                         whd_args='')
        results[name] = dict(disabled=check_disabled.inspect(folder, out/(name+'.lst'), True, False))
    return dict(results=results, comparisons=comparisons)


def check_buffers(out, args):
    setup, results, comparisons = 'a1200-060', {}, []
    for arm, enabled in (('control', 0), ('candidate', 1)):
        flags = base_flags(setup, 12)+f' -DBUFFER_REUSE={enabled}'
        trace = capture(out, arm+'-trace', setup, flags,
                        ['--tick', '600', '--tick-checkpoints', '1500', '--fields', '50', '--raw-trace'])
        listing = out/(arm+'-trace.lst')
        phase = capture(out, arm+'-phase', setup, flags,
                        ['--tick', '600', '--tick-checkpoints', '1500', '--fields', '50', '--state-only',
                         '--presentation-listing', rel(listing)], prebuilt=listing.with_suffix('.slave'))
        for folder in (trace, phase):
            assert (folder/'slave.slave').read_bytes() == listing.with_suffix('.slave').read_bytes()
            audit_hooks.installed(folder, listing)
        pixels = presentation_buffers.inspect(trace, require_stable=bool(enabled))
        events = json.loads((phase/'presentation-events.json').read_text())['events']
        last, reuse = None, []
        for event in events:
            if event['site'] == 'present_end':
                last = event
            elif event['site'] == 'draw_start' and last is not None:
                reuse.append(dict(present_field=last['epoch'], draw_field=event['epoch']))
        if enabled:
            assert reuse and all(x['draw_field'] > x['present_field'] for x in reuse), reuse
        results[arm] = dict(scanout=pixels, timing=presentation_report.inspect(phase), reuse=reuse,
                            changed_fields=len(pixels['same_buffer_word_changes']),
                            rates={name: simulation_rate.interval(folder, folder/'checkpoints/1500')
                                   for name, folder in (('trace', trace), ('phase', phase))})
    for name in ('control-phase', 'candidate-trace', 'candidate-phase'):
        for point in ('', 'checkpoints/1500'):
            comparisons.append(compare(out/'control-trace'/point, out/name/point))
    results['control_reproduces_defect'] = bool(results['control']['changed_fields'])
    return dict(results=results, comparisons=comparisons)


def check_buffers_normal(out, args):
    # The same two arms as buffers, 100 uninterrupted fields at normal speed.
    import shlex
    setup, results = 'a1200-060', {}
    builds = out.parent/'buffers'
    for arm, enabled in (('control', 0), ('candidate', 1)):
        binary = builds/(arm+'-trace.slave')
        folder = capture(out, arm, setup, base_flags(setup, 12)+f' -DBUFFER_REUSE={enabled}',
                         ['--tick', '600', '--fields', '100', '--raw-trace', '--retain-command'],
                         prebuilt=binary, extra_args='--warp_mode=0')
        words = shlex.split((folder/'emulator-command.txt').read_text())
        warp = [w.split('=', 1)[1] for w in words if w.startswith('--warp_mode=')]
        assert warp and warp[0] == '0', (arm, warp)
        assert (folder/'slave.slave').read_bytes() == binary.read_bytes()
        audit_hooks.installed(folder, builds/(arm+'-trace.lst'))
        pixels = presentation_buffers.inspect(folder, require_stable=bool(enabled))
        assert pixels['fields'] == 100
        results[arm] = dict(scanout=pixels, changed_fields=len(pixels['same_buffer_word_changes']), warp_options=warp)
    results['control_reproduces_defect'] = bool(results['control']['changed_fields'])
    results['comparison'] = compare(out/'control', out/'candidate')
    return results


def build(game, variant, extra='', build='release', substeps68000=None):
    env = {key: value for key, value in os.environ.items() if key not in ('VASM_EXTRA', 'SIM68000_SUBSTEPS', 'VERIFY_FLAGS')}
    env.update(VARIANT=variant, VASM_EXTRA=extra)
    if substeps68000 is not None:
        env['SIM68000_SUBSTEPS'] = str(substeps68000)
    subprocess.run(['make', '-s', 'build', 'BUILD='+build], cwd=game, env=env, check=True, stdout=subprocess.DEVNULL)
    return (game/'tmp/build'/build/(variant+'.Slave')).read_bytes()


def check_builds(out, args):
    # The reference revision's tracked game and shared build, exported into tmp/.
    reference = out/'reference'
    if reference.exists():
        shutil.rmtree(reference)
    reference.mkdir()
    top = Path(subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=ROOT, check=True,
                              capture_output=True, text=True).stdout.strip())
    revision = subprocess.run(['git', 'rev-parse', args.reference], cwd=ROOT, check=True,
                              capture_output=True, text=True).stdout.strip()
    archive = subprocess.run(['git', 'archive', revision, 'common', str(ROOT.relative_to(top))],
                             cwd=top, check=True, capture_output=True).stdout
    subprocess.run(['tar', '-x', '-C', str(reference)], input=archive, check=True)
    old_game = reference/ROOT.relative_to(top)
    sha = lambda blob: hashlib.sha256(blob).hexdigest()
    result = dict(reference=revision, releases={}, off_switches={}, exclusion={}, audits={})
    releases = {}
    for variant in VARIANTS:
        blob = build(ROOT, variant)
        listing = ROOT/'tmp/build/release'/(variant+'.lst')
        shutil.copyfile(listing, out/(variant+'.lst'))
        (out/(variant+'.slave')).write_bytes(blob)
        releases[variant] = blob
        old = build(old_game, variant)
        result['releases'][variant] = dict(sha256=sha(blob), size=len(blob), reference_sha256=sha(old),
                                           identical=blob == old)
        if variant != 'Stellar7':
            result['audits'][variant] = audit_hooks.audit(out/(variant+'.lst'))
    # The off switches rebuild the reference bytes; unchanged variants must already match.
    off = build(ROOT, 'Stellar7-Sim68000', '-DBLIT_IRQ_IDLE=0 -DSOUND_FAST=0')
    old = build(old_game, 'Stellar7-Sim68000')
    result['off_switches']['Stellar7-Sim68000 -DBLIT_IRQ_IDLE=0 -DSOUND_FAST=0'] = dict(sha256=sha(off), identical=off == old)
    for variant in ('Stellar7', 'Stellar7-Sim60'):
        assert result['releases'][variant]['identical'], (variant, 'changed from the reference')
    assert result['off_switches']['Stellar7-Sim68000 -DBLIT_IRQ_IDLE=0 -DSOUND_FAST=0']['identical']
    # The A500 rate override builds the same simulation at N=4.
    n4 = build(ROOT, 'Stellar7-Sim68000', substeps68000=4)
    result['rate_override'] = dict(sha256=sha(n4), differs_from_n3=n4 != releases['Stellar7-Sim68000'])
    assert result['rate_override']['differs_from_n3']
    # VERIFY-only fixtures and diagnostics compile to nothing in release builds.
    # SOUND_TWIN is refused where SOUND_FAST is off (Sim60), by design.
    fixtures = '-DRETICLE_TEST=100 -DRETICLE_BAD_RENDER=1 -DHISTORY_TEST=1 -DHISTORY_QUEUE_TEST=1 -DSLOW_DRAW=20'
    tags = sorted({line.split("'")[1].encode() for path in (ROOT/'src').glob('*_test.s')
                   for line in path.read_text(encoding='latin1').splitlines() if "dc.b '" in line
                   and len(line.split("'")[1]) == 4} | {b'BI60'})
    for variant in ('Stellar7-Sim60', 'Stellar7-Sim68000'):
        defines = fixtures+(' -DSOUND_TWIN=1 -DSOUND_TWIN_BAD=1' if variant == 'Stellar7-Sim68000' else '')
        blob = build(ROOT, variant, defines)
        markers = [tag.decode() for tag in tags if tag in releases[variant]]
        result['exclusion'][variant] = dict(fixtures=defines, identical=blob == releases[variant],
                                            verify_markers=markers)
        assert blob == releases[variant] and not markers, (variant, markers)
    build(ROOT, 'Stellar7-Sim68000')  # leave the default release build in place
    shutil.rmtree(reference)
    return result


CHECKS = dict(input=check_input, delayed=check_delayed, lifecycle=check_lifecycle,
              buffers=check_buffers, buffers_normal=check_buffers_normal, builds=check_builds)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('prefix', type=Path, help='directory under tmp/')
    parser.add_argument('checks', nargs='+', choices=CHECKS)
    parser.add_argument('--matrix', type=Path, help='rate matrix prefix for delayed (tools/rate_matrix.sh --selected-rates)')
    parser.add_argument('--reference', help='git revision whose release bytes builds compares against')
    args = parser.parse_args()
    if 'delayed' in args.checks and args.matrix is None:
        parser.error('delayed needs --matrix')
    if 'builds' in args.checks and args.reference is None:
        parser.error('builds needs --reference')
    prefix = args.prefix.resolve()
    prefix.relative_to(ROOT/'tmp')
    with (ROOT/'tmp/rate-matrix.lock').open('a') as lock:
        print('Waiting for the capture lock', flush=True)
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            for check in args.checks:
                out = prefix/check
                out.mkdir(parents=True, exist_ok=True)
                result = CHECKS[check](out, args)
                (out/'validation.json').write_text(json.dumps(result, indent=2)+'\n')
                print(f'{check}: passed', flush=True)
        finally:
            subprocess.run(['make', '-s', 'slave'], cwd=ROOT, stdout=subprocess.DEVNULL, check=True)


if __name__ == '__main__':
    main()
