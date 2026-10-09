# Stellar 7 internals

## Supplied version

The installed pack contains English Stellar 7, labelled NTSC, with Psygore's
1.0 slave (2 January 2008). Both archives contain an identical 3980-byte slave.
The installer contains no source. The `s7` executable is 186796 bytes.

Slave SHA-256: `b241c2656184ba17a6e5bfad3c335379b1e677c1df23731ceec296fc2aeef91d`.
Game SHA-256: `2360196317fc1d2a507c987834e9308f7368110194523c34b9376d606b606eb0`.

## Loader

The shipped slave requires WHDLoad 16, 512 KB base and 768 KB expansion RAM
(the latter includes the 256 KB Kickstart image). Its flags are NoError,
EmulPriv, ClearMem and Examine. It uses Kickstart 34.005, CRC $f9e3, and
current directory `data`. Keypad asterisk ($5d) quits. No CUSTOM options exist.

This is an OS game. The slave boots KickEmu 1.3, reads/decrunches `s7`, accepts
CRC16 $b9ea or $fcc4, frees the temporary file buffer, and LoadSegs `s7`.
It passes a newline argument and calls the loaded program. It applies no
patches to the game's hunks. Its patch list at slave:$60 instead adapts the
Kickstart image and filesystem. The game-specific loader is slave:$eb4–$f64.
It explicitly calls SetCPU with value $393d and mask $7f3f; actual cache state
must be checked before comparing fast-CPU measurements.

## Executable

| Hunk | Kind | File offset | File-backed bytes | Allocated bytes |
|---|---|---|---|---|
| 0 | Code | $24 | $25360 | $25360 |
| 1 | Data/BSS | $29f2c | $3558 | $823c |

Hunk 0 has 4833 relocation entries; hunk 1 has 323. Startup sets A4 to
hunk 1 + $8000. The code contains Aztec C `link a5` prologues and handwritten
assembly. Loaded-hunk identification must reject WHDLoad's PRELOAD file copy
and validate A4 against the next LoadSeg segment.

## Gameplay capture

The VERIFY-only CUSTOM5 fixture selects Escape through the intro's native
input paths and Begin through the main menu. It does not alter simulation,
RNG or rendering. Guarded hook ranges are hunk 0 $4582–$4587, $b1f4–$b1f9 and
$b8c4–$b8c9. Each replaces a four-byte PC-relative call plus its following
two-byte instruction. The release build contains none of these hooks.
The original pack's idle menu enters the briefing display; that is not the
real-gameplay route used here.

The anchor is hunk 0 $2c16 at gameplay counter hunk 1:$1e96 = 90, level SOL,
no player movement or firing. The call reaches the buffer-swap routine at
$1c84c; the gameplay counter increments at $2d4e and resets at $a0b6.
The three markers occurred equally often in the exploratory gameplay trace.
Independent read-only breakpoint captures reproduce the complete 50-field
swap pattern exactly on both CPUs.

Two fresh A500-equivalent runs have identical whole data-hunk snapshots at
the anchor, identical screenshots in all 50 fields, and identical PC/cycle
streams in all 50 fields. Raw traces are **not** fully identical: some saved
register values and DMA data values differ. The first observed register
difference is in Kickstart code; no claim of full machine-state identity is
made. Both captures have the same frame pattern and cycle/DMA totals.

## Measurements

Current frame-90 window, 50 PAL fields, reconstructed development slave,
CUSTOM5 enabled; no performance changes. Capture directories are local only.

| Machine | Fields/frame | fps | STOP | Interrupt-context cycles |
|---|---:|---:|---:|---:|
| A500-equivalent: 68000, 512 KB chip + 1536 KB slow | 10.00 | 5.0 | 0% | 21.4% |
| A1200: 68EC020, 2 MB chip + 4 MB fast | 4.40 | 11.4 | 0% | 20.4% |

The A500 window contains five swaps, with four complete inter-swap intervals;
the 68020 window contains eleven swaps, with ten complete intervals.
It is a stationary early-game scene, not a representative benchmark suite.
The earlier arbitrary gameplay capture measured 3.1 fps: do not compare those
scenes as an A/B result.

A500 self-cycle shares: $1bc94 7.01%, $1d51c 5.51%, $17c02 4.74%,
$14a9e 3.83%, $16c52 3.63%, $17cea 3.39%, $14d1e 2.32%.
$16c52 performs fixed-point vertex transforms; $17c02 caches transformed
vertices; $17cea performs perspective divisions. $1d51c is in the blitter
rendering path. These names are from static inspection, not source symbols.
The high interrupt share includes 1844 blitter-finished interrupts and 50
vertical blanks (1894 level-3 entries total) in 50 fields.

DMA slots: free 28.7%, refresh 1.8%, CPU 38.7%, copper 1.6%, audio 0.6%,
blitter 6.1%, bitplanes 22.5%. The native blitter-wait routine $1db8c–$1dbb1
accounts for 38180 / 7105050 cycles (0.54%); this excludes OS blitter waits.
The $2b96–$2bb3 tick wait and 750-iteration delay cost 220620 cycles (3.11%).
Do not confuse either figure with total renderer or total blitter overhead.

