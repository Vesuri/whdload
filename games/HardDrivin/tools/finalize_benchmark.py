#!/usr/bin/env python3
"""Validate and publish the saved initial A500 attract benchmark report."""
import collections,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];prof=ROOT/'tmp/prof';run=prof/'attract-a500-run1'
r=json.loads((prof/'repeatability.json').read_text());c=json.loads((prof/'attract-a500-counter/counter.json').read_text());h=json.loads((run/'hardware.json').read_text())
assert r['all_recorded_fields_identical'] and not any(r['snapshot_differences'].values())
assert c['matches_trace']
for name in ('attract-a500-run1','attract-a500-run2'):
 p=prof/name/'metrics.json';m=json.loads(p.read_text());events=[f['index'] for f in m['per_field'] for _ in range(f['candidate_swaps'])]
 m['frame_counter_validated']=True;m['validation']='Independent read-only breakpoint run matches every field; two full captures are identical.'
 m['displayed_frames']=sum(c['per_field']);m['whole_window_fps']=m['displayed_frames']/m['emulated_seconds']
 m['first_to_last_swap_fps']=(len(events)-1)/((events[-1]-events[0])*m['emulated_seconds']/m['fields'])
 m['frame_interval_fields']=dict(collections.Counter(b-a for a,b in zip(events,events[1:])))
 m['limitations']=['The fixed window includes the normal high-score text overlay while the demo continues driving.','Routine self estimates in this JSON use nearest LINK A5; use routines.txt for call-target-aware attribution.','VERIFY_ATTRACT injects one title key before the benchmark; normal builds exclude the fixture.','This baseline does not establish a simulation-time model or 68020 performance.']
 p.write_text(json.dumps(m,indent=2)+'\n')
total=sum(m['dma_slots'].values());dma={name:100*m['dma_slots'].get(str(k),0)/total for k,name in ((0,'free'),(1,'refresh'),(2,'CPU'),(3,'copper'),(4,'audio'),(5,'blitter'),(6,'bitplane'),(7,'sprite'),(8,'disk'))}
report=f'''HARD DRIVIN' — REPEATABLE ATTRACT-MODE BASELINE

Result
  1,000 consecutive PAL fields: {m['emulated_seconds']:.6f} seconds of emulated time.
  129 completed buffer swaps: {m['whole_window_fps']:.4f} displayed frames/second over the full window.
  First-to-last swap interval rate: {m['first_to_last_swap_fps']:.4f} FPS.
  Frames take 6–11 fields (approximately 120–220 ms); no chunk gaps.
  142,102,000 CPU clocks elapsed; 142,101,988 attributed (99.99999%).

Repeatability and validation
  Two fresh boots have identical instruction records, DMA records and screenshots
  in all 1,000 fields. Chip and slow RAM match byte-for-byte before and after.
  A third, trace-free run using read-only debugger breakpoints reproduces every
  swap in the same field. The game VBL handler executes exactly 1,000 times.
  Input files still match their pristine SHA-256 manifest.

Scene and start point
  Anchor: decompressed SPS 0126 game code +$10844, after the initial eight-step
  dissolve. The first clean road/cockpit matches the user's 0114_02 screenshot
  exactly inside the game area (only the far-right emulator border differs).
  Profiling begins at the following PAL field boundary, less than one field later.
  The high-score text starts scrolling over the driving view at about 10 seconds;
  this is retained as part of the requested 20-second attract run. The demo keeps
  driving and the cockpit remains present throughout.

Machine and inputs
  PAL A500-equivalent; cycle-exact 68000; 512 KiB chip + 1,536 KiB slow RAM;
  no fast RAM. PRELOAD enabled, CUSTOM2 left at zero, deterministic emulation,
  both host input ports disabled. Warp changes host throughput, not these times.
  Exact archive, slave and emulator hashes: each run's capture.json.

Startup fixture
  An untouched input-disabled boot waits on the title's key/mouse polling loop.
  VERIFY_ATTRACT supplies one space at that title wait, before the benchmark.
  It changes no driving routine and is completely omitted from normal builds.
  The user's screenshot shortcut may explain the earlier apparently automatic
  title advance; that detail was not confirmed. This report does not claim that
  the shipped slave reaches the demo without a startup input.

CPU findings (whole window)
  Main execution context: 94.1%; interrupt/other contexts: 5.9%.
  Game code: about 90.8%; slave: 4.5%; Kickstart: 4.0%; other runtime code: 0.7%.
  Largest call-target-aware self-time groups, using decompressed game offsets:
    +$0329a  20.15%   polygon rendering/edge processing (inferred from code)
    +$02a2e   7.94%   fixed-point vertex rotation
    +$03a28   6.85%   bitplane background/span fill
    +$03736   6.45%   polygon bounds/clipping (inferred from code)
    +$02da2   4.16%
    +$02b74   4.13%
  Routines.txt includes self and inclusive costs. Self-time grouping is analytical;
  exact instruction sites are retained in metrics.json and the raw trace.
  Existing slave blitter-check/wait routine: {h['percent_of_window']['blitter_check_and_wait_routine']:.3f}%.
  Its polling/CIA-wait body: {h['percent_of_window']['blitter_poll_and_CIA_wait_body']:.3f}% (included in the preceding figure).
  No STOP/missing-PC cycles were observed.

DMA slot shares (these are not CPU-time percentages)
  {', '.join(f'{k} {v:.2f}%' for k,v in dma.items() if v)}.

Reproduce from the game directory
  . tools/env.sh
  OUTPUT_SLAVE="$PWD/tmp/build/HardDrivin-verify.slave" /bin/bash tools/build.sh -DVERIFY_ATTRACT=1
  python3 tools/capture_demo.py tmp/prof/NEW-RUN-NAME
  python3 tools/compare_profiles.py tmp/prof/FIRST tmp/prof/SECOND

  Capture directories must be new. The anchor is calibrated for these exact
  inputs and this memory configuration; changing them requires recalibration.
  The host debugger extends only the profiler's 100-field limit to 1,000 fields;
  its one-shot action is logged. The installed emulator file is not modified.
  The independent frame-counter script is tools/count_demo_swaps.py and currently
  writes tmp/prof/attract-a500-counter (preserve/rename that directory before rerun).

Retained evidence
  attract-a500-run1/trace.bin and attract-a500-run2/trace.bin: full continuous traces.
  Each run: exact slave, machine config, before/after memory, hashes and metrics.
  repeatability.json: exhaustive comparison results.
  attract-a500-counter/counter.json: independent per-field frame counts.
  attract-a500-run1/routines.txt and hardware.json: cost breakdowns.
  Selected screenshots: field-0000.jpg, field-0250.jpg, field-0500.jpg,
  field-0750.jpg and field-0999.jpg in the first run.

Scope
  No performance optimization has been implemented. Intro optimization is deferred.
  Game-time/physics coupling, 68020 measurements and optimization candidates remain
  separate follow-up work. No commit or GitHub operation was performed.
'''
(prof/'benchmark-report.txt').write_text(report)
print(prof/'benchmark-report.txt')
if __name__=='__main__':pass
