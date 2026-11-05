from pathlib import Path
import json
r=Path(__file__).resolve().parents[1];repo=r.parents[1];v=json.loads((r/'manifest/render-h11-validation.json').read_text());assert v['status']=='passed'
assert all(v['fps'][p+'/grid/candidate']['histogram']=={'2':300} for p in ['030-50-bce','060-50-bce'])
validation=f'''- 100 exact game-state updates and private fractions.
- 30 complete RGB frames each for normal, solo, grid and dense: all exact.
- 47 native clock bitmap comparisons, including all 28 font columns,
  foreground/background alternatives and position fallbacks. Each compares
  all three complete 9,600-byte planes, including surrounding pixels.
- Trace audit: 840 prepared live-font bytes and 2,520 exact screen-byte stores;
  all preparation reads overlap an active blit. Workspace is Fast; screen writes are bounded to the seven native clock columns
  in rows 24–31, and DMA stays in Chip.
- 60 simulated seconds: {v['elapsed_error_percent']:.8f}% elapsed error (gate ≤0.25%).
- Native 040 pause, tow, pit/menu and fresh session pass; all
  {v['lifecycle']['ledger_restored_words']} patch-ledger words restored. Clock-ready state is clear at lifecycle boundaries.
- Faults injected after preparation restore both possible entry BLIT-enable
  states. No DMA can reference the prepared private bytes.
- Controlled 020+Fast CUSTOM2=0 is exact with both CUSTOM1 settings. The
  68000 and chip-only 020 payloads remain byte-identical to H13; CUSTOM2 stays default-off.
- Independent production rebuild byte-identical: {v['build']['slave_bytes']:,} bytes,
  SHA256 `{v['build']['slave_sha256']}`. Equal-layout control differs at only
  the immutable `FF1RenderOverlapControl` preset byte.'''
table=['| Profile / scene / arm | FPS | Mean ms | p95 ms | Interval histogram (fields) |','| --- | ---: | ---: | ---: | --- |']
for k,x in v['fps'].items():
 hist=', '.join(f'{n} × {f}' for f,n in x['histogram'].items());table.append(f"| {' / '.join(k.split('/'))} | {x['fps']:.5f} | {x['mean_ms']:.5f} | {x['p95_ms']:.5f} | {hist} |")
closure=(r/'tmp/h11-closure-draft.md').read_text().replace('{{VALIDATION}}',validation).replace('{{FPS}}','\n'.join(table))
p=repo/'Games/FerrariFormulaOne/RENDERING_PLAN.md';s=p.read_text();assert '## H11 — Prepare clock glyphs during drawing (accepted' not in s;p.write_text(s+closure)
p=repo/'Games/FerrariFormulaOne/README.md';s=p.read_text().replace('H10 was next at that checkpoint; H12 needs explicit approval.','H10 was next at that checkpoint; H12 was subsequently dropped.')
h11_readme='''H11 prepares the live session-clock glyphs in 56 bytes of public Fast memory\non 030/040/060, then copies them to Chip at the original HUD point. Reduced\nexact-state, native bitmap, RGB, elapsed, lifecycle, fault, legacy and performance\nchecks pass. Matched 040BCE post-wait draw time improves 37.13179 → 36.81414 ms;\ngrid improves 24.71307 → 24.91867 FPS. The 030/060 grid confirmations reach\n24.96020 FPS with all 300 intervals at two fields. Dense remains 12.48010 FPS.\nThe reproducible 267,960-byte build has SHA256\n`84783350ad9b1b5a23d3ac28862e53fbb0fb9cc6fdf553edb6289afcbe8bcb26`.\nSee the H11 closure in [RENDERING_PLAN.md](RENDERING_PLAN.md) for scope and\nhistograms. H6c common-scene confirmation remains open; H12 is dropped.\nThe H13 preinstalled snapshot and RC2 archive are unchanged.\n'''
s=s.replace('### H13 local preinstalled snapshot',h11_readme+'\n### H13 local preinstalled snapshot');p.write_text(s)
p=r/'docs/HI25_PLAN.md';p.write_text(p.read_text()+closure)
p=r/'manifest/project.json';x=json.loads(p.read_text());x['rendering_h11']='tmp/dev/manifest/render-h11-validation.json';x['rendering_h11_status']='Passed in reduced emulator scope: Fast clock preparation on030/040/060+Fast;47 native full-plane cases,100 exact updates/private fractions,4x30RGB,elapsed,lifecycle,both BLIT fault states,020legacy both options.040BCE grid24.71307->24.91867FPS;030/060grid24.96020 candidate-only;dense unchanged12.48010. Coarse payloads and archives unchanged;default-off.';x['rendering_h11_diagnostics']='tmp/dev/manifest/render-h11-diagnostics.json';x['next_steps'][0]='H11 accepted. H6c common-scene all-two-field confirmation remains open before considering optional H14–H16; stop optimizing if the target passes. H12 dropped. Keep reduced representative validation.';p.write_text(json.dumps(x,indent=2)+'\n')
p=r/'manifest/render-h11-diagnostics.json';x=json.loads(p.read_text());x['status']='Complete: final Fast-preparation v2 accepted; rejected variants absent from production.';x['validation']='tmp/dev/manifest/render-h11-validation.json';p.write_text(json.dumps(x,indent=2)+'\n')
print('H11 acceptance documentation written')
