# W3–W6 patch audit

Every patch is optional and bypasses character-creation mode. W3 and W4 select the
wall and sprite unrolls on 68000/10; later CPUs keep their original loops.
W5 also selects its cache on 68000/10; 68020+ retain the original divides.
W6 selects its clear on every CPU after gains in both measurement matrices.
CUSTOM2 bits 2–5 select W3–W6. All signatures are checked before writes; cache flushing
follows installation. No movement, AI, music, frame cap or beam wait is changed.

- W3 replaces six bytes at h12:04c50, 04cf4 and 04d78. The paired bodies at
  04c38, 04cdc and 04d60 are identical. The CMP/DBGE initial test, texture indexing,
  NOT, ADD/ADDX and count semantics remain. Sixteen pairs use fixed destination
  displacements; every exit advances both pointers by exactly the number drawn.
  Original material and clipping tails remain. The 020 fixed-wall candidate
  regressed (2,276 → 3,009 main-task cycles/column), so the normal installer
  leaves all three hook ranges untouched on 68020+. VERIFY twins may force
  these bodies on either CPU. VERIFY copies the original paired
  body at runtime and compares the entire allocated column, all 15 registers and
  X/N/Z/V/C. VERIFY rotates the actual optimized block to cover all three blocks
  even when a route doesn't reach the third material tail.
- W4 replaces six bytes at h12:0517e, 09452 and 094e2. Eight rows use fixed
  displacements and one counter update per block; a short tail retains the original
  DBF loop. A1 is saved/restored for counter arithmetic that preserves X. TST restores
  the final pixel's NZVC. The row-to-texel lookup, transparent test, palette remapping
  and preceding depth test remain unchanged. Forward/reverse remapped inner bodies
  are identical; column order remains in their original callers. VERIFY copies each
  original inner loop independently and compares all registers, flags and the whole
  allocated destination column, including unused rows. The candidate changed 020
  sprite-row costs by under 1% with no measured FPS gain, so the final installer
  leaves its hooks original on 68020+. VERIFY twins may force the body on either CPU.
- W5 replaces the initial six-byte immediate MOVE at h12:02998, 02de4,
  03236, 03676, 03ab4, 03f0c, 0435e and 0479c. Each resumes eighteen bytes
  after entry, following the complete two-DIVU quotient construction. A 1,024-slot
  direct-mapped cache stores Q32 and a full divisor16 tag in each eight-byte record.
  Misses execute the original arithmetic; divisor zero retains the original exception.
  No approximation or rounding change is introduced. D7 and CCR differ at the hook
  return, but every original continuation overwrites D7 and reads no incoming flags
  before its first ADD defines all five flags. The installer checks the complete
  skipped arithmetic and these exact continuations before patching any site.
  `tools/ray_liveness.py` independently checks this against the local unpacked game.
  VERIFY compares all fifteen registers and all five flags after the canonical
  reciprocal-times-coordinate continuation, then restores the raw optimized state
  so the game's unchanged continuation executes once. The exhaustive test varies
  coordinates, both register orders and X clear/set for every nonzero divisor
  (262,140 comparisons), then clears the cache for live testing. The once-per-view
  division at h12:028f8 remains unchanged. Final paired measurements establish
  gains on 68000/10. The CPU-independent candidate regressed
  on the 020, so the final installer gates this cache to 68000/10; VERIFY twins
  may force it on either CPU.
- W6 replaces the six-byte height load at h12:051ee. Eleven repeated colour registers
  clear 192/112/80-byte rows with fixed predecrement MOVEM blocks; rows still advance
  192 bytes. Other widths retain the general sixteen-byte block path.
  It retains the caller's sky/floor colours and half-height row count, restores extra
  registers, and returns the original A0/A1/D1/D2/D3 and flags. VERIFY copies the
  relocated original routine at runtime, retains its complete 20,000-byte output,
  and compares all registers, flags and buffer bytes after the replacement.

Relocation-reference searches found no absolute targets inside any replacement range.
Direct branch-target inspection found no interior targets, including the full skipped
W5 arithmetic regions. Current-source 68020 runtime coverage includes every replacement block and all
clear widths. Current-source A500 coverage also passes all replacement blocks and clear widths.
In VERIFY only, the C2P staging buffer is enlarged to 20,000 bytes so W6 can reuse it between conversions.
VERIFY far PC-relative buffer addressing uses an in-range anchor plus a constant offset; the
68000/PIC assembler validates both normal and VERIFY builds.

W3–W6 are verified and measured in final fixed-window pairs on both CPUs and
both routes, with a separate source commit for each feature. Local preferences
enable W1–W6 (mask 63). Timing investigation remains open; W7 remains deferred.

The revised source passed `render-rescue-twin-a500` and `render-rescue-twin-a1200`,
with the identical retained VERIFY SHA256
`4690a396852cf44643a0f84c5b7d9fcc726ef5fbcda437ced5704418deeb7092`.
Both cover every wall/sprite block, every clear width, all three view geometries,
300 large-view conversions after the anchor, and all 262,140 reciprocal cases.
All seventeen flag snapshots use legal SR reads on 68000 and nonprivileged CCR
reads on 68010+. The selector and all twins are excluded from normal assembly.
Counts and commands are in profiling §8.

A `VERIFY_WAIT_RESCUE` fixture pulses the EXIT/status-bar point while a C2P-twin
route waits for the computer button. The bounded stopped dump confirmed a later
wait remained stuck with another panel's button list active. The rescue is excluded
from ordinary VERIFY and performance builds; both byte comparisons passed.
`tools/render_validate.sh` preserves the successful serial calibration/startup-abort
workflow. It selects the options implemented in the assembled revision.

Temporary feature-prefix snapshots assemble in normal and VERIFY modes with
68000/PIC checks. Final per-feature builds are checked before each commit.
