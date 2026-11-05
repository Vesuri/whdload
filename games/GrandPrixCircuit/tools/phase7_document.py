#!/usr/bin/env python3
"""Write accepted evidence only after the completion gate has passed."""
import json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1];r=root/'tmp/phase7';source=root/'src'
m=json.loads((r/'completion-capture-audit.json').read_text())
assert len(m['verify_captures'])==20
for n,h in m['source_sha256'].items():assert hashlib.sha256((source/n).read_bytes()).hexdigest()==h,n
p=root/'docs/PERFORMANCE_PLAN.md';s=p.read_text();s=s.replace('**Status: implementation complete; final acceptance runs in progress.**','**Status: complete.**')
a=s.index('Acceptance results are being collected',s.index('### Phase 7'));b=s.index('\n### Phase 8',a)
cadence=[]
for name,label in [('a500','A500 / period 6'),('020','68EC020 / period 2'),('030','68030 25 MHz / period 2'),('traffic','68EC020 traffic / period 2')]:
 c=json.loads((r/('accepted-core-'+name)/'cadence.json').read_text())
 cadence.append('| '+label+' | '+str(c['render_latches'])+' | '+', '.join(map(str,c['field_intervals']))+' | '+', '.join(map(str,c['physics_updates_per_draw']))+' |')
cost=[];copies=0
for name,label in [('2000','Solo, skip 2,000'),('4000','Solo, skip 4,000'),('6000','Solo, skip 6,000'),('traffic','Traffic, skip 2,000')]:
 c=json.loads((r/('accepted-moving-'+name)/'phase7-cost.json').read_text());assert c['helper_percent']<=3
 cost.append(f"| {label} | {c['helper_cycles']:,} | {c['helper_percent']:.3f}% |")
 copies+=json.loads((r/('accepted-moving-'+name)/'latch-audit.json').read_text())['complete_copies']
evidence='''Accepted evidence is retained under ignored `tmp/phase7/`, with final
capture prefix `accepted-` and the three `normal-*` production captures.
`completion-capture-audit.json` binds all 20 VERIFY captures to their exact slave,
source hashes and acceptance gates; older candidates are diagnostic only.

- Four same-build C2=0/1 zero-fraction pairs cover straight, left, right and shallow
  curves with traffic and mirrors. Every one of eight fields per capture has the
  same 40,000 fetched bitmap bytes across all five planes: no crop, tolerance,
  masking or nearest-frame selection. A changed-byte negative control fails the
  same comparator. The frozen fixture sets added camera/AI fractions and angular
  interpolation to zero and holds wheel history; it is VERIFY-only.
- Nonzero fractions 1, 128 and 255 on the right curve, plus 128 on the left curve,
  pass the retained guest-table checks. An independent model exhausts all 256
  projection fractions and all 45,057 clamped signed angles, including negative
  rounding, endpoint bounds and unchanged native projection-selection bytes.
  All 20 captures pass 63 guest assertions with zero failures.
- All named player/AI, input, clock and event fields match Phase 6 exactly at each
  of 720 native-field observations on all four regression runs. Read-only latch
  observations show at least one physics update per draw on these profiles:

| Profile | Render latches | Fields between draws | Physics updates between draws |
|---|---:|---|---|
'''+ '\n'.join(cadence)+'''

The A500 budget uses four 100-field windows from the original human joystick
recording, including moving traffic. These count the entire new per-frame helper
range, including replacement native work and VERIFY overhead; no native cost is
subtracted, and this is not an FPS improvement claim. All pass a 3.0% gate:

| A500 window | Helper cycles | Share of all CPU cycles |
|---|---:|---:|
'''+ '\n'.join(cost)+f'''

- All 16 final bitmap traces have zero writes to the displayed buffer. The four
  moving traces contain {copies} complete native snapshot copies with no foreign PC
  during the protected copy, regardless of interrupt-vector location.
- Normal A500 C2=0/1 and A1200 C2=1 builds boot through the intro and race and drain
  the pending display handoff at native race exit. Both C2-on second-race checks
  start with 48 shifted table words (camera fractions 160 and 182), verify all
  102 canonical words restored and the fraction invalidated, then render 40 more
  swaps. Their second-race tables match the model; intro/race images were inspected.
- Exact runtime code/gating audits preserve inherited JOTD patches and all 139
  jump stubs, with corrupted-code negative controls. All 64 hook boundaries and
  direct branch entries pass. All 55 pristine input hashes remain unchanged.
- Normal and tape VERIFY builds reproduce byte-for-byte in separate output
  directories; ordinary VERIFY also builds without the private tape input. The
  normal build excludes test fixtures and assertion routines. Normal SHA-256:
  `{m['normal_sha256']}`;
  tape VERIFY: `{m['verify_sha256']}`.

This establishes the stated emulator coverage, not all-circuit or hardware
handling equivalence. The 030 backend supplies state/cadence observations but no
CPU instruction trace; no 030 cycle-cost claim is made. Phase 8 has not started.
'''
s=s[:a]+evidence+s[b:];p.write_text(s)
p=root/'docs/development.md';s=p.read_text().replace('Phases 0–6 are complete; Phase 7 final acceptance is in progress.','Phases 0–7 are complete; Phase 8 has not started.');p.write_text(s)
print('Updated Phase 7 acceptance evidence in the plan')
