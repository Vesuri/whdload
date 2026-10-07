# W6 chunky-clear patch audit

CUSTOM2 bit 5 replaces the complete six-byte half-height load at h12:051ee.
Disabled options and character-creation mode perform no writes. The installer checks
the original instruction and its relocated operand before patching, then flushes
caches. Relocation and direct-branch audits found no targets inside those six bytes.

Eleven repeated-colour registers (D2–D7/A2–A6) write 44-byte predecrement MOVEM
blocks. Fixed paths fill the exact active widths 192, 112 and 80; each advances the
source row pointer by 192 bytes. Other widths retain a general sixteen-byte path.
The original sky/floor colour, half-height count, row stride and unused columns stay
unchanged. Extra registers are saved/restored; the original A0/A1 endpoints, counter
low words, D3 group count and X/N/Z/V/C are preserved. The MOVEM mask excludes its
address register, avoiding CPU-dependent base-register semantics.

VERIFY copies the relocated original routine at runtime and runs both routines on
the same input allocation. It compares every byte of the 20,000-byte buffer, all
fifteen registers and all five flags, aborting at the first difference. Counts for
all three widths and both CPUs are recorded in profiling §8. VERIFY alone enlarges
the C2P staging area to 20,000 bytes so it can hold the expected output between
conversions; normal builds retain the smaller staging allocation and exclude tests.
Normal, VERIFY and capture variants pass the 68000/PIC assembler.
