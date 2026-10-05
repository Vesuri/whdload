# W2 chunky-buffer allocation audit

2026-10-06. Allocation policy: `AllocMem(20000, MEMF_PUBLIC)`, independent of CPU.
PUBLIC allows Exec to choose its normal memory-list priority; it does not require FAST
or CHIP. Kickemu can label expansion slow RAM FAST, so distinguish Exec attributes from
physical bus placement in measurements. If this allocation fails, retain the original
pool allocation and its failure handling. Other pool allocations remain unchanged.

## Pointer and ownership

The game stores the pointer at `h11:05fc2` (`-8254(a4)`, A4 = h11 + `$8000`).
`h1:022c6` pushes 20,000 bytes; `h1:022ca` calls `h1:020d4`; `h1:022ce` stores its result.
The original path reaches `h0:00cd4`/`00dd4`. It adds a private size header and suballocates
from the C runtime's pool. That pointer must not be passed to Exec FreeMem.
The refill at `h0:00e66`/`00e68` calls `h0:00d68`, which adds a 12-byte backing-block
header and calls Exec AllocMem at `h0:00d7c` with flags **0** (`moveq #0,d1` at
`00d76`). It feeds the free list and retries the suballocation. There is no global
MEMF_CHIP flag here to change; the observed chunky suballocation is in chip memory.
W2 leaves this refill path untouched.

W2 patches the eight bytes covering the PEA/BSR with JMP/NOP. It retains the original
20,000-byte argument slot on the stack and returns to `h1:022ce`. The new pointer is tracked
as slave-owned. At `h1:02760` the original MOVE pointer,(SP) and JSR pool-free are replaced
as another complete eight-byte range. A slave-owned pointer uses `FreeMem(pointer,20000)`;
a pooled pointer follows the original `h1:02a4a` → `h0:00f04` path. That pool free is deferred:
it records the private header for release on the next pool allocation.

Both hook signatures are checked before either write. Relocation cross-references report
no references into either range; the h1 branch audit also finds none into those bytes.
CUSTOM2 bit 1 gates both hooks; bit 0 remains W1. Character creation is excluded. Neither
CPU flags nor addresses determine allocation policy. Shipping code contains no test cycle
or forced allocation failure.

## Every pointer user

The ten relocated absolute references, plus six A4-relative references, are:

| Site | Use | Chip RAM required? |
|---|---|---|
| `h1:022ce` | Store allocation result | No |
| `h1:02760` | Pool free, replaced for owned allocations | Matching allocator required |
| `h12:02814` | CPU wall renderer's base in a5, with row/view offset | No |
| `h12:051a6` | CPU sky/floor fill and clear | No |
| `h12:054d2` | Per-frame CPU C2P input (W1 also rereads it) | No |
| `h12:05604` | CPU C2P into separate planar bitmap | No |
| `h12:05702` | CPU C2P into `h11:05fae` planar staging buffer | No |
| `h12:05a96` | CPU column-wise one-shot conversion | No |
| `h12:05b86` | CPU reverse-column one-shot conversion | No |
| `h12:05caa` | CPU conversion interleaved with planar screen blits | No |
| `h12:09402`, `0948a` | CPU palette-remapped sprite writes | No |
| `h2:026c6` | CPU map drawing into chunky buffer | No |
| `h5:0026a`, `00412` | Pass pointer to sprite drawer via `h5:02638` → `h12:05114` | No |
| `h9:00024` | CPU masked byte copies into chunky buffer, stride 192 | No |

The relocation operand offsets are two bytes after the listed instruction addresses.
An additional raw `$dfc2` word at `h2:05e0a` is a BSR displacement, not a pointer access.

In the one-shot path, `h12:05dd4` calls BltBitMap and WaitBlit using the bitmap at
`h11:05f2c`, not the chunky pointer. Chunky-to-planar staging is CPU work; planar buffers,
screen planes, textures and audio retain their original allocation paths. No chunky
pointer is supplied to a DMA register or graphics blitter call in these users.

## Verification design

VERIFY CUSTOM5 bit 2 forces the PUBLIC allocation attempt to fail, exercising original
pool allocation and free. Bit 3 runs allocate/free/reallocate through the same callable
allocation/free dispatchers used by the game, checks that ownership clears after free,
and records a successful cycle. VERIFY also records TypeOfMem flags. These checks run at
allocation time, not in measured frames. Performance captures use CUSTOM5=1 only.

`tools/chunky_check.py` checks the game's pointer against ownership, reported memory type,
and the successful cycle when requested. Three-view correctness uses W1's existing pixel
twin, including perturbed low nibbles. Fixed-window W2 A/B keeps W1 enabled (CUSTOM2=1/3);
`tools/check_disabled.py --custom2 1` checks only W2's disabled ranges.

## Capture-harness correction

A larger 68000 expansion dump exposed a race: the debugger resumed after a memory dump,
then the host's region scan could run past the tape's one-time anchor. The harness now
explicitly stops before dumping/scanning and rejects any stop other than the anchor.
Interrupted diagnostic runs are not accepted as correctness or performance evidence.

The 512 KB chip + 4 MB fast 68000 VERIFY fixture stopped in the original startup
allocator's failure loop before the chunky allocation (zero W2 cycles and pixel twins).
Use 1 MB chip + 8 MB physical fast RAM for the additional 68000 fast-memory test.
The corrected control reaches the wall anchor there with W2 disabled.

## Completed correctness checks

The retained VERIFY slave SHA256 is
`b7484e3af7fe5628252cab342e9f3b9c18051165d356ecd8cbd75fca82cfda54`.
With CUSTOM2=3 and CUSTOM5=11 (tape, pixel twin, lifecycle), the 68000 fixture
(1 MB chip + 8 MB physical fast) passed 551 twins: 371 large, 73 medium, 107 small.
The 68EC020 fixture (2 MB chip + 4 MB fast) passed 1,545 twins: 746 large,
347 medium, 452 small. Both recorded PUBLIC/FAST flags and an owned buffer within
physical fast memory, and passed allocation/free/reallocation. These captures are
`tmp/prof/w2-views-68000-fast-1m` and `tmp/prof/w2-views-a1200`.

`tmp/prof/w2-public-fallback-a1200` uses the same build with CUSTOM5=13
(tape, forced PUBLIC allocation failure, lifecycle). It reached the wall anchor,
kept the original pooled buffer in chip memory, cleared ownership and passed the
cycle. The ordinary 68000 fast-memory control with CUSTOM2=1 also reached its
anchor and retained both original W2 hook ranges. Performance measurements and
scene comparisons are recorded in profiling.md §8.
