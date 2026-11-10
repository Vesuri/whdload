# Internals

What is known from reading JOTD's 1.2 slave (`src/EncounterHD.s`) and the installed
`disk.1`, and from the level-1 benchmark traces ("Frames and time", "Performance").

## The installed game

`tmp/game/Encounter/disk.1` (473088 bytes) is Harry's Patcher image of the original disk
(the install package's `encounter.imager`; its source, `source/encounterimager05.asm`,
ships in `Encounter.lha` but is not in JOTD's repository). The game is a non-DOS
trackloaded program: no hunks, no files, absolute addresses. Offsets below are `disk.1` file
offsets, with the address the slave loads them to.

## Slave header

`ws_Version` 10, flags `WHDLF_Disk|WHDLF_NoError|WHDLF_EmulTrap|WHDLF_EmulDivZero`,
`ws_BaseMemSize` `$80000` (512 KB, the whole game in chip memory), no ExpMem
(`USE_FASTMEM` is never defined), no Kickstart: a direct slave. Quit key `$5D`
(numeric `*`). `resload_Control` reads `CUSTOM1` (unused) and `BUTTONWAIT`.

## How it loads

The slave does the original boot's work with `resload_DiskLoad` (disk 1) and skips the
boot block's own MFM trackloader:

| Step | `disk.1` | Address | What |
|---|---|---|---|
| 1 | `$8C00`, `$400` bytes | `$400` | the boot block code (`DOS\0` at `$400`) |
| 2 | `$0000`, `$7E00` bytes | `$68000` | the title picture: 16 colours at `$68004`, planes from `$68080` |
| 3 | `jsr $4BC` (file `$8CBC`) | | the boot code's title routine: copies the four planes to `$78000`, sets DMA, sprites, the copper list at `$528` and the palette, returns |
| 4 | | | with `BUTTONWAIT`, waits for the left mouse button or the port 2 fire button; otherwise the title is shown only while the next load runs (under `WARP=1` it is gone within a few seconds) |
| 5 | `$9000`, `$69530` bytes | `$1AD0`–`$6B000` | the program and its data (file offset = address + `$7530`) |
| 6 | | `$6000`–`$13000` | decrypted in place: per word, a 16-bit shift-register key (seed `$3491`; `asl #3`, `eor`, two `roxl`, `eori #$AAAA`) XORed into the word. This replaces the original protection, which failed on 68020+ (Harry's 1.1) |
| 7 | `ENHIGH`, `$90` bytes | `$91E2` | the high-score table, when the file exists |
| 8 | | | the patches below, DMACON `$8390`, ADKCON `$B500` (as the boot code sets them), cache flush, `jmp $D7E2` (file `$14D12`: the game's start, stack at `$7FFFE`) |

Because of step 6, the file bytes at the patched addresses are encrypted; the original
instructions below are read from the decrypted image.

## Patches

All are written to memory after the decryption; addresses with their `disk.1` offsets.

| Address | File | Original | Patch |
|---|---|---|---|
| `$6C` | | (unset) | level 3 vector to `INT3`, which clears INTREQ `$0380` and returns, until the game installs its own (`$804E`, at `$E1A0`, file `$156D0`) |
| `$94C6` | `$109F6` | `clr.b $939B` (6 bytes) | `jsr SAVEHIGH`: the same `clr.b`, then `resload_SaveFile` of `$91E2`, `$90` bytes, to `ENHIGH` |
| `$C4D2` | `$13A02` | `moveq #75,d1; dbf d1,*` (6 bytes): the keyboard handshake delay, a CPU-speed loop | `jsr keyhp` (below) |

Inside `keyhp` (the raw key, already decoded, is in `d0`):

- `DBFD1` with `d1 = $50`: `divu #$28` gives 2, so it waits for three changes of the
  vertical beam position byte (`$DFF006`), two to three raster lines, independent of the
  CPU.
- The quit key (`_keyexit`, `$5D` unless `QUITKEY` overrides it) calls `resload_Abort`
  with `TDREASON_OK`.
- Key `$5B` (the ReadMe's numeric `]`) writes 0 to `$DFF101` (BPLCON0's low byte), BPLCON2
  and BPLCON3, and `$0011` to BPLCON4: the workaround for the rare white-colours bug the
  ReadMe mentions, which on an AGA machine looks like stale AGA bitplane control state.

The game's own exception vectors make the header flags work: the boot block runs a
`trap #0` through `$80` (at `$420`, file `$8C20`), and the game points the division-by-zero
vector `$14` at an `rte` (`$E288`, file `$157B8`, set at `$E1BE`, file `$156EE`). With the VBR moved by WHDLoad, `EmulTrap` and
`EmulDivZero` forward those exceptions to these vectors; this is the ReadMe's "no more need
for NOVBRMOVE (division by zero avoided)" in 1.2.

The source's `ifeq 1` block (clearing `$69666`–`$6B000`, patching `$69A8A` and
`$69A9C`) and the commented-out quit patch at `$D7F6` are not assembled.

## Frames and time

Addresses are base-memory addresses; in the program region the `disk.1` offset is the
address + `$7530` (encrypted bytes between `$6000` and `$13000`).

- **Field counter**: the level-3 handler (`$804E`) starts with `addq.l #1,$11DEA`. Its low
  word `$11DEC` is read only by the frame pacing and the title setup (`$A078`).
- **Copper lists**: COP1LC is `$12370` (bitplanes at `$68000`) or `$12324` (`$78000`).
  Both jump to `$123B4`: colours 1–7 and 9–15, a copper interrupt, then a jump to the
  sub-list whose address is in the moves at `$123F4`/`$123F8`. In play that is `$125AA`;
  during the start-of-level countdown it is `$1255E` (colour 8 black at line `$3C`).
- **Every field** the level-3 handler:
  - copies the palette at `($124B6)` (`$1258C` in play) into the colour moves at `$123BA`
    (`$12468`);
  - points COP2LC at `$123B4`;
  - writes the sub-list address `($124BE)` into `$123F6`/`$123FA`, and turns sprite DMA off
    while it is `$1255E`;
  - reads the keyboard (`$C4B6`: the key byte `$C526`) and the input byte `$11E72`.
- **Frame end** (`$DE3E`, called from the main loop at `$DA52`):
  1. Swaps the screens: toggles the parity `$11E67`, and points COP1LC at the copper list
     of the screen just drawn. On odd parity that is `$12370`, and `$11E36` is incremented
     (stopping at 15360); on even parity it is `$12324`.
  2. While the start-of-level countdown `$11E0C` runs, it uses the fixed pointers `$1256A`
     and `$1255E`. Otherwise it copies `$124AE` and `$124B2` into the palette pointer
     `$124B6` and the sub-list pointer `$124BE` (`$DEA4`).
  3. Loops on `$E28C` (wait for the next field) until `$11DEC − $11ECC ≥ $11E4C`. It stores
     the wait's exit count in `$11ECC` and the fields since the previous exit in `$11ECE`.

  `$11E4C` is 2 and nothing writes it, so the game runs at most 25 fps. Every frame waits for
  at least one field boundary, so frames are whole fields.
- **Main loop** (`$DA30`–`$DB0E`, in play), in order:
  1. Draw: `$DF94`, `$D636`, `$D374`, `$10B48`, `$CD14`, `$DDC0`, `$9D10`, `$D362`.
  2. Frame end.
  3. World, once a frame: `$ED76` (shot spawn), `$A1F6` (player and object state).
  4. Player, per elapsed field: `d0` = `$11ECF` (the low byte of the elapsed count, the only
     reader), clamped to 3 (fixed at 2 in the attract demo, `$11E06`), runs `$A836`, `$E7AA`
     and `$FD26` that many times, back to back. `$E7AA` takes the input byte `$11E72` (or
     the demo's recorded input) and turns the heading `$11EB4`; the steps of one frame see
     the same input.
  5. World, once a frame:
     - `$A570`;
     - `$E29E` (every object: position += velocity, gravity subtracted from the vertical
       velocity, lifetime counted down);
     - `$F0A6`;
     - `$CC2C` (colour cycling: one word a frame into the shown palette);
     - collision tests (`$F2CA`, `$EE86` twice);
     - the death check.

     None of these is scaled by time.
  6. Presentation, once a frame: `$E32A` (transform and cull) and `$E724` (depth sort).
     They read the world and write only lists the drawing reads; nothing in steps 3 to 5
     reads what they write (byte-level data flow over the benchmark).
  7. `$C536`: keys.
- So the game is **partly coupled**: the player's own turning and movement follow fields
  (identical heading after the same input on the a500 and the a1200-030), but other objects,
  shots, lifetimes, collisions and enemy behaviour step once per frame, tuned for 25 fps.
  - Measured over the same 20 fields: 7 object steps on the a500, 10 on the a1200-030.
  - At 15.7 fps (a500) the world runs at 63% speed. With frames longer than 3 fields the
    player loses time too (467 of 500 player steps on the a500).
  - Raising the cap to 50 fps as it stands would double the world speed.
  - Outside the world block, two counters also count frames: `$11E36` (every second
    frame), whose low byte is added to an index the world uses at `$10858`, and `$11E0C`.
    `$11E67` is the screen swap itself, so it belongs to presentation. The world's palette
    writes through `$124B6` (`$A50A`, `$CC48`) reach the screen at the next field.
- **RNG**: a pointer at `$7000` into a 4 KB word table at `$6000`.
  - Each call (92 call sites, the idiom `movea.l $7000,a0; ror.w (a0); move.w (a0)+,d0`,
    wrapping at `$7000`) rotates and returns the next word.
  - `$D95A` seeds it with no entropy (rotates the table to a fixed value); the attract demo
    sets `$7000 = $6000`.
  - The title loop (`$DCFC`) calls it once per field until fire, so the level depends on
    how many passes the title made. In play, only world code calls it (`$A570`, `$F2CA` in
    the benchmark).
  - The game reads no beam position, CIA timer or TOD. Its only hardware reads are the
    blitter busy bit, `INTREQR`, the fire button, the keyboard and `JOY1DAT`.
  - Within one machine setup the game is deterministic under `DETERMINISTIC=1`. Across
    setups or builds the frame timing changes the RNG stream and the world. The 68030 with
    and without FS-UAE's MMU emulation already differ, though WHDLoad uses no MMU on a 68030
    by default.

## Drawing

- **Objects**: `$DDC0` walks the sorted list. The primitive `$BB22`, about 72 calls a frame,
  draws with blitter strips (`$B2C4`, `$B6BC`, `$C56C`) and busy-waits on the blitter
  (`btst #6,$DFF002`) between them. The blitter is busy in only 5% of the chip slots.
- **Clear**: `$DF94` clears the back buffer with the CPU (`movem`, through `$DFE6` and
  `$DFCC`): about 32 KB a frame.
- **Horizon**: `$CD14` with the plotter `$CA52`–`$CB8C`, CPU only. The plotter modifies its
  own code:
  - per call it writes plane operations into the slots `$CB0A`–`$CB1C` and `$CB80`–`$CB84`
    from the table at `$12A40` (`move.l a5,$CB0A` at `$CA86`, and so on);
  - it caches the last colour at `$CA4E`, read PC-relative at `$CA6C`.

  On a 68020 or later with the instruction cache on, stale slots could execute; this is not
  verified.
- **Double buffering**: two screens of four planes, `$68000`–`$6FCFF` and
  `$78000`–`$7FCFF` (40 bytes × 200 lines × 4). The frame end shows the one just drawn by
  switching COP1LC ("Frames and time").

## Performance

The level-1 benchmark ([development.md](development.md), "Benchmark"): 500 fields,
fire held, one enemy destroyed. The a1200-fast gives the a1200's figures: the game never
uses fast memory.

| | a1200-030 (no MMU emulation) | a1200 (68020/14) | a500 |
|---|---|---|---|
| fps | 25.00 (the cap) | 24.70 | 15.70 |
| fields between frames | 2 (216 of 249), 1 or 3 for the rest | 2 (235 of 246) | 3 (127), 4 (14), 5 (10), 2 (5) |
| work per frame, fields (wait excluded, interrupts included) | median 1.06, p90 1.24, max 1.82 (the explosion), mean 1.12 | median 1.19, p90 1.38, max 2.11, mean 1.25 | median 2.40, max 4.52 |
| frames needing more than one field | 229 of 249 | 241 of 247 | all |
| pacing wait | 44% of the CPU | 38% | 18% |
| DMA slots | free 26%, CPU 43%, bitplane 22.5%, blitter 4.9% | free 30%, CPU 40% | free 31%, CPU 40%, blitter 3.1% |

On the a1200-030 the cap, not the renderer, sets the frame rate. The game is bound by the
chip bus: the 030/50 has 3.5 times the 020/14's clock and does a frame's work only 10%
faster. Shares of all traced cycles on the a1200-030 (inclusive; the call stacks are rebuilt
from the trace and include interrupts that hit a routine):

| Routine | Calls | Share | What |
|---|---|---|---|
| `$DDC0` | per frame | 16.0% | object draw loop; most of it in `$BB22` (18.0%, about 72 calls a frame) |
| `$E32A` | per frame | 10.2% | transform and cull |
| `$DF94` | per frame | 9.1% | the clear; calls `$DFE6` 8 times (5.6%) |
| `$10B48` | per frame | 6.3% | |
| `$CD14` | per frame | 5.4% | horizon |
| `$BFB8` | 9 a frame | 5.9% | |
| `$E7AA` | per field | 1.9% | input and player |
| `$E724` | per frame | 0.9% | depth sort |
| world (`$ED76`, `$A1F6`, `$A570`–`$EE86`) | per frame | about 2% | |
| `$E28C` | | 44.7% | the pacing wait |

The hottest single instructions outside the wait (`$C0E0`–`$C162`, `$B7C8`–`$B84C`,
`$D3F2`–`$D44A`) are each under 1%; there is no single hot loop.

The CPU's chip accesses outside the pacing wait, per field (`tools/chipprofile.py`,
classified by the DMA map below):

| | a1200-030 | a1200 |
|---|---:|---:|
| code fetches | 8359 (50%) | 7700 (48%) |
| screen writes / reads | 3710 / 671 (26%) | 3679 / 665 (27%) |
| CPU-only data reads / writes | 2109 / 266 (14%) | 2156 / 264 (15%) |
| stack (`$7FD00` up) reads / writes | 431 / 921 (8%) | 453 / 913 (9%) |
| blitter sources, copper, audio, sprites | 119 (under 1%) | 119 |

A chip access costs the 030 about 29 clocks on average. Code, CPU-only data and the stack
(73%) can move to fast memory; the screens cannot. The CPU-only data are:

| Region | Reads / writes per field | Kind |
|---|---:|---|
| `$1000`–`$3FFF` | 869 / 126 | object arrays (base registers) |
| `$11000`–`$11FFF` | 273 / 29 | variables |
| `$C000`–`$10FFF` | 199 / 27 | variables and tables inside the program |
| `$12000`–`$122FF`, `$12700`–`$12FFF` | 197 / 0 | tables (`$12A40`: the horizon plotter's slots) |
| `$59000`–`$5FFFF` | 299 / 0 | tables |
| `$20000`, `$28000`–`$29FFF`, `$17000` | 198 / 0 | tables |
| `$0000` page | 44 / 80 | low variables |

Code fetches are almost all from `$B000`–`$F000`; the window executes code from `$5296` (a
sprite-pointer routine in the level-3 handler) to `$124AC`. The program's references, in
the window's 3994 executed instructions:
- 640 `abs.l` operands;
- 442 `d16(An)` with a displacement of `$400` or more, into arrays through base registers;
- 81 address-like `#imm.l`: code pointers such as `move.l #$8C2E,$8266` (audio
  continuations), data and DMA addresses such as `move.l #$82BE,$DFF0B0`;
- 17 absolute `jsr`/`jmp`;
- 4 PC-relative data reads: `$C536` reads the key byte `$C526`, `$C5CC` the jump table
  `$C5D6`, `$CA6C` the colour cache `$CA4E`, `$E402` a table at `$E408`. Outside the
  window, `$C558` reads `$C526` too.

DMA in the benchmark window (256-byte pages; other levels, the title and other sounds can
add more):

| Channel | Regions |
|---|---|
| bitplanes | `$68000`–`$6FCFF`, `$78000`–`$7FCFF` |
| blitter A/B (sources) | `$20300`–`$205FF`, `$3F100`–`$41FFF` (in parts), `$70000`–`$715FF` |
| blitter C/D | inside the screens |
| copper | `$12300`–`$126FF` (the palettes at `$1255E`–`$125A9`, which only the CPU reads, share these pages) |
| audio | `$7000`–`$80FF`, `$8200`–`$82FF` (inside the program: the chip copy must stay) |
| sprites | `$5400`–`$59FF` |

## Limitations

- No caches beyond the instruction cache (`resload_SetCACR` enables only `CACRF_EnableI`).
- 512 KB chip only; nothing is relocated to fast memory, so a frame costs nearly the same on
  a 68020/14 and a 68030/50 ("Performance").
- The white-colours bug is unexplained (ReadMe).
