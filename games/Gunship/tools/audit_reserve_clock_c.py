"""Audit fixed-collective live captures against native depletion and clock rules."""
from pathlib import Path
import json
root = Path(__file__).resolve().parents[1] / 'tmp/c'
results = []
for video in ('pal', 'ntsc'):
    for cpu in ('000', '020', '030', '040', '060'):
        path = root / f'anchor-draw-probe-{video}-{cpu}'
        timing = json.loads((path / 'actual-rate.json').read_text())
        rows = []
        events = []
        for t in timing['rows']:
            w = t['world']
            p = (path / f'world-{w}/h6.bin').read_bytes()[0x3b88:0x3b88+86]
            word = lambda o: int.from_bytes(p[o:o+2], 'big')
            assert len(p) == 86
            assert word(12) == w
            # This fixture has both engines, fixed collective and no damage.
            # Refuse to apply this simplified native formula to other states.
            assert p[0x39] == 40 and p[0x42] == 28 and word(14) == 0
            assert word(4) > 40 and word(6) > 120
            r = dict(world=w, clock_seconds=word(12)//3,
                     reserves=[word(4),word(6)], native=t['native'], logical=t['logical'])
            if rows:
                prev=rows[-1]
                assert w == prev['world']+1
                amount = [40,120] if w % 16 == 0 else [0,0]
                assert [a-b for a,b in zip(prev['reserves'],r['reserves'])] == amount
                assert r['logical']-prev['logical'] in (t['rate']//3,(t['rate']+2)//3)
                if w % 16 == 0:
                    events.append(r)
            rows.append(r)
        assert [r['world'] for r in rows] == list(range(20,81))
        assert [r['world'] for r in events] == [32,48,64,80]
        assert rows[-1]['clock_seconds']-rows[0]['clock_seconds'] == 20
        assert rows[-1]['logical']-rows[0]['logical'] == 20*t['rate']
        result=dict(video=video,cpu=cpu,captures=len(rows),transitions=len(rows)-1,
                    depletion_worlds=[r['world'] for r in events],amounts=[40,120],
                    game_clock_elapsed_seconds=20,
                    native_elapsed_seconds=timing['native_fields']/t['rate'],
                    reserve_event_intervals_seconds=[(b['native']-a['native'])/t['rate'] for a,b in zip(events,events[1:])])
        results.append(result)
report=dict(scope='Fixed collective, two running engines, no damage, worlds 20..80. Clock conversion is the previously verified native tick/3 rule; this does not observe clock UI or minute rollover. Native completion timestamps are distinct from logical deadlines.',runs=results)
(root/'reserve-clock-live-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
