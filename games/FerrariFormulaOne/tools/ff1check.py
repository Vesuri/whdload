#!/usr/bin/env python3
"""Ferrari Formula One check runner: one entry point for the current test matrix.

  ff1check.py list
  ff1check.py run CHECK [CHECK...] [--profiles P,P] [--build DIR] [--tag TAG]
                  [--whd-args ARGS] [--emulator PATH] [--overrides JSON] [--force]
  ff1check.py changed [--run] [same options]   # feature checks whose sources changed
  ff1check.py release [same options]           # every check, for a release candidate

Matrix policy (manifest/project.json test_matrix_policy): no 68060 and no
WHDLoad 17.0. One A500 setup, except the memory check, which tries several
memory layouts. Core checks run on every source change. Feature checks run
when a file they cover changes (`changed`), and all of them run for a release.
Without --build, the working tree is built into tmp/build/ff1check/<tag>.

Each check is an existing harness script driven through environment variables:
FF1_BUILD (build dir), C1_VARIANT (output tag), RELEASE_WHD_ARGS,
RELEASE_FSUAE, RELEASE_PROFILE_OVERRIDES. Results land in
tmp/step5/c4-q03-<kind>-<profile>-<tag>/; this runner records pass stamps
(covered-source hashes) in manifest/check-stamps.json.
"""
import argparse, fnmatch, hashlib, json, os, subprocess, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[1]          # games/FerrariFormulaOne
sys.path.insert(0, str(R / 'tools'))
from ff1layout import legacy
GAMES = legacy()                                  # the old Games/ view, staged from src/ and tools/
STAMPS = R / 'tmp/manifest/check-stamps.json'
GAME = R / 'tmp/game/FerrariFormulaOne/data/racemenu'

CORE = ['a500', 'a1200', 'a1200-fast', '030-50-bce', '040-40-bce']
FAST = ['a1200', 'a1200-fast', '030-50-bce', '040-40-bce']
PERF = 'CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache'
ANY = ['FerrariFormulaOne_*.s', 'FerrariFormulaOne/*.s', 'FerrariFormulaOne/*.py',
       'FerrariFormulaOne/layout.json']

# A500 and chip-only memory layouts: (profile, tag, overrides, expect pass).
MEMORY = [
    ('a500', 'mem-slow1536', {'SLOW_KB': '1536'}, True),
    ('a500-fast', 'mem-fast2m', {'SLOW_KB': '0'}, True),
    ('a1200', 'mem-chip2m', {}, True),
    ('a500', 'mem-slow1024', {'SLOW_KB': '1024'}, False),
    ('a500', 'mem-slow512', {'SLOW_KB': '512'}, False),
    ('a1200', 'mem-chip1m', {'CHIP_KB': '1024'}, False),
]

# MMU variants on the shared emulator ($FSUAE_ARM): (profile, tag, overrides, WHDLoad extra).
# The 030 MMU case also enables WHDLoad's MMU option and emulated data cache.
MMU_DC = '--uae_cpu_data_cache=true --uae_uaeboard=full+indirect'
MMU = [
    ('030-50', 'mmu030', {'EXTRA_ARGS': '--uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_cycle_exact=true '
      '--uae_cpu_frequency=50000000 --uae_blitter_cycle_exact=true ' + MMU_DC}, ' MMU'),
    ('040-40', 'mmu040', {'CPU': '68040', 'EXTRA_ARGS': '--uae_mmu_model=68040 --uae_fpu_model=68040 '
      '--uae_cpu_24bit_addressing=false --uae_cpu_compatible=true --jit_compiler=0 ' + MMU_DC}, ''),
]

