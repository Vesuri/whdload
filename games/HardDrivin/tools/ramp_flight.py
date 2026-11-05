"""Ramp flights per run: ramp_flight.py RUN_DIR... (tools/capture_feel.py output, from the game directory).

For the first flight past 400 ft of the route: the lip (distance, height, speed over the last 10
fields, the pitch of the first pass in the air), the peak over the lip, the flight's length and
time (50 fields per second), the landing height, fall word and pitch, and "frozen" when the speed
stops changing after the landing (a crash)."""
import struct, sys, math
def rows(run):
    b = open(run + '/steps.bin', 'rb').read(); R = []
    for i in range(0, len(b), 92):
        f, c = struct.unpack_from('>II', b, i)
        g = lambda a, t: struct.unpack_from('>' + t, b, i + 8 + a - 0x98fc)[0]
        R.append(dict(f=f, x=g(0x98fc, 'i') / 8 * .1791, y=g(0x9900, 'i') / 8 * .1791, z=g(0x9904, 'i') / 8 * .1791,
                      m=g(0x9910, 'B'), p=g(0x994c, 'h') / 4, fall=g(0x990e, 'h'), v=g(0x9928, 'h')))
    return R
for run in sys.argv[1:]:
    R = rows(run); d = 0
    for k in range(1, len(R)): R[k]['d'] = R[k-1].get('d', 0) + math.hypot(R[k]['x'] - R[k-1]['x'], R[k]['z'] - R[k-1]['z'])
    R[0]['d'] = 0
    lip = next((k for k in range(len(R)) if R[k]['m'] == 0 and R[k]['d'] > 400), None)
    if lip is None: print(run, 'no flight'); continue
    L = R[lip - 1]
    a = next(k for k in range(lip, 0, -1) if R[lip-1]['f'] - R[k]['f'] >= 10)
    spd = (L['d'] - R[a]['d']) / ((L["f"] - R[a]["f"]) / 50)
    land = next((k for k in range(lip, len(R)) if R[k]['m'] in (3, 15) and R[k]['d'] > L['d'] + 20), None)
    T = R[land]; t = (T["f"] - L["f"]) / 50
    peak = max(r['y'] for r in R[lip:land])
    stop = next((r['f'] for r in R[land:land+60] if r['v'] == R[land+10]['v'] and r['f'] > T['f'] + 4 and all(q['v'] == r['v'] for q in R[R.index(r):R.index(r)+15])), None)
    print('%-34s lip %5.0f ft y %4.1f %5.1f ft/s pitch %5.1f -> peak +%4.1f ft, flew %5.0f ft %.2f s, lands y %4.1f fall %3d pitch %6.1f %s' % (
        run.split('prof/')[1], L['d'], L['y'], spd, R[lip]['p'], peak - L['y'], T['d'] - L['d'], t, T['y'], R[land-1]['fall'], T['p'], 'frozen' if stop else ''))
