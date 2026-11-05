#!/usr/bin/env python3
"""FR0 measurement matrix (FASTRAM_PLAN.md FR0). Sequential; skips passed results.

  fr0_run.py [--only SUBSTR] [--dry]

Requires tools/fr0_build.py base nodraw bench. Modes:
  base    today's slave                      (in-session reference)
  imm     today's slave, immediate blits     (FR0b: blits free, pixels exact)
  nodraw  drawing stages skipped             (FR0a floor)
  bench   nodraw + copy/kernel benchmarks    (FR0c/FR0d, trace only)
FPS: tools/test_h5_fps.py (300 intervals). Traces: tools/capture_hi25_profile.py
then tools/analyze_hi25_profile.py; detail.bin is gzip-compressed afterwards.
"""
import argparse, gzip, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

r = Path(__file__).resolve().parents[1]
PERF = 'CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache'
PROFILES = ['040-40-bce', '030-50-bce', 'a1200-fast']
SCENES = ['normal', 'solo', 'grid', 'dense']
prof = json.loads((r / 'tmp/manifest/step3-profiles.json').read_text())


def overrides(p, mode, kind='fps'):
    o = {}
    if mode == 'imm':
        o['EXTRA_ARGS'] = (prof[p].get('EXTRA_ARGS', '') + ' --uae_immediate_blits=true').strip()
    if kind == 'trace' and p.startswith('030'):
        o['CPU'] = '68EC030'      # HI25 M-3: the full-MMU 68030 loop is not instrumented
    return o


def jobs():
    out = []
    for p in PROFILES:
        for s in SCENES:
            for m in ['base', 'imm', 'nodraw']:
                out.append(('fps', p, m, s, None))
        for s in SCENES:
            out.append(('trace', p, 'imm', s, 30))
        for s in SCENES:
            out.append(('trace', p, 'nodraw', s, 30))
        out.append(('trace', p, 'bench', 'normal', 60))
        if p == '040-40-bce':
            for s in SCENES:
                out.append(('trace', p, 'base', s, 30))
    return out


def run(kind, p, mode, scene, fields, dry):
    build = 'base' if mode == 'imm' else mode
    b = r / f'tmp/build/fr0-{build}-{scene}'
    tag = f'fr0-{mode}-{scene}'
    if kind == 'fps':
        out = r / f'tmp/step5/c4-q03-h5-fps-{p}-{tag}'; script = 'test_h5_fps.py'
    else:
        out = r / f'tmp/step5/hi25-profile-{p}-{tag}'; script = 'capture_hi25_profile.py'
    res = out / 'result.json'
    sha = hashlib.sha256((b / 'FerrariFormulaOne.slave').read_bytes()).hexdigest()
    if res.exists():
        x = json.loads(res.read_text())
        if x.get('status') == 'passed' and x.get('slave_sha256') == sha and \
                (kind == 'fps' or (out / 'hi25-analysis.json').exists()) and \
                not (kind == 'trace' and p.startswith('030') and x.get('launch', {}).get('CPU') != '68EC030'):
            print('SKIP', kind, p, tag, flush=True); return True
    print('RUN', kind, p, tag, flush=True)
    if dry:
        return True
    env = dict(os.environ, H5_BUILD=str(b), FF1_BUILD=str(b), C1_VARIANT=tag, RELEASE_WHD_ARGS=PERF,
               RELEASE_PROFILE_OVERRIDES=json.dumps(overrides(p, mode, kind)))
    if mode in ('nodraw', 'bench'):
        env['FR0_NODRAW'] = '1'
    if fields:
        env['HI25_FIELDS'] = str(fields)
    log = r / f'tmp/fr0/{kind}-{p}-{tag}.log'; log.parent.mkdir(parents=True, exist_ok=True)
    t = time.time()
    with log.open('w') as f:
        rc = subprocess.run([sys.executable, str(r / 'tools' / script), p], env=env, stdout=f,
                            stderr=subprocess.STDOUT).returncode
        if rc == 0 and kind == 'trace':
            rc = subprocess.run([sys.executable, str(r / 'tools/analyze_hi25_profile.py'), str(out)], env=env,
                                stdout=f, stderr=subprocess.STDOUT).returncode
            if rc == 0 and mode == 'bench':
                rc = subprocess.run([sys.executable, str(r / 'tools/fr0_bench_analyze.py'), str(out)], env=env,
                                    stdout=f, stderr=subprocess.STDOUT).returncode
    for name in ['detail.bin', 'start.bin', 'start-fast.bin', 'end.bin', 'end-fast.bin', 'memory.bin',
                 'memory-fast.bin', 'canonical.bin']:
        q = out / name
        if q.exists():
            with q.open('rb') as i, gzip.open(str(q) + '.gz', 'wb', compresslevel=1) as o:
                shutil.copyfileobj(i, o)
            q.unlink()
    print('DONE' if rc == 0 else 'FAIL', kind, p, tag, f'rc={rc} {time.time()-t:.0f}s', flush=True)
    return rc == 0


ap = argparse.ArgumentParser(); ap.add_argument('--only', default=''); ap.add_argument('--dry', action='store_true')
a = ap.parse_args()
if 'WHDLOAD' not in os.environ:
    os.execvp('bash', ['bash', '-c', '. ~/.local/share/amiga/env.sh && exec python3 "$0" "$@"', __file__] + sys.argv[1:])
fails = []
for j in jobs():
    if a.only and a.only not in ' '.join(str(x) for x in j):
        continue
    if not run(*j, a.dry):
        fails.append(j)
print('FAILED' if fails else 'ALL DONE', fails, flush=True)
