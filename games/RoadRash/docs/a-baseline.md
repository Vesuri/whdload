# Accepted A baseline — 2026-10-20

A1–A5 are complete. B–G remain open. The tracked performance-plan.md §9 contains the
accepted measurements and limitations; this file indexes local evidence. Do not use the
other a-* directories as accepted references: they include rejected configuration and
host-input experiments.

- tools/fixtures/a-reference.json: expected artifact hashes and accepted run paths.
- tools/fixtures/lap.json: 30-second PAL tape, race fields 100–1600; steering, overtaking,
  roadside collision and one crash. normal-1/race-1380.png visibly shows the crash.
- tmp/a-isolated-validation/validation.json: normal, VERIFY, fixed-field slave-hash
  repeats pass; distance, rank, crash, missing-image and state-hash corruptions rejected.
- tmp/a-accepted-matrix/matrix.json: 12 passes, uncached 030 failure; both MMU cells pass.
- tmp/a-accepted-normal/matrix.json: 10 passes, uncached 030 failure. This is the fps
  reference for normal builds; diagnostics have their own reference.
- tmp/a-030-failure-evidence/030-50/route-failure.png: Line 1111 Emulator ($2C) at $4.
  Do not conflate this with the original B2 Illegal Instruction at $68 without debugging.
- tmp/a-timeout-control/matrix.json: intentionally enforced one-second deadline failure.
- tmp/a-accepted-profile-020/: Barto profile.json, profile.pkl.gz, compressed raw chunks
  and trace-manifest.json. 495 traced whole fields in race window 100–600. CPU 284204
  cycles/field; DMA free 27.9%, CPU 31.8%, blitter 13.6%.
- tmp/a-accepted-profiles/: 030-50+cache, 040-25, 060-50. Each captures 500 vsyncs and
  validates actual CPU model. Flat instruction/chip statistics only; unmatched RTS means
  inclusive costs are untrusted. 040/060 are not hardware instruction-cycle simulations.

Every successful capture records tested slave/emulator SHA-256, effective configuration,
field boundaries and input. Private emulator SHA-256:
ee8e2f41e49021d7377d2adf782ebaff6a99fc49df57e6007d86b862bcf7cbc3.
Normal slave SHA-256: 5c85f98b820abbf02af5bdf6696b1111321e0942047fc0739a6c60226bb138da.

Acceptance uses same-cell, same-instrumentation comparisons. ±1% is not relaxed for
cross-CPU differences or VERIFY overhead. Fixed checkpoint states/screens repeat; two
normal intermediate samples differ at debugger stop phase. MMU translation is proven
by TC=$8000, but data-cache emulation is disabled and the direct UAE board avoids a native
filesystem trap deadlock. B1, B2 and D1 coherency work remain outstanding.
