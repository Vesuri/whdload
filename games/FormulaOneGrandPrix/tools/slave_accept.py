#!/usr/bin/env python3
"""Combine B3's paired windows and clean-quit evidence for the current slave build."""
import hashlib
import json
from slave_compare import BUILT, OUT, compare
from slave_inputs import verify

verify()
windows_ok = compare() == 0
metas = []
for case in ('baseline', 'repeat'):
    for phase in ('green', 'tow', 'follow'):
        path = OUT/case/phase/'meta.json'
        if path.exists():
            metas.append(json.loads(path.read_text()))
identity = ('slave_sha256', 'emulator_sha256', 'capture_tools_sha256', 'game_inputs', 'setup')
coherent = len(metas) == 6 and all(
    key in m and m[key] == metas[0].get(key) for m in metas for key in identity)
current = hashlib.sha256(BUILT.read_bytes()).hexdigest()
current_build = bool(metas) and all(m.get('slave_sha256') == current for m in metas)
path = OUT/'quit/result.json'
quit_result = json.loads(path.read_text()) if path.exists() else {}
quit_ok = (quit_result.get('exit_status') == 'OK'
           and quit_result.get('marker_absent_before_key') is True
           and quit_result.get('slave_sha256') == current
           and all(f'{screen}@' in quit_result.get('route', '')
                   for screen in ('language', 'protection', 'startup', 'track', 'race')))
checks = dict(paired_windows=windows_ok, coherent_capture_set=coherent,
              current_build=current_build, clean_f10_quit=quit_ok)
passed = all(checks.values())
report = dict(gate='B3-modern-KickEmu', status='PASS' if passed else 'FAIL',
              slave_sha256=current, checks=checks)
(OUT/'acceptance.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
raise SystemExit(0 if passed else 1)
