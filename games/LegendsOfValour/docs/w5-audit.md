# W5 exact reciprocal cache audit

CUSTOM2 bit 4 selects a 1,024-slot tagged quotient cache on 68000/10. The original
020 divides cost less than the candidate's lookup/miss overhead, so 68020+ retain
all eight original hook ranges. VERIFY bit 6 may force the cache on either CPU.
Disabled options and character-creation mode perform no writes.

Each hook replaces a complete six-byte immediate MOVE at h12:02998, 02de4,
03236, 03676, 03ab4, 03f0c, 0435e and 0479c. Its jump resumes eighteen bytes after
entry, skipping the complete two-DIVU construction. Relocation and direct-branch
audits found no interior targets across those entire skipped regions. The once-per-view
division at h12:028f8 stays original.

Eight-byte records contain the exact 32-bit quotient, full 16-bit divisor tag and
two padding bytes. A zero tag represents an unused slot. Tags prevent collision
aliases from returning a wrong value; misses execute the original arithmetic and
store its result. A zero divisor takes the original divide exception path. The
cache lives in the slave, uses only legal 68000 instructions and needs no allocator.

A0 is saved/restored; D2 holds the canonical quotient and D3 the divisor. Four
callers swap D2/D3 before and after the helper. D7 and CCR differ at the hook return,
but every original continuation overwrites D7's low word and then the whole register
with MULU, reads no incoming flags, and defines all five flags with ADD before use.
The installer validates the complete skipped arithmetic, coordinate source, optional
NOT and exact continuation through that ADD before writing any hook. The independent
source checker `tools/ray_liveness.py` verifies the same facts against the local game.
No approximate arithmetic or change in rounding is introduced.

VERIFY compares all fifteen registers and X/N/Z/V/C after the canonical original
continuation. Its SWAP pair retains the full quotient in D2, so the comparison checks
every quotient bit as well as the resulting coordinate. The raw optimized state is
then restored and the game's unchanged continuation runs once. Before live rendering,
every nonzero divisor is tested in both register orders with X clear/set and varied
coordinates: 262,140 comparisons. The cache is cleared before live tests. The retained
integration build passed on both CPUs; counts and hashes are in profiling §8.

The seventeenth flag site is included conditionally, keeping earlier feature revisions
independently buildable. Snapshots use SR on 68000 and legal CCR reads on 68010+;
normal builds exclude all snapshot selection and twin/unit-test code. Normal,
VERIFY and capture variants pass the 68000/PIC assembler.