# name: script, result kind, default profiles, covered Games/ globs, core?
CHECKS = {
    'smoke':    dict(script='test_release_smoke.py', kind='release-smoke', profiles=CORE, covers=ANY, core=True,
                     whd='CUSTOM1=1 CUSTOM2=1 ConfigDelay=0',   # as the icons launch; chip-only 020 needs it
                     doc='20 production updates, no engine error'),
    'fps':      dict(script='test_h5_fps.py', kind='h5-fps', profiles=FAST, covers=ANY, core=True, whd=PERF,
                     doc='300-presentation FPS and live CACR in performance mode'),
    'gates':    dict(script='ff1_gates.py', kind=None, profiles=['040-40-bce'], covers=ANY, core=True,
                     doc='exact states, 30 stable frames (normal/grid) and elapsed clock vs B8-PAL'),
    'memory':   dict(script='test_release_smoke.py', kind='release-smoke', profiles=None, core=False,
                     covers=['FerrariFormulaOne_WHD.s', 'FerrariFormulaOne_PublicMemory.s',
                             'FerrariFormulaOne_PublicLoader.s', 'FerrariFormulaOne/layout.json',
                             'FerrariFormulaOne/build.py'],
                     whd='CUSTOM1=1 CUSTOM2=1 ConfigDelay=0',   # chip-only 020 needs ConfigDelay=0 on 20.1
                     doc='A500/chip-only memory layouts start (or fail) as documented'),
    'mmu':      dict(script='test_release_smoke.py', kind='release-smoke', profiles=None, core=False,
                     covers=['FerrariFormulaOne_Cache.s', 'FerrariFormulaOne_PublicMemory.s', 'FerrariFormulaOne_WHD.s'],
                     doc='030 WHDLoad MMU + data cache and 040 MMU, performance mode, 20 updates'),
    'lap':      dict(script='test_release_lap.py', kind='release-lap', profiles=['a500', 'a1200', 'a1200-fast'],
                     core=False, covers=['FerrariFormulaOne_Logic.s', 'FerrariFormulaOne_Track.s',
                     'FerrariFormulaOne_Position*.s', 'FerrariFormulaOne_Time.s', 'FerrariFormulaOne_UpdateHooks.s',
                     'FerrariFormulaOne_Coarse200Timing.s'], doc='native lap crossing and last-lap time'),
    'controls': dict(script='test_drive_controls.py', kind='controls', profiles=['a500', 'a1200-fast', '040-40-bce'],
                     core=False, covers=['FerrariFormulaOne_Speed.s', 'FerrariFormulaOne_Velocity.s',
                     'FerrariFormulaOne_Steering.s', 'FerrariFormulaOne_Physics200.s', 'FerrariFormulaOne_Step.s',
                     'FerrariFormulaOne_Coarse200Response.s', 'FerrariFormulaOne_Coarse200Motion.s',
                     'FerrariFormulaOne/Fine.s', 'FerrariFormulaOne/Coarse.s'],
                     doc='throttle/clutch, coast, braking, steering and gears (RC2 regression)'),
    'season':   dict(script='run_release_season.py', kind='release-live', profiles=['a500'], core=False,
                     covers=['FerrariFormulaOne_Coarse200Save.s', 'FerrariFormulaOne_PublicLoader.s',
                     'FerrariFormulaOne_PublicLifecycle.s', 'FerrariFormulaOne/ProductionHost.s'],
                     whd='CUSTOM1=1 CUSTOM2=1 NoWriteCache', doc='native season save'),
    'route':    dict(script='run_release_route.py', kind='release-live', profiles=['a1200-fast'], core=False,
                     covers=['FerrariFormulaOne_PublicLifecycle.s', 'FerrariFormulaOne_Opponents.s',
                     'FerrariFormulaOne_Time.s', 'FerrariFormulaOne/FinePause.s', 'FerrariFormulaOne/ProductionHost.s'],
                     doc='race control route: start, pause, tow, results, F10'),
    'modal':    dict(script='run_release_modal.py', kind='release-live', profiles=['a1200-fast'], core=False,
                     covers=['FerrariFormulaOne_Time.s', 'FerrariFormulaOne_Coarse200Timing.s',
                     'FerrariFormulaOne_Coarse200Wait*.s', 'FerrariFormulaOne_PublicLifecycle.s'],
                     doc='repair and transport calendar clocks'),
    'reload':   dict(script='run_release_legacy_reload.py', kind='release-legacy-live', profiles=['a500', 'a1200-fast'],
                     core=False, covers=['FerrariFormulaOne_PublicPatches.s', 'FerrariFormulaOne_PublicLoader.s',
                     'FerrariFormulaOne_PublicLifecycle.s', 'FerrariFormulaOne_Bindings.s', 'FerrariFormulaOne_Native*.s',
                     'FerrariFormulaOne/bindings.py', 'FerrariFormulaOne/native.py', 'FerrariFormulaOne/layout.json'],
                     doc='CUSTOM2=0 native overlay reloads keep the patch inventory exact'),
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def covered(check):
    files = sorted(p for p in GAMES.rglob('*') if p.is_file() and '__pycache__' not in p.parts
                   and any(fnmatch.fnmatch(str(p.relative_to(GAMES)), g) for g in CHECKS[check]['covers']))
    return {'Games/' + str(p.relative_to(GAMES)): sha(p) for p in files}


def load_stamps():
    return json.loads(STAMPS.read_text()) if STAMPS.exists() else {}


def build_tree(tag):
    out = R / 'tmp/build/ff1check' / tag
    subprocess.run([sys.executable, str(GAMES / 'FerrariFormulaOne/build.py'), '--game', str(GAME), '--out', str(out)],
                   cwd=R, check=True, stdout=subprocess.DEVNULL)
    return out


def cases(check, a):
    c = CHECKS[check]
    if check == 'memory':
        for prof, tag, ov, ok in MEMORY:
            yield prof, f'{a.tag}-{tag}', ov, ok
        return
    if check == 'mmu':
        for prof, tag, ov, extra in MMU:
            yield prof, f'{a.tag}-{tag}', ov, True
        return
    for prof in (a.profiles.split(',') if a.profiles else c['profiles']):
        yield prof, a.tag, {}, True


def run_one(check, prof, tag, ov, expect, build, a):
    c = CHECKS[check]
    env = dict(os.environ, FF1_BUILD=str(build), H5_BUILD=str(build), DRIVE_SLAVE=str(build / 'FerrariFormulaOne.slave'),
               C1_VARIANT=tag)
    whd = a.whd_args or c.get('whd')
    if check == 'mmu':
        whd = whd or PERF + ' COREDUMP' + dict((t, e) for _, t, _, e in MMU)[tag.rsplit('-', 1)[1]]
        env['RELEASE_FSUAE'] = a.emulator or os.environ['FSUAE_ARM']
    if whd:
        env['RELEASE_WHD_ARGS'] = whd
    if a.emulator:
        env['RELEASE_FSUAE'] = a.emulator
    if a.nondeterministic:
        env['FF1_DETERMINISTIC'] = '0'
    over = dict(json.loads(a.overrides or '{}'), **ov)
    if over:
        env['RELEASE_PROFILE_OVERRIDES'] = json.dumps(over)
    argv = [sys.executable, str(R / 'tools' / c['script'])]
    argv += ['--build', str(build), '--tag', tag] if check == 'gates' else [prof]
    log = R / 'tmp/ff1check' / f'{check}-{prof}-{tag}.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    t = time.time()
    with log.open('w') as f:
        rc = subprocess.run(argv, cwd=R, env=env, stdout=f, stderr=subprocess.STDOUT).returncode
    res = R / 'tmp/step5' / f"c4-q03-{c['kind']}-{prof}-{tag}" / 'result.json' if c['kind'] else None
    status = json.loads(res.read_text()).get('status') if res and res.exists() else None
    ok = (rc == 0) == expect
    print(f"{'PASS' if ok else 'FAIL'} {check} {prof} {tag} rc={rc} status={status} "
          f"expect={'pass' if expect else 'fail'} {time.time() - t:.0f}s log={log.relative_to(R)}", flush=True)
    return ok


def run(checks, a):
    a.tag = a.tag or time.strftime('ff1-%Y%m%d-%H%M')
    build = Path(a.build).resolve() if a.build else build_tree(a.tag)
    slave = sha(build / 'FerrariFormulaOne.slave')
    print(f'build {build} slave {slave[:12]}', flush=True)
    stamps, failed = load_stamps(), []
    for check in checks:
        ok = all([run_one(check, *x, build, a) for x in cases(check, a)])
        if ok and not (a.profiles or a.overrides or a.whd_args or a.emulator or a.nondeterministic):
            stamps[check] = dict(passed=time.strftime('%Y-%m-%dT%H:%M:%S'), slave_sha256=slave, tag=a.tag,
                                 sources=covered(check))
            STAMPS.write_text(json.dumps(stamps, indent=1) + '\n')
        if not ok:
            failed.append(check)
    print('FAILED ' + ' '.join(failed) if failed else 'ALL PASSED', flush=True)
    return 1 if failed else 0


def changed():
    stamps, out = load_stamps(), []
    for name, c in CHECKS.items():
        if c['core']:
            continue
        old = stamps.get(name, {}).get('sources')
        now = covered(name)
        diff = sorted(set(now.items()) ^ set((old or {}).items()))
        if old is None or diff:
            out.append((name, 'never passed' if old is None else ', '.join(sorted({k for k, _ in diff}))))
    return out


def main():
    if 'WHDLOAD' not in os.environ:                # needs the shared Amiga environment
        # env.sh also puts the shared Python (capstone, amitools) first on PATH.
        os.execvp('bash', ['bash', '-c', '. "$0"/../../common/env.sh && exec python3 "$0"/tools/ff1check.py "$@"',
                           str(R)] + sys.argv[1:])
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['list', 'run', 'changed', 'release', 'core'])
    ap.add_argument('checks', nargs='*')
    ap.add_argument('--profiles'); ap.add_argument('--build'); ap.add_argument('--tag')
    ap.add_argument('--whd-args'); ap.add_argument('--emulator'); ap.add_argument('--overrides')
    ap.add_argument('--nondeterministic', action='store_true', help='FF1_DETERMINISTIC=0')
    ap.add_argument('--run', action='store_true', help='with changed: also run core checks and the changed ones')
    a = ap.parse_args()
    if a.mode == 'list':
        st = load_stamps()
        for n, c in CHECKS.items():
            prof = {'memory': 'A500/chip-only memory layouts', 'mmu': '030-50 MMU+DC, 040-40 MMU'}.get(n) or ','.join(c['profiles'])
            last = st.get(n, {}).get('passed', '-')
            print(f"{n:9} {'core' if c['core'] else 'feature':8} {prof:40} last pass {last}  {c['doc']}")
        return 0
    if a.mode == 'changed':
        todo = changed()
        for n, why in todo:
            print(f'{n}: {why}')
        if not todo:
            print('no feature check covers a changed file')
        return run([n for n, c in CHECKS.items() if c['core']] + [n for n, _ in todo], a) if a.run else 0
    if a.mode == 'core':
        return run([n for n, c in CHECKS.items() if c['core']], a)
    if a.mode == 'release':
        return run(list(CHECKS), a)
    bad = [c for c in a.checks if c not in CHECKS]
    if bad or not a.checks:
        ap.error(f'unknown or missing checks {bad}; see list')
    return run(a.checks, a)


if __name__ == '__main__':
    sys.exit(main())
