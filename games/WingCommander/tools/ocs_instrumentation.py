"""OCS native observer adapter for the shared WCFS/WCDS validation interface.

This exports host observations, not guest-recorder captures. Actual DMA remains
independent of the publication PC. Source provenance is mandatory in the report.
"""
from bisect import bisect_right
from collections import Counter
import copy
import struct
from frame_schema import encode_frames, decode_frames, encode_display, decode_display, display_order
from ocs_baseline_report import parse, measure, neutrality, negative_controls
from ocs_boot_compare import memory_contract, pixels
from native_validation import state
from variants import ocs

# OCS hunk-0 offsets (file offsets add 0x2c). Do not infer an OCS timer from CD32.
EVENTS = {('S', 0x2be): 2, ('P', 0x2dc): 3, ('S', 0x2e6): 4,
          ('P', 0x3260a): 17, ('P', 0x32626): 9,
          ('P', 0x329e4): 12, ('P', 0x32e02): 13, ('P', 0x33aa8): 18}


def export_window(root, label, out, rows=None):
    rows = parse(root/(label+'-events.txt')) if rows is None else rows
    measured = measure(rows)  # Reject clock, source-lifetime and DMA disagreement first.
    begin = next(r for r in rows if r[0] == 'B')
    edges = [begin[1]]+[r[1] for r in rows if r[0] == 'F']
    def stamp(cycles):
        field = bisect_right(edges, cycles)-1
        if not 0 <= field < len(edges)-1:
            raise ValueError('event outside frozen field window')
        return field, (cycles-edges[field])//(227*512)
    events = [(EVENTS[(r[0], r[2])], *stamp(r[1])) for r in rows
              if r[0] in ('S', 'P') and (r[0], r[2]) in EVENTS]
    if any(b[1:] < a[1:] for a, b in zip(events, events[1:])):
        raise ValueError('observer events go backwards')
    raw = encode_frames(50, events)
    if decode_frames(raw)[2] != events:
        raise ValueError('frame schema roundtrip differs')
    frame_bytes = raw
    # Validate the actual Chip allocations, then check every DMA fetch belongs
    # to the named plane-0 range, not merely a plausible alternating index.
    code = (root/(label+'-h0.bin')).read_bytes()
    plane = int.from_bytes(code[0x331d2:0x331d4], 'big')
    buffers = struct.unpack_from('>II', code, 0x331c0)
    dma = [r for r in rows if r[0] == 'D']
    if any(d[3] not in (0, 1) or not buffers[d[3]] <= d[4] < buffers[d[3]]+plane for d in dma):
        raise ValueError('display DMA outside owned plane')
    pubs = [r for r in rows if r[0] == 'P' and r[2] == 0x33aa8]
    # Final blitter completion must precede publication. The very first event
    # may represent work already pending when the field window began.
    ready = 0
    ready_index = None
    completion_seen = False
    for r in rows:
        if r[0] != 'P':
            continue
        if r[2] == 0x32e02:
            ready += 1; completion_seen = True
            ready_index = r[5]
            if ready > 1:
                raise ValueError('completed native image overwritten before publication')
        elif r[2] == 0x33aa8:
            if not ready and completion_seen:
                raise ValueError('publication without completed blitter image')
            if ready:
                if r[5] != ready_index:
                    raise ValueError('publication uses a different completed buffer')
                ready -= 1
            else:
                completion_seen = True
    shown, used = [], set()
    for a, b in zip(dma, dma[1:]):
        if a[3] == b[3]:
            continue
        candidates = [(i, p) for i, p in enumerate(pubs)
                      if i not in used and p[1] < b[1] and p[5] == b[3]]
        if len(candidates) != 1:
            raise ValueError('missing or duplicate publication before display')
        i, pub = candidates[0]; used.add(i)
        copper = pub[3]
        if copper & 1 or not 0 < copper < 0x80000:
            raise ValueError('Copper publication is not aligned Chip RAM')
        shown.append((*stamp(b[1]), b[3], buffers[b[3]], copper))
    display_order(shown)
    raw = encode_display(50, shown)
    if decode_display(raw)[2] != shown:
        raise ValueError('display schema roundtrip differs')
    display_bytes = raw
    counts = Counter(e for e, f, v in events)
    field_rows = [r for r in rows if r[0] == 'F']
    draw_counter_delta = (field_rows[-1][4]-begin[6]) & 65535
    if counts[4] != draw_counter_delta:
        raise ValueError('draw entries/native draw counter disagree')
    # A field window can begin after draw entry or end before completion.
    # Keep both edges explicit instead of forcing draw and conversion equality.
    draw_events = [(e, f, v) for e, f, v in events if e in (4, 17)]
    pending = 1 if draw_events and draw_events[0][0] == 17 else 0
    initial = pending
    for event, _, _ in draw_events:
        pending += 1 if event == 4 else -1
        if pending not in (0, 1):
            raise ValueError('overlapping or unmatched native drawing')
    if counts[3] != measured['world_updates'] or len(shown) != measured['displayed_changes']:
        raise ValueError('normalised counters disagree')
    (out/(label+'-framestats.bin')).write_bytes(frame_bytes)
    (out/(label+'-displaystats.bin')).write_bytes(display_bytes)
    return dict(source='read-only OCS host observer; not guest WCFS',
                clock='independent field-edge/colour-clock samples',
                world_ticks=counts[3], draw_entries=counts[4],
                rendered_pictures=counts[17], published_pictures=counts[18],
                actually_displayed_pictures=len(shown),
                drawing_at_window_begin=initial, drawing_at_window_end=pending,
                publication_pending_at_end=measured['boundary_pending'],
                memory=memory_contract(root, label), negative_controls=negative_controls(rows))


def check(on, off, out):
    control = neutrality(on, off)
    checkpoints = ('origin', 'title', 'credits', 'menu', 'simulator', 'name', 'asteroids', 'fire')
    for label in checkpoints:
        state('ocs', *[[(root/f'{label}-h{n}.bin').read_bytes() for n in range(len(ocs.HUNKS))]
                      for root in (on, off)])
    windows = {label: export_window(on, label, out) for label in ('asteroids', 'fire')}
    rejected = []
    original = parse(on/'asteroids-events.txt')
    for name in ('DMA address outside plane', 'Fast Copper pointer', 'wrong drawing count', 'missing render completion', 'wrong completed buffer'):
        bad = copy.deepcopy(original)
        if name == 'DMA address outside plane':
            next(r for r in bad if r[0] == 'D')[4] = 0x200000
        elif name == 'Fast Copper pointer':
            next(r for r in bad if r[0] == 'P' and r[2] == 0x33aa8)[3] = 0x200000
        elif name == 'wrong drawing count':
            next(r for r in reversed(bad) if r[0] == 'F')[4] += 1
        elif name == 'wrong completed buffer':
            next(r for r in bad if r[0] == 'P' and r[2] == 0x32e02)[5] ^= 1
        else:
            bad.remove([r for r in bad if r[0] == 'P' and r[2] == 0x3260a][2])
        try:
            export_window(on, 'asteroids', out, bad)
        except ValueError:
            rejected.append(name)
        else:
            raise AssertionError('adapter accepted '+name)
    return dict(adapter_negative_controls=rejected, variant='ocs', passed=True, windows=windows, control=control,
                native_pixels=pixels(on), observer_overhead=dict(
                    emulated_cycle_delta=0, method='exact matched field edges and native state/pixels',
                    scope='read-only host observer; host wall time and guest-recorder cost not measured'))
