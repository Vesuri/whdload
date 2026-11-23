# Internals

## Loading

A direct slave (`ws_Version` 17, `WHDLF_NoError|WHDLF_ClearMem|WHDLF_EmulTrap`): 512 KB
base memory, no ExpMem, quit key F10, data from the RawDIC image `Disk.1`. It turns on the
instruction cache (`resload_SetCACR` 1, 1; the data cache stays as WHDLoad sets it), loads
the first `$B400` bytes of the image to `BASE` = `$57FE4` and identifies them by CRC16
(`$67E7`, SPS 3025; anything else `TDREASON_WRONGVER`). The image has 10 sectors a track
of which the game uses 9, so the slave packs the first nine tracks to 9 sectors each in
place. It sets CIA-A's LED bit, enables interrupts (`INTENA` `$C000`), patches the program
and jumps to `BASE+$10D4`.

Every later load goes through the game's track loader, which the slave replaces: the
parameter block at `BASE+$C98` holds the start track, the length in tracks and the
destination, and the slave reads `(track-2)*5120` bytes in from the image (tracks of 10
sectors).

## Slave patches

Offsets are into the program as loaded, from `BASE` (so the file offset into the packed
9-sector stream).

| Offset | Patch | By |
|---|---|---|
| `$A3E` | `rts`: drive motor off | Harry |
| `$A78` | `rts`: drive motor on | Harry |
| `$ADC` | `rts`: step to track 0 | Harry |
| `$B9C` | `rts`: read the protection track | Harry |
| `$669C` | jump to `Loader`, the image loader above | Harry |
| `$4B2` | `jsr CheckKeys`: stores the key at `$58C6B`, handshakes the keyboard with a 3-line delay, and quits on the quit key | Harry |
| `$51C` | `rts`: the game's CPU-timed keyboard delay | Harry |
| `$C0A` | skip to `$C6C`: the protection track check | StingRay |
| `$30C` | `jsr` a blitter wait before writing `BLTCON0` `$09F0` (not with CUSTOM1) | StingRay |
| `$6D4` | `jsr`: acknowledge the vertical blank interrupt twice, for 68040/060 and fast chipsets | StingRay |
| `$14BE` | jump to `EdgeStep` (2.0b): the edge scan converter's stepping (`$14BE`..`$165B`) without self-modification | Vesuri |
| module `$F2E` | `jsr SfxDmaWait` (2.0b), applied by `Loader` when it loads the sound module to `$20000` and the bytes match: the effect trigger's DMA-off wait, below | Vesuri |

CUSTOM1 (`C1:B:Disable Blitter Waits`) drops the `$30C` wait.

`EdgeStep` keeps the step (+1 or -1) in d3 instead of writing `addq.w`/`subq.w #1,d1` into
the loops, and has a loop for each x-major mode instead of writing the `bcc.s` displacement.
It leaves registers, N, Z, V, C and memory as the game's code does; `tools/edgecheck.py`
(`make check`) compares the two under Unicorn's 68000 on random edges.

## Sound

The sound module is loaded to `$20000` (offsets below are into it). The game calls it from
wrappers that save every register and run with interrupts off (`SR` `$2700`): `$0` starts
the music, `$E9C` an effect, `$F62` is the vertical blank player.

- **The effect trigger** turns the channel's DMA off (`$EEC`), sets up the channel, waits
  (`move.w #512,d0; dbf d0,*` at `$F2E`) and sets the channel's flag (`$F36`); the next
  vertical blank player tick sets the effect's registers and turns DMA on (`$10B2`). That
  tick can come straight after the trigger returns, so the wait is the only time the DMA is
  sure to be off, and Paula restarts a channel only if it sees it off. The `dbf` is 5134
  cycles or more, 11.3 raster lines on the 68000 (more under blitter-nasty), under one line
  on the a1200-040 (beam read at entry and exit). 2.0b's `SfxDmaWait` waits for 13 changes
  of the `VHPOSR` line (12 lines or more) on every CPU; measured 13 lines on the a500 and
  the a1200-040.