## Game time: mapped behavior

Hunk 1 offsets:

| Offset | Meaning |
|---|---|
| $1e96 (word) | Gameplay loop counter; also used by some non-gameplay paths |
| $24a8 (long) | Timer callback counter |
| $2434, $2436 (words) | RNG indices |
| $2438–$24a7 | 56-word additive RNG table |
| $43c0 (pointer) | Player object; x/z at +8/+12, heading at +$18, speed at +$40 |
| $46a0 (word) | Current level (0 = SOL) |
| $46c4 (word) | Player energy/shield value |
| $6870 (word) | Timer scale; observed 234 |
| $2946 (word) | Countdown used by intro, menu and swap waits |

The callback at hunk 0:$11748 increments $24a8; it ran exactly 50 times in
50 PAL fields. Setup at $8ca4 passes 13 to $1a6e4, which stores 13*18 = 234
in $6870. $1bab0 schedules callbacks with rounded `period*60/scale`, clamped
to at least one VBL; $1c6e8 dispatches them and decrements $2946 by
`scale/58` (4 at this setting). The sound driver separately installs CIA-B
timer interrupts through cia.resource at $25f0–$2666.

The gameplay loop waits for $24a8 to differ from its saved value at $2b96,
then runs a fixed 750-iteration delay. At the swap it records the current tick.
Several simulation counters decrement **once per gameplay iteration**: the
power timer at $3dc4 and object timers at $2cf2/$2d2c are examples. Enemy
spawning tests the gameplay counter modulo 16/64 at $2c96/$2cb2. Therefore at
least these behaviors are frame-coupled. The tick wait provides a ceiling,
not a fixed-rate simulation. A faster renderer can change game speed.

Over the same 50 PAL fields, the A500 executes five gameplay counter increments
and the 68020 eleven; both execute fifty timer callbacks. At frame 90, both
have identical mapped player state, energy (680), RNG state and timer scale,
but the timer counters are 3786 and 1628 respectively (including boot).
This confirms frame-coupled counters; it is not a complete motion-rate study.

Slowed-renderer coupling measurements, moving-input routes,
full object-state mapping and PAL/NTSC validation remain outstanding.

## Original Kickstart patch list

The following entries are decoded from the shipped slave list at slave:$60.
Targets are offsets in the Kickstart image; replacement destinations are
slave-code offsets. There are no original game-hunk patches.

| Kick offset | Command | Argument |
|---|---|---|
| $000d2 | PL_S | 0x2c |
| $00106 | PL_L | 02390002 |
| $00132 | PL_CW | — |
| $0025a | PL_CW | — |
| $00286 | PL_PS | slave:01ca |
| $00422 | PL_PS | slave:021c |
| $004f4 | PL_L | ffffffff |
| $0050c | PL_S | 0x8 |
| $00546 | PL_P | slave:01d4 |
| $00592 | PL_P | slave:01c2 |
| $005f0 | PL_P | slave:0058 |
| $0061a | PL_P | slave:01a4 |
| $00ebc | PL_P | slave:01de |
| $01354 | PL_P | slave:01ea |
| $014b6 | PL_PS | slave:020c |
| $015b2 | PL_PS | slave:01f4 |
| $04964 | PL_S | 0x14 |
| $04adc | PL_P | slave:02a8 |
| $04cce | PL_S | 0x4 |
| $06d70 | PL_PS | slave:0226 |
| $06d86 | PL_PS | slave:023e |
| $06efe | PL_L | 08390005 |
| $06f02 | PL_L | 00dff01f |
| $0ad5e | PL_PS | slave:0266 |
| $0ad7a | PL_S | 0x6 |
| $0aecc | PL_S | 0x18 |
| $0af96 | PL_P | slave:0248 |
| $0b00c | PL_P | slave:024c |
| $0d5be | PL_PS | slave:0284 |
| $1b96c | PL_B | 0008 |
| $1b9d2 | PL_C | 0006 |
| $1b9da | PL_C | 0008 |
| $1b9d8 | PL_W | 0001 |
| $25290 | PL_PS | slave:02b2 |
| $253a2 | PL_PS | slave:030e |
| $28452 | PL_PS | slave:04c6 |
| $28f88 | PL_P | slave:033e |
| $2960c | PL_P | slave:0444 |
| $29cfa | PL_P | slave:036a |
| $2a0e2 | PL_P | slave:0406 |
| $2a3b4 | PL_P | slave:036a |
| $2a6d6 | PL_PS | slave:0412 |
| $33ef0 | PL_PS | slave:046c |
| $3568c | PL_PS | slave:0476 |
| $36e4c | PL_PS | slave:048c |
| $38748 | PL_PS | slave:04b6 |
| $3c9b6 | PL_PS | slave:0482 |
