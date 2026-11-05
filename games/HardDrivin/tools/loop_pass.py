"""Loop outcome per C4 loop probe: loop_pass.py RUN... (run from the game directory)."""
import json, sys
def deg(p): return ((p + 720) % 1440 - 720) / 4
for run in sys.argv[1:]:
    S = [r for r in json.load(open('tmp/prof/%s/motion.json' % run))['rows'] if r['kind'] == 'STEP']
    top = min(S, key=lambda r: abs(abs(deg(r['pitch'])) - 180))
    crash = next((r['field'] for r in S if r['throttle'] == 0 and r['field'] > 10), None)
    lost = next((r for r in S if r['mask'] == 0), None)
    passed = crash is None and any(r['road_cursor'] - r['stunt_base'] >= 1000 and r['mask'] == 15 for r in S)
    print('%-12s top at %3d: v %d (%.0f MPH) | %s | %s | %s' % (
        run, top['field'], top['velocity'], top['velocity'] * .28,
        'contact lost at %d, pitch %.0f' % (lost['field'], deg(lost['pitch'])) if lost else 'contact kept',
        'crash at %d' % crash if crash else 'no crash', 'PASSED' if passed else 'failed'))
