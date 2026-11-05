from pathlib import Path
import json,hashlib,shutil
r=Path(__file__).resolve().parents[1];root=r.parents[1]
p=r/'tmp/h3-findings-draft.md';s=p.read_text().replace('## H3 road preparation and safe handover (2026-10-15)','## H3 accepted: road preparation and safe handover (2026-10-15)')
s=s.replace('FINAL_AUDIT_PENDING','The independent ordinary trace/census boots have identical complete start/end\nChip/Fast snapshots, scheduler contexts, DMA counts and displayed bitplane\naddresses. All DMA remains Chip. Recorded cycle coverage is 99.999993%, with\none boundary cycle unrecorded. Both CUSTOM1 settings pass the unchanged\ncontrolled CUSTOM2=0 exact-state gate on A500, A500+Fast, chip-only 020 and\n020+Fast. Deliberate colour-signature corruption reaches the WHDLoad error\nroute before installing that hook.\n\nThe ordinary post-H3 trace has 11 complete draws averaging 62.873917 ms in its\nown scene: the remaining scene/HUD stage costs 22.118482 ms, including the\n7.215498 ms demo-label call. This is fresh H4 input, not an A/B speedup claim.\n\nLocal evidence: `tmp/dev/manifest/render-h3-validation.json`,\n`render-h3-performance.json`, `render-h3-matched-profile.json`,\n`render-h3-palette.json`, `render-h3-palette-dma.json`,\n`render-h3-field-rgb.json`, `render-h3-build-audit.json`,\n`render-h3-dma.json` and `render-h3-traces.json`. Raw traces were compressed\nand decompressed hashes verified. The rejected first candidate is indexed by\n`render-h3-v1-rejection.json`; harnesses, fixtures and game data remain ignored.')
s+='\n**Next optimization: H4.** Separate pre-release cleanup **B8-PAL** is removal\nof the inherited unconditional diagnostic `COLOR00` pulse described above;\nH3 preserves its values and does not claim identical transition-field JPEGs.\n'
assert '_PENDING' not in s
p=root/'Games/FerrariFormulaOne/RENDERING_PLAN.md';t=p.read_text().replace('3. **H3 — Overlap road preparation with safe buffer handover.**','3. **H3 — Overlap road preparation with safe buffer handover: accepted.**').replace('RC2 LHA is unchanged. **H3 is next.**','RC2 LHA is unchanged. H3 was next; its findings follow.');p.write_text(t+'\n'+s)
p=root/'Games/FerrariFormulaOne/README.md';p.write_text(p.read_text()+'''
H3 overlaps road preparation with safe display handover and composes the final
flag/clock on the back buffer. Matched draw cost falls 1.04% (0.626 ms); 020+Fast
grid improves 12.48 -> 12.84 FPS and dense 6.24 -> 6.32. Normal accelerated
presentation remains 16.64 FPS. All twelve performance pairs have no mean/p95
regression. State/private fractions, 90 full RGB comparisons, native controls
(including 040/MMU/32 MiB), lifecycle, both legacy options and failure checks pass.
See RENDERING_PLAN.md for scope and the separately documented inherited B8-PAL
palette pulse; intermediate transition JPEGs are not claimed identical.

The current H3 source independently builds to 262,056 bytes, SHA256
`ac034f9786055bcb04c45383740def6cf249bf0910260dbc322c98461f15a8c2`.
CUSTOM2 remains default-off, and the packaged RC2 above is unchanged. H4 is the
next optimization; human full races and real-hardware testing remain deferred.
''')
p=r/'docs/STEP5_CAPACITY.md';p.write_text(p.read_text()+'''
## H3 accepted: safe road preparation overlap (2026-10-15)

H3 is implemented on the fine path with CCR saves, the fine VBL counter,
line-256 fallback and lifecycle-reset workspace. Native clear/sky order is
unchanged. Earlier completion exposed transient native flag-over-clock writes
to the displayed bitmap; the corrected implementation composes both final HUD
passes on the back buffer and restores the pointer view before completion.

Matched 14-draw cost 60.110256 -> 59.484553 ms (-0.625703 ms / 1.04%).
020+Fast normal remains 13.312 FPS; grid 12.480 -> 12.844; dense 6.240 -> 6.316.
Normal/grid accelerated profiles remain 16.640 FPS. 030 dense remains 9.984;
040/060 dense 9.984 -> 10.004. All twelve 300-interval mean/p95 gates pass.
100 exact state/private updates, 90 full RGB comparisons, 60-second elapsed,
both buffer alternations and 15 safe clear transitions pass. Independent
trace/census full snapshots, contexts and DMA are exact; all DMA stays Chip.
Native F1/F3 controls, 040/MMU/32 MiB controls, pause/tow/pit/menu/re-entry,
905-word patch restoration, unchanged INTENA, fresh workspace/bindings, all
four profiles with both legacy options and signature rejection pass.

One pre-existing issue is documented as B8-PAL: the unconditional B8 COLOR00=1
palette pulse from 38b2c61 (absent from the original game). H3 preserves its
values; its scanline shifts with drawing. All 15 stable RGB images and bitplane
sequences match; transition-field JPEGs differ at the palette-pulse boundary.
The completed lossless RGB gate is unchanged, with no pixel masks. Remove this
in separate cleanup before a successor package; no full intermediate-JPEG
identity is claimed. The rejected first H3 candidate's actual flag/clock
corruption was fixed and its evidence retained.

Current slave: 262,056 bytes, SHA256
ac034f9786055bcb04c45383740def6cf249bf0910260dbc322c98461f15a8c2.
The 000/chip-only 020 payloads remain byte-identical; default-off and RC2 LHA
unchanged. H4 is next. Full evidence is in manifest/render-h3-validation.json
and the tracked RENDERING_PLAN.md. Human playtesting and hardware remain deferred.
''')
p=r/'manifest/project.json';j=json.loads(p.read_text());j['rendering_h3_status']='Passed in documented emulator scope: matched draw -0.625703 ms (1.04%); all 12 performance pairs no regression, exact state/private and 90 completed RGB comparisons, safe handover/bitplane sequence, elapsed, controls/lifecycle, legacy options and failure cleanup. Existing B8-PAL pulse documented separately; no transition-JPEG identity claim.';j['rendering_h3']='tmp/dev/manifest/render-h3-validation.json';j['next_steps']=['H4: reduce repeated text/instrument bitmap work using the fresh post-H3 profile in RENDERING_PLAN.md.','B8-PAL: remove the inherited unconditional COLOR00 diagnostic pulse in separate cleanup before a successor package.','Human full-race playtesting and real Amiga hardware testing remain deferred; delivered RC2 archive unchanged.'];p.write_text(json.dumps(j,indent=2)+'\n')
p=r/'manifest/render-h3-validation.json';j=json.loads(p.read_text());j['candidate']={'path':'tmp/build/render-h3/FerrariFormulaOne.slave','sha256':hashlib.sha256((r/'tmp/build/render-h3/FerrariFormulaOne.slave').read_bytes()).hexdigest()};j['decision']='H3 accepted against the documented gates. Pre-existing B8-PAL palette pulse retained and explicitly documented; no full transition-JPEG identity claim.';p.write_text(json.dumps(j,indent=2)+'\n')
# Leave the launch drawer with the actual normal production candidate.
shutil.copy2(r/'tmp/build/render-h3/FerrariFormulaOne.slave',r/'amiga/.run/dh1/FerrariFormulaOne.slave')
archive=r/'dist/FerrariFormulaOne_v1.02-rc2_0481_Performance.lha';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='cdd0357047f302f1faec3584eafba5af2bfa56720452ab1f7eb1ad806a87c68b'
print('H3 findings saved; normal candidate restored; RC2 archive verified unchanged')
