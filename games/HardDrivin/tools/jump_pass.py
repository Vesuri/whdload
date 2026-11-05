"""Jump outcome per C4 jump probe: jump_pass.py RUN... (run from the game directory).

The lip speed (real MPH), each flight (passes with no wheel down: its fields,
the pitch at take-off and at touchdown, the fall velocity before touchdown),
and the crash (throttle cut after field 10)."""
import json, sys
def deg(p): return ((p + 720) % 1440 - 720) / 4
MPH = 0.28 * 0.1791 / 0.3504
for run in sys.argv[1:]:
    S = [r for r in json.load(open('tmp/prof/%s/motion.json' % run))['rows'] if r['kind'] == 'STEP']
    crash = next((r['field'] for r in S if r['throttle'] == 0 and r['field'] > 10), None)
    flights = []
    i = 0
    while i < len(S):
        if S[i]['mask'] == 0:
            j = i
            while j < len(S) and S[j]['mask'] == 0:
                j += 1
            if j < len(S):
                flights.append((S[i - 1] if i else S[i], S[j - 1], S[j]))
            i = j
        else:
            i += 1
    text = ['lip %.0f MPH' % (flights[0][0]['velocity'] * MPH) if flights else 'no flight']
    for a, b, c in flights:
        text.append('flight %d-%d (%d fields) pitch %.1f -> %.1f, fall %d' % (
            a['field'], c['field'], c['field'] - a['field'], deg(a['pitch']), deg(c['pitch']), b['fall_velocity']))
    print('%-14s %s | %s' % (run, ' | '.join(text), 'crash at %d' % crash if crash else 'no crash'))
