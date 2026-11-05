from pathlib import Path
import json,hashlib,shutil,subprocess,collections,gzip
r=Path(__file__).resolve().parents[1];root=r.parents[1];p=r/'manifest/b8-pal-validation.json';v=json.loads(p.read_text());assert v['capture_status']=='passed'
v['source_audit']=json.loads((r/'manifest/b8-pal-source-audit.json').read_text());assert v['source_audit']['status']=='passed'
a=r/'tmp/build/render-b8pal/FerrariFormulaOne.slave';assert a.read_bytes()==(r/'tmp/build/render-b8pal-rebuild/FerrariFormulaOne.slave').read_bytes();v['reproducible']=True
v['trace_audit']=json.loads((r/'manifest/b8-pal-trace-audit.json').read_text());s=json.loads((r/'tmp/step5/hi25-profile-040-40-bce-b8pal-grid/h7-safety.json').read_text());assert s['status']=='passed';v['dma_irq_audit']=s
for name,expected in [('FerrariFormulaOne_v1.02-h13_0481_Performance.lha','9a09fbb8715fe5fe382de07c328cfaf284e5c4e996677c1a3edbcdcf98ad8780'),('FerrariFormulaOne_v1.02-rc2_0481_Performance.lha','cdd0357047f302f1faec3584eafba5af2bfa56720452ab1f7eb1ad806a87c68b')]:assert hashlib.sha256((r/'dist'/name).read_bytes()).hexdigest()==expected
fps=v['results']['fps/b8pal-grid']['result'];elapsed=v['results']['timing/b8pal-elapsed']['result'];v['status']='passed';v['scope']='Focused cleanup: compiled-region/CCR proof on all three performance payloads; 040 BCE exact state/private100, 30RGB normal/grid each,60simseconds elapsed,300grid intervals,6field palette/IRQ/DMA trace. No broad release qualification or new coarse/lifecycle/legacy runtime matrix.';p.write_text(json.dumps(v,indent=2)+'\n')
text=f'''
## B8-PAL — Remove the diagnostic palette pulse (2026-10-16)

B8-PAL is complete. The shared performance drawing adapter no longer writes
`D1.w` to `COLOR00` after repairing the screen pointers. This inherited diagnostic
write could turn colour zero blue between the CPU write and the next copper
palette load; its timing-dependent boundary explained earlier transitional RGB
differences. The cleanup removes the write rather than masking pixels or
changing the real palette. It applies to 68000, chip-only 020 and Fast-memory
performance paths. The preceding `EXT.L D1` already supplies identical CCR
flags for every 16-bit input; no replacement instruction or test switch remains.

The historical host `.patch` write is deliberately retained for CUSTOM2=0
legacy-exact behavior. That source is unchanged. The shared adapter is used
only by the opt-in performance paths; CUSTOM2 remains default-off.

Focused checks passed:

- All three compiled payloads remove exactly the six-byte write at the audited
  screen-pointer repair site. Exhaustive 65,536-word flag equivalence passes.
- 040BCE: 100 game-state updates and private fractions match H11 exactly.
- 30 complete RGB frames each for normal and grid match H11 exactly, with no
  pixel masks or palette edits. These stable scanouts are separate from the
  transitional-field diagnostic identified in H3.
- Six traced 040BCE grid fields show the draw site executing with no CPU
  palette bus writes. The retained H11 trace contains the removed pulse;
  copper palette activity remains. Queue/interrupt and Chip-DMA checks pass.
- 60 simulated seconds: elapsed error **{elapsed['error_percent']:.8f}%**, below 0.25%.
- 300 040BCE grid intervals: **{fps['fps']:.5f} FPS**, mean **{fps['mean_ms']:.5f} ms**,
  p95 **{fps['p95_ms']:.5f} ms**; histogram **{dict(sorted(collections.Counter(fps['interval_fields']).items()))}**
  in PAL fields. The revised H6c 95%/three-field maximum gate passes.
- Independent build is byte-identical: **267,940 bytes**, SHA256
  `5db5a4c4fb42360578a38aa61c5cdcb3c7524fb4c5bed948f51d305050e1663e`.

This is a palette cleanup, not a claimed speed optimization. No native patch,
simulation, lifecycle, DMA resource, real palette or buffer ownership logic was
changed. The reduced scope does not claim a fresh coarse-path, lifecycle or
CUSTOM2=0 runtime matrix; host source identity and the compiled-site audit
cover the unchanged code contracts. Successor packaging/qualification remains
separate. RC2 and H13 archives are unchanged; human full races and real hardware
testing remain deferred. Earlier B8-PAL limitations describe historical builds.

Local evidence: `tmp/dev/manifest/b8-pal-validation.json`,
`b8-pal-source-audit.json`, `b8-pal-trace-audit.json` and their linked captures.
'''
f=root/'Games/FerrariFormulaOne/RENDERING_PLAN.md';assert '## B8-PAL — Remove' not in f.read_text();f.write_text(f.read_text()+text)
f=root/'Games/FerrariFormulaOne/README.md';s=f.read_text();s+='''
### B8-PAL cleanup

The inherited diagnostic COLOR00 write is removed from all performance paths.
Real palette setup and the frozen CUSTOM2=0 host patch remain unchanged.
Focused exact-state/RGB, elapsed, palette trace, DMA and 040BCE grid timing checks
pass; see the B8-PAL closure in [RENDERING_PLAN.md](RENDERING_PLAN.md).
The reproducible production build is 267,940 bytes, SHA256
`5db5a4c4fb42360578a38aa61c5cdcb3c7524fb4c5bed948f51d305050e1663e`.
This supersedes earlier B8-PAL cleanup notes for current source. The existing
preinstalled archives still contain their documented older builds.
''';f.write_text(s)
f=r/'manifest/project.json';j=json.loads(f.read_text());j['b8_pal']='tmp/dev/manifest/b8-pal-validation.json';j['b8_pal_status']='Complete: shared performance COLOR00 pulse removed; focused source/CCR, exact state/RGB, elapsed, palette trace/DMA and 040BCE grid gates passed. Legacy host patch unchanged; archives unchanged.';j['next_steps']=[x for x in j['next_steps'] if not x.startswith('B8-PAL:')];f.write_text(json.dumps(j,indent=2)+'\n')
f=r/'docs/HI25_PLAN.md';f.write_text(f.read_text()+text)
shutil.copy2(a,r/'amiga/.run/dh1/FerrariFormulaOne.slave');(r/'amiga/.run/restored-production.json').write_text(json.dumps({'source':str(a.relative_to(root)),'sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'note':'Restored B8-PAL production after focused checks; launch.json describes the previous test, not a new launch.'},indent=2)+'\n')
for folder in (r/'tmp/step5').glob('*b8pal-*'):
 for f in folder.glob('*.bin'):
  if f.stat().st_size<262144:continue
  h=hashlib.file_digest(f.open('rb'),'sha256').hexdigest();z=f.with_suffix('.bin.gz')
  with f.open('rb') as src,gzip.open(z,'wb',compresslevel=1) as dst:shutil.copyfileobj(src,dst)
  with gzip.open(z,'rb') as src:assert hashlib.file_digest(src,'sha256').hexdigest()==h
  f.unlink()
print('B8-PAL passed',fps['fps'],elapsed['error_percent'])
