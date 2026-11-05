# B correctness work (2026-10-20)

B1 commit 56aa291 balances d0-d1/a0 and compares the key before restoring a0.
Input evidence: b1-input-run2, b1-pad6. CD32 monitor events must register the
virtual controller repeatedly during startup before the slave detects it;
otherwise FS-UAE's startup configuration reset leaves the controller absent.
The test uses real serial pad reads, not injected guest key data.
Normal/VERIFY matrix: b1-normal / b1-matrix-run. Ten normal cells within 1%
of A; uncached 030 remains failing. Replay b1-replay-run matches A images,
rank order, and one crash. References retain their tested.slave binaries.

## B2 loader/DMA race

On the fixed route, uncached 030 enters DASH2.LBM loading around monitored
boot fields 2380–2400, during race dashboard preparation ($a8c08->$b29f8),
before the race hook is installed. The bad decoder is seen at 2400–2440.
The eventual exception is Line 1111 ($2c) at $4; the old exploratory $68
Illegal Instruction report was not reproduced and is not claimed identical.

b2-load/after.bin proves the loader returns all 7824 original file bytes at
$77cc0. The subsequent copy at $b2a12 into $da7e has 2300 damaged bytes,
starting at offset $13c6 (b2-copy/chip.bin). The previous screen copy's DMA
source/destination are $6f780/$77cc0. The corrupted data contains a spurious
$80 run at $ee5b. $aef64 negates that byte and sign-extends it to $ff80;
DBF runs for 65409 writes, overwriting the program and interrupt hook.
The failing PC subsequently runs through unmapped memory from $80808080,
wraps around, and eventually traps at $4. See b2-rle and b2-crash/crash.json.

Waiting for blitter completion before resload file loading prevents the
loaded file being overwritten. b2-fixed-copy/chip.bin retains an exact
7824-byte DASH2.LBM at $da7e, and b2-wait proves the formerly failing cell
runs the race. The normal loader fix applies to boot and game file calls;
it does not change simulation or attempt to decode corrupt input.

Caution: debugger custom-register reads use save_custom and may affect
pending blitter state. The before/after chip-only copy captures are the
primary evidence; the matrix/replay use no custom-register debugger reads.

B2 acceptance: all 11 normal cells pass; all 13 diagnostic/functional cells
pass after retrying a1200-fast (b2-matrix-retry) following a pre-boot launcher
failure. The normal A1b replay retains exact images, racer order, one crash.
B2 is committed as 8f0dd1c. No emulator-only workaround was needed.

## B3–B5 timing limits and acceptance

B3 commit 3c81c2d adds CUSTOM2 bit 0. b3-animation-020 and
b3-animation-25-run validate 250 hook phase samples at 12.5/25 fps, with
full-render images inspected. The functional 25 fps machine is deliberately
fast, not a claim about real 68020 performance. The final hook explicitly
clears X like the original ADDQ (whose input phase is always 0..7).

b4-deltas uses the same functional 68020 machine, fixed periods 4/2/1,
and renderer omission. Distances at 490 fields: 3364352 / 3333820 / 3327906.
Differences from delta 4: -0.9075% for delta 2, -1.0833% for delta 1.
Tape outcomes change: delta 4 crashes at 1350; delta 2 does not crash in
the 1500-field window; delta 1 crashes at 1096. Full-render delta 2 in
b5-25-replay has exactly the same terminal state as renderer-skipped delta 2.
The guard (CUSTOM2 bit 1) waits at the swap, never fakes a larger elapsed
delta. b4-guard-straight/tape are exactly the delta-2 distance/final state
including rank order and crash count. No 50 fps equivalence is claimed.
Long-frame control b4-upper-control uses delta 12; b4-upper-clamp uses 8.
Startup's six initial delta-1 samples precede steady race integration.

B5 baseline b5-020-replay: 399 gates, zero closed, zero drains, crash 1366.
B5 25 fps b5-crash-search/run-0-False: 1204 gates, zero closed, zero drains,
crash sampled at 1100 and visible recovery at 1400. The original A tape did
not crash at delta 2, so this additional tape omits the early wiggles.
Queue production clamps at 6400; drain subtracts min(queue,3000) each field;
three drain fields suffice before consumption on the following field. No
producer refills that occupied consumer buffer while it waits. The live
queue remains zero in the measured scenarios. No production gate/drain
rewrite is justified.

Final source is 2.1 beta. CUSTOM2=0 is original timing, 1 field animation,
2 safety (two-field floor/eight-field ceiling), 3 both. Fixes always on.
The prior plan's implication of exact cross-rate gameplay is not supported:
collision sampling changes outcomes even when straight distance is within 1%.

Final validation paths:
- b-final-normal-off / b-final-normal-on / b-final-verify: full preliminary
  off/on/diagnostic matrices before the final animation X-flag correction.
- b-final-matrix-v2 / b-final-mmu-v2: final binary, all normal cells with
  both options and 040/060 MMU functional coverage.
- b-final-checks: final keyboard/CD32, off/on replay and fixed-field hash.
- b-final-build: normal and three diagnostic builds, normal has no markers.
- b-final-profile-020: default-timing Barto trace, 495 complete fields,
  284204 cycles per field, no missing PCs, CPU/blitter/free DMA shares
  31.8%/13.6%/27.9%, matching A. Captured before the four-byte X-flag fix;
  animation is disabled in this profile. Raw traces are losslessly compressed
  with checked decompressed SHA256 in trace-manifest.json.
- b-visual-review.png compares representative A500/020-cache/030/040/060
  fixed-field scenes. Small frame-phase differences are visible, with no
  corruption or missing objects. The 020 fixed tape's images remain exact.

The generic preload-versus-DMA lesson should go to AmigaXDev when its
unrelated working changes are settled. Its AGENTS.md says to leave a dirty
project alone; that repository was not modified by this task.

Final acceptance completed: 11/11 normal cells and 2/2 MMU functional cells on
the final binary pass; same-cell normal distances stay within 1% of B2. Both final
option-off/on tapes match B2 screenshots, rank order and crash count. Extra
b-final-input-on/b-final-pad-on checks pass keyboard/CD32 with safe timing enabled.
Minimum runtime tested: WHDLoad 17.2 build 5386, official old-whdload user archive
SHA256 5227383a6b3920074409e625cac72115aaea342b7ee7e620d94bd5ceeb13547b.
b-whd172 confirms 12.5 fps, distance 3364352 with CUSTOM2=3. The main matrices use
WHDLoad 20.1 build 7190. See b-whd172/runtime.json for source URL and runtime hash.
Normal final SHA256: 6892f327f8f6c7719a3d5603a4bd1ed6a844dbd228b7e50c916678d58ba10bf3.
