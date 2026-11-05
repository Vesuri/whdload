from pathlib import Path
import json
r=Path(__file__).resolve().parents[1];g=r.parents[1]/'Games/FerrariFormulaOne';v=json.loads((r/'manifest/render-h10-validation.json').read_text());assert v['status']=='passed';b=v['build'];t=v['traces'];micro=v['microbench'];fps=v['fps']
lines=[]
for key,x in fps.items():
 hist=', '.join(f'{n} × {k}' for k,n in x['histogram'].items());lines.append(f"| {key.replace('/',' / ')} | {x['fps']:.5f} | {x['mean_ms']:.5f} | {x['p95_ms']:.5f} | {hist} |")
text=f'''

## H10 — CPU background clears on 030+ (accepted, 2026-10-15)

H10 replaces the six solid D-only background fills inside `$6b050` with
CPU stores on WHDLoad-detected 030/040/060 + Fast. The native three-plane
loops retain their destinations, colours and geometry: the lower band starts
at row `100-h`, spans `100+h` rows, and sets planes 0/1 to zero and plane 2
to ones; the upper 17-row band starts at row 58 and sets plane 0 to ones and
planes 1/2 to zero. Each row remains 24 words / 48 bytes.

`RenderClear.s` patches only the two BLTSIZE writes at `$6b0e4` and `$6b138`.
Twelve-register MOVEM stores write each complete row. Both wrappers preserve
all CPU registers and reproduce the displaced MOVE's CCR, including X.
Unexpected lower-band heights (zero/1024 or above 200) retain the native
BLTSIZE write. The original ownership, WaitBlit calls and geometry calculations
stay in place; this is not an H1/H12 wait shortcut. No extra DMA allocation,
inter-frame cache, mutable workspace or interrupt/priority policy is added.

The installer reads the existing WHDLoad ATTNFLAGS result through a generated
host-symbol offset (`$8c`: 030/040/060). Guest Exec is not used. 020+Fast keeps
the native clears, and the 68000/chip-only 020 payloads are byte-identical.
The equal-layout control validates the same native signatures and leaves both
writes intact; its only binary difference is `FF1RenderClearControl` at byte
{b['only_difference'][0]}. The preset is outside lifecycle reset ranges.
The public patch ledger owns all seven new patch words and restores them on
native exit before re-binding them on reload. CUSTOM2 remains default-off.

### Required CPU-store benchmarks

Before selecting the implementation, three matched grid microbenchmarks ran
at the native clear phase with cycle-exact blitting, 12 traced fields per arm.
The 030 trace uses 68EC030 because the full-MMU loop lacks instruction records.
Both live hook operands were checked before capture. The initial diagnostic
was outside the binding scan and did not install; those results were discarded
and are not performance evidence. The corrected diagnostic produced:

| Profile | Control post-wait ms | CPU-store post-wait ms | Saving ms |
| --- | ---: | ---: | ---: |
'''
for p,x in micro['profiles'].items():text+=f"| {p} | {x['control']['post_wait_ms']:.5f} | {x['candidate']['post_wait_ms']:.5f} | {x['post_wait_saved_ms']:.5f} |\n"
text+=f'''
The inclusive background call falls from 5.084 to 2.552 ms on EC030,
5.267 to 2.623 ms on 040, and 5.225 to 2.887 ms on 060. CPU Chip-store
transactions and patterns are verified in all three candidate traces.
These short diagnostic traces select CPU-only clears; a concurrent CPU/blitter
variant was not needed or accepted. They are not the final production timing
claim: production adds explicit CCR preservation and the height guard. CPU
instruction/cache charging remains emulator-specific. No hardware speed or
CPU-ranking claim is made.

### Reduced representative acceptance

- 480 native-blitter versus CPU primitive cases pass: all 32 CCR inputs,
  all three plane colours, lower heights 1/17/100/200 and the 17-row upper
  band. Every complete 9,600-byte plane, including untouched pixels, agrees;
  CCR, destination pointer and the D0 size word are checked.
- 040 cycle-exact passes 100 exact state/private-fraction updates and 30
  complete RGB frames each for normal, solo, grid and dense. This CPU carries
  the detailed correctness tests because 020 deliberately does not install H10.
  The accepted H7 three-field test-only scanout hold is retained; production's
  inherited B8-PAL pulse is unchanged, with no pixel masks or timing tolerance.
- 60 simulated seconds on 040 cycle-exact differ from elapsed time by
  {v['elapsed_error_percent']:.6f}% (gate <=0.25%).
- Actual 040 pause/resume, tow, pit/menu and session re-entry pass; all
  {v['lifecycle']['ledger_restored_words']} owned patch words restore. Both new hooks are verified at takeover
  and after re-entry. A deliberately damaged clear signature aborts before
  either clear hook is installed.
- Controlled CUSTOM2=0 remains legacy-exact on 020+Fast with both CUSTOM1
  settings; static coarse-payload identity covers the unchanged coarse code.
  This keeps the user-reduced representative scope, not a Cartesian matrix.
- The final trace verifies CPU row patterns and actual Chip bus stores,
  with selected words outside their display-fetch intervals. DMA stays in Chip,
  graphics queues remain empty, and BLIT remains disabled during racing.

### Final 300-presentation results

Warp is off during measurement. Each row uses 300 complete intervals and
excludes window boundaries. Histograms are count × PAL fields. Only the 040
and 020 rows are fresh matched production-control pairs; 030 and 060 grid
rows are candidate-only. No new default-blitter result is claimed.

| Profile / scene / arm | FPS | Mean ms | p95 ms | Histogram |
| --- | ---: | ---: | ---: | --- |
'''+ '\n'.join(lines)+f'''

All paired mean/p95 no-regression gates pass. The 020 pair is identical because
H10 is not installed there. Dense remains within the same four-field budget.
The final matched 30-field 040 grid trace measures post-wait drawing
{t['control']['analysis']['mean_after_wait_ms']:.6f} -> {t['candidate']['analysis']['mean_after_wait_ms']:.6f} ms,
a saving of {t['control']['analysis']['mean_after_wait_ms']-t['candidate']['analysis']['mean_after_wait_ms']:.6f} ms per complete draw.
The native last clear finishes in the next caller's WaitBlit, whereas CPU
clears finish before returning. The whole post-wait draw measurement includes
that boundary; individual call totals must not double-count its saving.
The decisive all-300-two-field target is met by this 030 grid run, but 040 and
060 still have occasional three-field intervals. Normal/solo/grid on 040/060
have not all met H6c. Next is H13, then H11 only if needed; H12 still requires
explicit approval. Do not add further optimizations once H6c is proven.

The independent rebuild is byte-identical: {b['candidate_bytes']:,} bytes, SHA256
`{b['candidate_sha256']}`. RC2 SHA256 is unchanged:
`{b['rc2_sha256']}`.
B8-PAL cleanup, successor packaging, human full races and real hardware remain
separate work. No new release qualification or archive is claimed.

Local evidence: `tmp/dev/manifest/render-h10-validation.json`,
`render-h10-microbench.json`, `render-h10-checks.json`,
`render-h10-build-audit.json`, default-off manifests, native primitive/lifecycle/
fault captures and hash-verified compressed traces. The validation index also
records exact source/tool and result hashes.
'''
p=g/'RENDERING_PLAN.md';s=p.read_text();assert '## H10 — CPU background clears' not in s;p.write_text(s+text)
p=g/'README.md';s=p.read_text().replace('H10 is next; H12 still needs explicit approval. The H9 source reproducibly builds','H10 was next at that checkpoint; H12 needs explicit approval. The H9 source reproducibly builds');s+=f'''
H10 now uses CPU background stores on 030/040/060 + Fast after per-CPU
cycle-exact benchmarks. Reduced correctness, lifecycle, elapsed and no-regression
checks pass. Cycle-exact grid reaches 24.96 FPS on 030, 24.71 on 040 and 24.88
on 060; only 030 has all 300 intervals at two fields. The fresh 040 pair improves
19.97 -> 24.71 FPS; dense remains 12.48, and 020 is unchanged. H13 is next.
The {b['candidate_bytes']:,}-byte source build is independently reproducible, SHA256
`{b['candidate_sha256']}`.
See [RENDERING_PLAN.md](RENDERING_PLAN.md) for exact scopes and histograms.
CUSTOM2 stays default-off and RC2 is unchanged.
''';p.write_text(s)
p=r/'docs/HI25_PLAN.md';p.write_text(p.read_text()+f'\n## H10 closure\n\nCPU background clears passed per-CPU microbenchmarks and reduced production gates.\n040BCE grid19.96816 ->24.71307 FPS;030BCE24.96020 and060BCE24.87728 candidate-only.\n040BCE dense12.48010 unchanged;020Fast15.37590 identical. Post-wait040 saving\n{t["control"]["analysis"]["mean_after_wait_ms"]-t["candidate"]["analysis"]["mean_after_wait_ms"]:.6f} ms. See render-h10-validation.json and tracked RENDERING_PLAN.md.\nNext H13, then H11 if needed;H12 approval-gated. Common-scene H6c remains open.\n')
p=r/'manifest/project.json';x=json.loads(p.read_text());x['rendering_h10']='tmp/dev/manifest/render-h10-validation.json';x['rendering_h10_status']='Passed in reduced emulator scope: CPU solid clears on WHDLoad-selected030/040/060+Fast; per-CPU microbenchmarks,480 primitive cases,040exact state/private and4x30RGB,elapsed,lifecycle,fault,020legacybothoptions; matched040grid19.96816->24.71307FPS,dense unchanged;030grid24.96020,060grid24.87728 candidate-only. Coarse/RC2 unchanged,default-off.';x['next_steps'][0]='H10 accepted. Next H13, then H11 if needed; H12 needs explicit approval. 040/060 common-scene all-two-field H6c remains open. Keep reduced representative validation, not a Cartesian matrix.';p.write_text(json.dumps(x,indent=2)+'\n')
p=r/'manifest/hi25-profile.json';x=json.loads(p.read_text());x['h10_validation']='manifest/render-h10-validation.json';p.write_text(json.dumps(x,indent=2)+'\n')
print('H10 documentation updated')
