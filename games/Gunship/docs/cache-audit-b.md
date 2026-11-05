# B3: gamemule cache audit

Offsets below refer to PAL 0658 hunk 0. `tools/audit_cache_b.py` records the
instruction inventory and control-flow results in `tmp/b/cache-audit.json`.
The complete direct-writer listing is `tmp/b/direct-writes.txt`.

There are 267 direct write sites, targeting 138 distinct starting addresses.
All are reached by the static control-flow traversal, seeded with the entry
point, OS/formatter callbacks, the input dispatch vector and the retained A
profiles. Those profiles contribute 6,023 observed PCs; traversal decodes
13,490 instructions. No instruction byte intersects any writable island below.
The source addresses, operand sizes and destination addresses are retained,
not inferred from differences between two sparse memory dumps.

Indirect stores were followed from the address references, including the input
handler's A2, geometry/projection arrays, span table, instrument arrays, numeric
format buffer, message/radar arrays and object/effect scratch. Ranges below are
half-open containers for writable data, not a claim that every byte changes.

| Hunk-0 range | Use / writers |
|---|---|
| `0C64–0C78` | Input-key flags; `0EB8`, `0EDC` |
| `0C8E–0D4C` | Input pointer, DMA/input state, three saved register blocks; `0D60`, `0E64`, `0EC6`, `0F14`, `0F32`, `0FEC`, `1020` |
| `4B18–4B1C` | Timer accumulator; `4B40` |
| `4E18–4E3B` | Interrupt/sound/control state; `4BDA–4E82`, `52BA`, `8198` |
| `5518–5526` | Input/control state and copied input bytes; `4F0A`, `5488–54CE` |
| `5AF6–5AFA` | View origin, temporarily changed/restored at `A7CC–A820` |
| `5AFE–5B04`, `5B22–5B24` | Current object/render state; `5FB6`, `610A–6306` |
| `6980–77B8` | Geometry pointer, edge cache, transform/vertex/projected-coordinate arrays, face flags and bounds; `5C1E–6912` |
| `8524–8530` | Plane count and clipping bounds; `320C–3226`, `5C62–5C70`, `8846–8CCE`, `A6E4–A80C` |
| `8D88–90B0` | CPU span table and polygon bounds; `8820–8CCA` |
| `9C44–9C58` | Object/effect scratch; `8028`, `987A–9B46`, `9EA6–9EB4`, `C696` |
| `A14C–A14E` | Effect state; `A074–A09A` |
| `A434–A450` | Message/object state; `4C1E`, `A1DE–A422`, `BC12–BC42` |
| `A99C–AA4A` | Visibility/object list, saved view state; `473A`, `4F52`, `9842`, `9B92`, `A506–A7F6` |
| `AF8C–AFA4` | Needle endpoints, indexed by buffer; `AD30–ADAA` |
| `B048–B05E` | Instrument/tape redraw state; `5364`, `AAA2–AB12`, `ACBE–ACE0`, `AF54`, `B0C4` |
| `B1BA–B1C3` | Numeric formatting buffer, predecrement writes at `B1A2/B1B2` |
| `B1DC–B278` | Instrument state accessed through A0; `536A`, `AC78/AC8C`, `B05C–B184` |
| `B6EC–B70C` | Message/text scratch; `B4AA–B68C` |
| `B92C–BA10` | Radar coordinates and weapon/status words; `58FE`, `A074`, `B70C–B7AC`, `BBD0`, `BEB6–BECA`, `C290–C52E` |
| `BA34–BA64` | Object/effect scratch arrays; `BB1C`, `C118`, `C4B8` |
| `C6A0–C762` | Object positions, trails, effects and flags; `428A`, `4C40–4C5E`, `9A2A–C6A0`, including completed-swap clear `44CA` |

The nearby input dispatch vector, trigonometric/needle lookup tables, strings,
formatter callbacks and library jump veneers are read-only. In particular,
`C764` is a callback entry, not part of the preceding writable effect state.
The indirect control transfers in the report are indexed branch tables, the
input dispatch vector and registered callbacks; they do not execute writable
geometry, span or instrument data. Shared cache lines containing unchanged
instructions and writable data do not by themselves require cache flushing.

## Cache and DMA ownership

The shared KickEmu `CACHE` definition selects `Base_NC`, `Exp_CB`, `Slave_CB`,
IC/DC and branch caches. Thus chip/base memory used by bitplanes, mask planes,
sprites, copper lists and DMA buffers is non-cacheable; fast CPU-only data and
slave memory may use copyback. The geometry/span data embedded in hunk 0 is
CPU-only: the CPU expands spans into the chip mask before the blitter uses it.
Palette data is copied into the display structures. No writable hunk-0 table
is a DMA source or destination, and no game routine generates instructions.

Loader relocation, regular slave patches, `blitter_dispatch` and VERIFY patching
are the intended writes to instructions. They run before execution of the new
segment. KickEmu's LoadSeg hook invokes `_flushcache` after `_cb_dosLoadSeg`
returns; `_load_exe` does the same after its initial callback. No per-frame
flush or relocation of the data islands is required. B3c therefore needs no
runtime change. The inventory is for the available PAL game; it is not a
claim to have exhaustively executed every mission or examined an unavailable
German binary.

## Additional MMU observations

The original A matrix uses NOMMU cores on 040/060. Its graphics comparison is
separate from full-MMU cache observation; enabling data-cache emulation in a
configuration does not prove that WHDLoad enabled copyback in that run.

Extra runs using the current native full-MMU 040/060 setup reveal pre-existing
cockpit artwork corruption. The pre-B slave and NOCACHE reproduce the same
missing/displaced cockpit outlines. The fixed-seed 040 pre-B and patched
NOCACHE screenshots are byte-identical; the patched cached run differs only
by 25 radar pixels, with the same corrupted static cockpit. This is not a
new self-modifying-code or cache-coherence failure. Retain these runs under
`tmp/b/graphics-*-mmu-*`, `graphics-040-original`, and `graphics-040-nocache`.
The user-observed T-74 copy-protection graphics issue remains deferred; these
observations do not establish whether it has the same cause.

The final observer publishes both CPU tick and back-buffer index in D0 at the
completed-swap checkpoint (marker +76). The front buffer is the other index.
It obtains the immutable BitMap array address from the relocated LEA at hunk-0
+0BA0 and reads that selected array member, rather than the changing cached
Screen.BitMap. A 68060 trial showed a physical RAM tick of 319 while the CPU
had reached tick 320. That trial is retained as an observation negative control;
raw physical hunk snapshots must not be represented as the full CPU-visible
copyback state. The final comparison uses the CPU register as its tick oracle.

With CPU-selected front-buffer capture, the 68060's ticks 300/310/320 match
the 68020 reference exactly. At tick 300 its raw RAM still reported 299; this
is an observed negative control for trusting raw tick reads, not a game-state
failure. `resload_SetCPU(0,0)` reports policy `0x3B3D` with caches enabled and
`0` under NOCACHE. The normal slave is byte-identical before/after these VERIFY
observer additions. Cache-only checks use immediate blits; the A2 cycle-exact
matrix and delayed-BBUSY assembled tests remain the blitter-correctness checks.
