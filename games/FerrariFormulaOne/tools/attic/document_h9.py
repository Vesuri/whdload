from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parents[1];repo=r.parents[1];v=json.loads((r/'manifest/render-h9-validation.json').read_text());assert v['status']=='passed';fps=v['fps'];tr=v['traces'];a=tr['control']['analysis']['mean_after_wait_ms'];b=tr['candidate']['analysis']['mean_after_wait_ms']
rows=[]
for key,x in fps.items():
 p,s,arm=key.split('/');hist=', '.join(f'{n} × {k}' for k,n in x['histogram'].items());rows.append(f"| {p} | {s} | {arm} | {x['fps']:.5f} | {x['mean_ms']:.3f} | {x['p95_ms']:.3f} | {hist} |")
report=f'''
## H9 — Exact road-fill narrowing (accepted, 2026-10-15)

The fine path replaces native `$6abc6` with a bounded, banded version of its
same two descending CD exclusive fills. All native relocation records identify
one caller, the main-road call at `$6b8be`; the mirrors do not use this entry.
The 68000 and chip-only 020 payloads remain byte-identical. CUSTOM2 remains
default-off, and RC2 is unchanged.

### Exact bounds and implementation

The captures revise the original geometry-based estimate: one road plane has
roughly 50 empty lower rows, while the other usually reaches both screen edges.
`RenderFill.s` therefore reads the actual pre-fill Chip words rather than
inferring a potentially unsafe bound from projected endpoints. Each band has
at most 16 rows. It scans right-to-left in longwords, only outside the widest
bound already found in that band, and keeps the left boundary at column zero.
A completely empty band needs no blit. Nonempty bands use the original minterm,
exclusive-fill mode, zero initial carry, masks and 48-byte row stride, with a
narrower width and corresponding descending modulo.

Keeping the left edge is deliberate: skipped right-hand words are all zero,
so carry is still zero when entering the shortened row. Odd-parity rows retain
the native fill all the way to the left edge. Each row resets carry, so band
boundaries do not change the result. No closed-polygon assumption is needed.
Rows outside the native fill range are untouched. Extents outside 1–200 rows
retain the original native routine.

The native WaitBlit synchronizes preceding line writes before any scan.
Scanning a subsequent disjoint band can overlap the preceding fill; register
changes wait for completion, and both plane boundaries and the return are
synchronized. No H12-style WaitBlit shortcut or priority change is included.
The existing cache policy is unchanged; these are reads from the original Chip
DMA planes. Code lives in the public fine payload; no new allocation or
persistent workspace is needed. The immutable equal-layout preset changes one
byte only. The new entry uses the existing patch ledger for restoration.

### Reduced acceptance

- The reference fill model passes on 16 captured pre-fill planes and 450
  directed cases, including zero, dense, sparse, odd-parity and edge-bit rows,
  partial bands and heights 1–200. It compares all 200 rows, including those
  outside the fill. Captured narrowed work is 28,428 versus 39,792 words
  (28.56% fewer); this is a DMA-word reduction, not a whole-frame speedup.
- 100 updates have identical game state and private physics fractions on
  020+Fast. All 30 completed RGB frames in each of normal, solo, grid and
  dense match exactly. The previously accepted test-only scanout hold is used
  in both image arms; production B8-PAL behavior is unchanged.
- The 60-second elapsed check has {v['elapsed_error_percent']:.6f}% error,
  below 0.25%. Native 040 pause/resume, tow, pit/menu and fresh-session re-entry
  pass; all {v['lifecycle']['ledger_restored_words']} owned patch words restore. The H9 entry is
  explicitly verified on takeover and after reload. INTENA ownership/restoration
  remains exact. A deliberately wrong H9 signature exits before its hook is
  installed. Controlled CUSTOM2=0 is exact on 020+Fast with both CUSTOM1 values.
- Matched 040 cycle-exact traces retain empty graphics queues, no BLIT-enabled
  observations and DMA entirely in Chip (highest address `$59fb0`). An independent
  production rebuild is byte-identical. This is the representative reduced
  scope, not a repeated CPU-by-scene qualification matrix.

### Measured performance

300 complete presentation intervals per run, warp off after warm-up. BCE means
cycle-exact blitter. Mean/p95 are milliseconds; histograms count PAL fields per
interval. Controls differ only at the H9 preset. The 060 row is candidate-only,
not a fresh matched A/B; no new 030 or default-blitter claim is made.

| Profile | Scene | Arm | FPS | Mean ms | p95 ms | Interval histogram |
|---|---|---|---:|---:|---:|---|
'''+ '\n'.join(rows)+f'''

Both 020 workloads and 040 dense pass mean/p95 no-regression. Dense 040 improves
12.03868 → 12.46971 FPS; 040/060 grid remains 19.96816 FPS. The matched 30-field
040 grid trace reduces post-wait draw **{a:.5f} → {b:.5f} ms**, a
**{a-b:.5f} ms** saving. Its inclusive road call falls 11.120 → 10.414 ms.
Whole-window CD-fill activity falls about 2.039 → 1.465 ms per field, but the
CPU scan and extra setup consume much of that saving. Per-field DMA and
per-draw call measurements are different denominators and are not additive.
The original 1.5–3 ms whole-frame saving estimate was not achieved.

H6c's 25 FPS target remains unmet: grid still has 150 two-field and 150
three-field intervals. H10 is next, followed by H13/H11 only if needed;
H12 still requires explicit approval. Stop further optimizations once the
common-scene two-field gate passes. B8-PAL cleanup, successor packaging, human
full races and real hardware remain separate/deferred work.

Production slave: {v['build']['candidate_bytes']:,} bytes, SHA256
`{v['build']['candidate_sha256']}`.
Local evidence: `tmp/dev/manifest/render-h9-validation.json`, build/model/caller
audits, `render-h9-checks.json`, matched `hi25-profile-040-40-bce-h9-grid-*`
compressed traces and the H9 capture/model/check tools. RC2 SHA256 remains
`{v['build']['rc2_sha256']}`.
'''
p=repo/'Games/FerrariFormulaOne/RENDERING_PLAN.md';s=p.read_text();assert '\n## H9 — Exact road-fill narrowing (accepted,' not in s;p.write_text(s.replace('**H9 — Exact road-fill narrowing (all CPUs).**','**H9 — Exact road-fill narrowing (fine path; see H8 scope and H9 closure).**')+report)
p=repo/'Games/FerrariFormulaOne/README.md';s=p.read_text().replace('The current source independently builds to 264,520 bytes','The H5 source independently builds to 264,520 bytes').replace('H8 is next; H12 still needs explicit approval.','H8 ranked the remaining costs. H9 now narrows the road fills exactly and passes\nthe reduced state/image/elapsed/lifecycle gates. On cycle-exact 040, dense improves\n12.04 → 12.47 FPS; grid remains 19.97 FPS with a 0.34 ms draw-time saving.\nH10 is next; H12 still needs explicit approval. The H9 source reproducibly builds\nto 265,512 bytes, SHA256\n`'+v['build']['candidate_sha256']+'`.');p.write_text(s)
p=r/'manifest/project.json';s=json.loads(p.read_text());s['next_steps'][0]='H9 accepted: exact right-edge road-fill bands; reduced state/RGB/elapsed/lifecycle/default-off and representative FPS gates pass. Next H10, then H13/H11 if needed; H12 needs explicit approval. Keep reduced representative validation, not a Cartesian matrix.';s['rendering_h9']='tmp/dev/manifest/render-h9-validation.json';s['rendering_h9_status']='Passed in reduced emulator scope. 040BCE grid post-wait 40.24848 ->39.90844 ms; dense12.03868 ->12.46971FPS;020 normal/dense no regression. Coarse payloads/RC2 unchanged, default-off.';p.write_text(json.dumps(s,indent=2)+'\n')
p=r/'manifest/hi25-profile.json';s=json.loads(p.read_text());s['h9_validation']='tmp/dev/manifest/render-h9-validation.json';p.write_text(json.dumps(s,indent=2)+'\n')
p=r/'docs/HI25_PLAN.md';p.write_text(p.read_text().replace('**H9 — Exact road-fill narrowing (all CPUs).**','**H9 — Exact road-fill narrowing (fine path; see H8 scope and H9 closure).**')+'\n## H9 closure\n\nH9 passed the reduced representative gates. Exact right-edge 16-row bands\nand empty-band elision avoid any polygon/parity assumption. Matched 040-bce\ngrid post-wait40.24848 ->39.90844ms; dense12.03868 ->12.46971FPS; grid remains\n19.96816FPS on040/060. The1.5–3ms estimate was not met. 020 normal/dense do not\nregress. See tracked RENDERING_PLAN.md and manifest/render-h9-validation.json.\nNext H10; H12 remains approval-gated. RC2 unchanged.\n')
print('Documented H9 acceptance')
