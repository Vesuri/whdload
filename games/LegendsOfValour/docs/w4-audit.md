# W4 sprite-column patch audit

CUSTOM2 bit 3 selects counted eight-row blocks on 68000/10. The 020 candidate
changed inner-row costs by less than 1% with no measured FPS gain, so 68020+
retain the original hooks. VERIFY's sprite-twin option may force the bodies on
either CPU. Character-creation mode and disabled options perform no writes.

The complete-instruction hooks are h12:0517e, 09452 and 094e2 (six bytes each).
They replace the row-table load and indexed texel load. All signatures are checked
before writes, and caches are flushed afterwards. Relocation-reference and direct
branch audits found no targets inside these ranges; the loop-back branches target
their entry. Original column clipping, z-test and traversal order stay in place.

Eight rows retain the source row table, colour mask or palette lookup and transparent
branch. A1 is saved/restored for counter arithmetic using MOVEA/SUBA, preserving X;
the low counter word ends exactly as the original DBF loop. Fixed displacements
advance A0 by 1,536 bytes per block. The short tail uses the original one-row pattern.
TST restores the final pixel's NZVC before the unchanged column tail. The remapped
forward/reverse bodies use A2 and D5 exactly as their originals, without a colour mask.

VERIFY copies each relocated original inner loop at runtime. It runs both routines
on the same inputs and checks all fifteen registers, all five flags and every byte
of the allocated destination column, including unused rows. The two identical
remapped replacements alternate to cover both bodies without changing their caller's
traversal. SR snapshots are legal on 68000; CCR snapshots are selected on 68010+.
Counts, exact retained build hashes and fixed-window measurements are in profiling §8.

The optional VERIFY_WAIT_RESCUE fixture pulses EXIT/status-bar while a C2P twin waits
for the computer button with another panel active. It is excluded from ordinary
VERIFY and performance builds; assembled byte comparisons passed. The reusable
render_validate.sh calibrates and retains one build, then arms abort detection before
startup continues. All three geometries and 300 post-anchor conversions are required.
Normal, VERIFY and capture feature-prefix builds pass the 68000/PIC assembler.
