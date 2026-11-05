"""Remove regenerable scratch data (2026-10-23): traces, stopped runtimes, boot dumps, old listings."""
import json, os, shutil, sys
from pathlib import Path
base = Path.cwd(); prof = base / 'tmp/prof'; build = base / 'tmp/build'
dry = '--dry' in sys.argv; saved = 0; log = []
def drop(p):
    global saved
    if p.is_symlink(): return
    n = sum(f.stat().st_size for f in p.rglob('*') if f.is_file() and not f.is_symlink()) if p.is_dir() else p.stat().st_size
    saved += n; log.append(str(p.relative_to(base)))
    if not dry: shutil.rmtree(p) if p.is_dir() else p.unlink()
# profiler traces; frame-budget.json and the summaries stay
for f in prof.rglob('trace.bin*'): drop(f)
for run in sorted(prof.iterdir()):
    if run.is_symlink() or not run.is_dir(): continue
    if run.name.startswith('old-'): drop(run); continue
    for f in run.glob('calibration-*.bin'): drop(f)
    if (run / 'rec.bin').exists() or (run / 'motion.json').exists() or (run / 'model.bin').exists():
        for f in run.glob('anchor-*.bin'): drop(f)
print('prof: %.1f GB' % (saved / 1e9), flush=True)
# stopped emulator runtimes, keeping screenshots, configurations and scores
for run in (base / 'tmp/run').glob('*/.run'):
    if not run.is_dir() or run.is_symlink(): continue
    alive = False
    for p in run.rglob('*.pid'):
        try: os.kill(int(p.read_text().strip()), 0); alive = True
        except ProcessLookupError: pass
        except (ValueError, PermissionError): alive = True
    if alive: print('running, kept:', run); continue
    keep = run.parent / 'retained-runtime-files'
    for f in run.rglob('*'):
        if f.is_file() and not f.is_symlink() and (f.suffix.lower() in ('.png', '.jpg', '.fs-uae', '.uae') or 'high' in f.name.lower() or 'score' in f.name.lower()):
            t = keep / f.relative_to(run)
            if not dry: t.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(f, t)
    drop(run)
for d in (base / 'tmp/run').glob('*/fsuae'): drop(d)
print('with runtimes: %.1f GB' % (saved / 1e9), flush=True)
# listings of old test builds; the current, release and control ones stay
keep_prefix = ('su17-', 'b13-', 'r1', 'HardDrivin', 'drive', 'slow', 'p4-', 'p6-')
for f in build.glob('*.lst'):
    if not f.name.startswith(keep_prefix): drop(f)
print('total: %.1f GB in %d items%s' % (saved / 1e9, len(log), ' (dry run)' if dry else ''), flush=True)
if not dry: (base / 'tmp/cleanup-2026-10-23.json').write_text(json.dumps(log, indent=1) + '\n')