- **The player's resume** (`$FE4`..`$1014`, at the end of an effect) turns DMA off, sets
  four registers and turns it on again, with no wait on any CPU; FS-UAE logs it as "DMA wait
  hack DISABLED" (under 60 instructions, so it emulates Paula not restarting) on the a500
  as on the a1200-040. It is the game's behaviour on a 68000 too, so it stays.
- The music's DMA-off and DMA-on (`$236`, `$2D2`) are on separate ticks; `$F3C` is a
  `dbf`-to-self nothing calls.

## Rendering and panning

Offsets are from `BASE`, as above; the addresses below `$8000` are the game's absolute
low-memory variables and tables.

- **Display**: 320x200, 4 bitplanes (`BPLCON0` `$4200`), planes 8000 bytes apart, two
  buffers at `$60000` and `$78000`; `$58C76` holds the back buffer, so its changes count
  frames. The view is 192 lines.
- **The blitter** is used only for the scroll step at `$2E2`: four A-to-D plane copies (19
  words by 192 lines, or 20 by 184 for a vertical step), with blitter-nasty set (`DMACON`
  `$8440` at `$342`). Everything else is drawn by the CPU.
- **A pan step** renders a 128-pixel strip into the strip buffer at `$70000` (160 bytes a
  row, word-interleaved planes), then scrolls it in over 8 frames: each blits the front
  buffer into the back buffer shifted by one word (or 8 lines), copies one word column from
  the strip (`$493E`, from the pointer `$5C848`) and swaps at the next field. Holding D on
  the a500 gives 8 swaps one field apart, then a 17 to 29 field pause for the next strip.
- **The polygon path**: the edge scan converter (`$1440`) writes left and right edges to the
  tables at `$7B00`/`$7D00`; the span filler (`$18B4`) fills each span with `movep.l`
  read-modify-writes, 8 pixels of each plane at a time, through pattern tables at `$56100`,
  `$56800`, `$56C00` and `$56E60`.
- **Self-modifying code** (fixed in 2.0b, `EdgeStep`): the edge scan converter rewrote its own `subq.w`/`addq.w #1,d1`
  opcodes (`$1546`, `$15BE`, `$15F6`, `$1630`) and a `bcc.s` displacement (`$15C3`) for each
  edge. On a 68040/060 with the instruction cache on, the cache keeps the old instruction,
  so edges step the wrong way: faces go missing and white triangles appear. With WHDLoad's
  `NOCACHE` the a1200-040 drew correctly, and turning off only the emulated data cache did
  not help. The 68020's 256-byte cache rarely holds the patched loop, so it drew correctly.
  A census over 4085 traced a500 fields (`tools/sentinel.py census`, `tools/smc_census.py`:
  the route, pans in all four directions, boulder, robot, transfer, U-turn, hyperspace, pause,
  the music and sound keys, ESC) found no other instruction the CPU wrote and executed.

MEASURED (FS-UAE, landscape 0000, D held, 250 fields; fields between swaps):

| Machine | Strip pause | Scroll-in |
|---|---|---|
| a500 | 17 to 29 | 1 |
| a1200-040, `NOCACHE` | 12 to 21 | 1 |
| a1200-040 (draws wrongly) | 4 to 9 | 1 |
| a1200-040 with `68040-NOMMU` (draws wrongly) | 4 to 9 | 1 |

MEASURED (a500, 60 fields traced while panning; share of CPU cycles): the span filler
(`$18B4`) 31%, the CPU held by the scroll blits (the instruction after the `BLTSIZE` write,
`$356`) 17%, the edge scan converter (`$1440`) 14%, the field wait (`$358`) 8%, `$11D8` 5%,
`$6BDA` 3%, `$17A2` 3%, the sound module at `$20000` 2%.

MEASURED (2.0b with `EdgeStep`, `tools/render_check.sh`, the fields its ten pan steps take):
a500 360, a1200 197, a1200-030 with `MMU DCACHE` 164, a1200-040 166 (`CACHE` 166, `DCACHE` 127,
`NOCACHE` 263), a1200-060 104 (`DCACHE` and `BRANCHCACHE DCACHE` 104).

## Limitations

The other fast-CPU hazards in [open-work.md](open-work.md) step 6 are not yet checked.
