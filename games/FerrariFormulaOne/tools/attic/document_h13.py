from pathlib import Path
import json
r=Path(__file__).resolve().parents[1];g=r.parents[1]/'Games/FerrariFormulaOne';v=json.loads((r/'manifest/render-h13-validation.json').read_text());assert v['status']=='passed';b=v['build'];t=v['traces'];fps=v['fps'];rows=[]
for key,x in fps.items():
 hist=', '.join(f'{n} × {k}' for k,n in x['histogram'].items());rows.append(f"| {key.replace('/',' / ')} | {x['fps']:.5f} | {x['mean_ms']:.5f} | {x['p95_ms']:.5f} | {hist} |")
a=t['control']['analysis']['mean_after_wait_ms'];z=t['candidate']['analysis']['mean_after_wait_ms']
s=f'''

## H13 — Bounded CPU gauge strips (accepted, 2026-10-15)

The accepted H13 change replaces six one-row gauge background operations per
rendered frame on WHDLoad-selected 030/040/060 + Fast. `RenderGauges.s` redirects
the calls at `$6bd66` and `$6bdb6`, each executed for three adjacent rows, to a
bounded CPU bitmap operation. These draw the live 68-pixel and 40-pixel source
patterns into the cockpit bitmap. Gauge calculations, foreground bars, cockpit
cookie-cuts and mirrors retain their native code.

Both call signatures are validated before either operand changes. The original
patch ledger owns the four replacement words and restores them on driving exit;
re-entry binds the new live hunk addresses. The CPU path requires one row, three
planes, a 12-word destination stride, foreground 6/background 0, zero source
coordinates, the two native source patterns, and the cockpit plane table.
Unsigned destination and source-width bounds retain the native operation for
other cases. Source data is read live, including first/last-word masks and all
16 destination shifts. There is no cached image or persistent workspace.

The native OwnBlitter/WaitBlit boundary precedes CPU writes, and the native
conditional DisownBlitter epilogue completes the call. The private primitive
oracle compares complete destination planes and native A6/SP/CCR, and checks
that the CPU path preserves its other input registers. Native scratch-register
outputs are unused at these two call sites. Actual Chip bus writes remain within the cockpit
source planes, with no overlapping display bitplane fetch. DMA stays in Chip;
CPU code remains in public Fast memory. No wait shortcut, priority change or
H12 implementation is included. H12 was dropped separately by user decision.

### Rejected larger cockpit option

The captured cockpit mask has 446 fully opaque, 89 transparent and 149 partial
words in its 12 × 57 source rectangle; its openings and edges prevent treating
the whole image as opaque. A live-mask CPU cookie-cut was tested first, copying
opaque words and blending partial words. It passed 68 native pixel comparisons
across shifts and clipping, but the matched 040BCE short trace regressed from
36.97148 to 40.66361 ms post-wait. It is rejected and absent from production.
The bounded gauge diagnostic subsequently passed 108 native comparisons and
saved 0.68650 ms (37.47383 → 36.78733 ms) in a verified-hook 12-field pair.
Those diagnostics are separate from the final production figures below.

### Final production evidence

- 100 exact game-state updates and private fractions; live new hooks checked.
- 30 complete RGB frames each for normal, solo, grid and dense: all exact.
  The existing test-only scanout hold is retained; no pixels or tolerances change.
- {v['native_oracle_cases']} native primitive cases, including every pixel shift,
  exact surrounding pixels, CPU register preservation and native A6/SP/CCR;
  CPU execution confirmed.
- 60 simulated seconds: {v['elapsed_error_percent']:.8f}% elapsed error (gate ≤0.25%).
- Native 040 pause, tow, pit/menu and fresh session; all
  {v['lifecycle']['ledger_restored_words']} ledger words restored, new hooks present
  again after re-entry. Corrupting the second signature leaves both calls native
  and reaches the normal WHDLoad failure route.
- Controlled 020+Fast CUSTOM2=0 exact with both CUSTOM1 settings. The 68000 and
  chip-only 020 payloads remain byte-identical to H10; CUSTOM2 remains default-off.
- Independent production rebuild byte-identical: {b['candidate_bytes']} bytes,
  SHA256 `{b['candidate_sha256']}`. The equal-layout control differs only in
  immutable `FF1RenderGaugeControl`; no allocation or reset-state addition.
- Matched 30-field 040BCE grid traces: post-wait draw cost
  **{a:.6f} → {z:.6f} ms**, saving **{a-z:.6f} ms**. All trace costs retained.

Warp is disabled for every 300-complete-interval measurement. These are emulator
results, not hardware measurements. As in H10's reduced scope, 030/060 grid
runs are candidate confirmations; fresh matched pairs cover 040 grid/dense and
020 normal. No new default-blitter matrix or release archive is claimed.

| Profile / scene / arm | FPS | Mean ms | p95 ms | Interval histogram (fields) |
| --- | ---: | ---: | ---: | --- |
'''+'\n'.join(rows)+'''

H13's earlier 2–4 ms estimate was not achieved. The small accepted operation
saves measured work, but does not establish the all-300-two-field H6c target
for every common scene. H11 remains the next planned option if that target is
pursued; H12 is dropped. Human full-race playtesting and real hardware remain
deferred. B8-PAL cleanup, packaging and the RC2 archive are unchanged.

Local evidence: `tmp/dev/manifest/render-h13-validation.json`,
`render-h13-microbench.json`, `render-h13-build-audit.json`,
`render-h13-diagnostics.json` and `render-h13-capture-archive.json`.
Completed large captures are hash-verified and compressed; no rejected cockpit
kernel or test counter is part of the production source.
'''
p=g/'RENDERING_PLAN.md';text=p.read_text();assert '## H13 — Bounded CPU gauge strips' not in text;p.write_text(text+s)
p=g/'README.md';p.write_text(p.read_text()+f'''\nH13 adds bounded CPU gauge background strips on 030/040/060+Fast; native gauge\ncalculations and foreground drawing remain unchanged. Reduced exact-state,\nRGB, native primitive, elapsed, lifecycle, legacy and performance gates pass.\n040BCE grid improves {fps['040-40-bce/grid/control']['fps']:.5f} → {fps['040-40-bce/grid/candidate']['fps']:.5f} FPS.\nSee the H13 closure in [RENDERING_PLAN.md](RENDERING_PLAN.md) for scope and\nremaining H6c work. H12 is dropped; RC2 packaging remains unchanged.\n''')
p=r/'docs/HI25_PLAN.md';p.write_text(p.read_text()+f'''\n## H13 closure\n\nAccepted bounded CPU gauge strips on030/040/060+Fast; larger cockpit CPU copy\nrejected after regression. Reduced gates passed; matched040BCE post-wait\n{a:.6f}->{z:.6f}ms. See render-h13-validation.json and tracked RENDERING_PLAN.md.\nH6c remains open; nextH11 if pursued. H12 dropped;RC2 unchanged.\n''')
p=r/'manifest/project.json';x=json.loads(p.read_text());x['rendering_h13']='tmp/dev/manifest/render-h13-validation.json';x['rendering_h13_status']=f"Passed in reduced emulator scope: bounded live CPU gauge strips on030/040/060+Fast;108 native pixel/register-contract cases,100 exact updates/private fractions,4x30RGB,elapsed,lifecycle,fault,020legacy bothoptions.040BCE grid {fps['040-40-bce/grid/control']['fps']:.5f}->{fps['040-40-bce/grid/candidate']['fps']:.5f}FPS. Coarse/RC2 unchanged;default-off. Larger cockpit CPU kernel rejected.";x['next_steps'][0]='H13 accepted. H6c common-scene all-two-field target remains open; next H11 if pursued. H12 dropped by user decision. Keep reduced representative validation.';p.write_text(json.dumps(x,indent=2)+'\n')
p=r/'manifest/hi25-profile.json';x=json.loads(p.read_text());x['h13_validation']='manifest/render-h13-validation.json';p.write_text(json.dumps(x,indent=2)+'\n')
