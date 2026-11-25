# Internals

## Loading

A kick13 slave (`slv_Version` 17, `WHDLF_NoError|WHDLF_Examine` and kick13's
`WHDLF_EmulPriv`, `BOOTDOS`, `HDINIT`, `CACHE`, `NO68020`): 512 KB BaseMem, 1.25 MB
ExpMem, quit key F10. `_bootdos` opens
dos.library, reads CUSTOM1, and unless CUSTOM1 (`C1:B:Skip Intro`) is set loads `title`,
patches it (an empty list) and runs it. It then loads `golf`, takes a CRC16 over `$18`
bytes at offset `$12E` of the first segment to tell the version (`$E70A` v1.50, SPS
2010; `$371D` v1.53, SPS 2481), patches it with `resload_PatchSeg` and runs it with a
fake command line, then quits.

`golf` is 52 code hunks (data lives in the code hunks). Four of them are `MEMF_CHIP`:

| Hunk | Size (v1.53) | Holds |
|---|---|---|
| 2 | `$101C` | code (`$0`-`$363`), two flags (`$372`, `$373`), sprite images (`$374`-) |
| 20 | `$780` | the CIA-B timer and vertical blank interrupt code (`$0`-`$4A9`), their variables and the keyboard table (to `$5B3`), the copper list (`$5B4`-) |
| 24 | `$144` | the memory check at start (code and its message) |
| 27 | `$27C` | sprite data |

`title` is 10 hunks; its hunk 3 (`MEMF_CHIP`, `$864`) holds the intro's interrupt code
and variables (`$0`-`$125`) and then a pointer table and copper data.

## The game's cache handling

On a 68020 or later (`AttnFlags` >= `AFF_68020`) the game writes `$0808` to `CACR` through
`Supervisor` (hunk 0 `$2E4`, v1.53), which clears and disables both caches, and adds 100
to the word at hunk 0 `$648`. StingRay's slave skips the `CACR` write; the add stays.

The renderer modifies its own code. Every site ends with a `jmp` to the next instruction
(the 68000 prefetch idiom):

| Version | Hunk | Writes | Modified code | `jmp` |
|---|---|---|---|---|
| v1.53 | 12 | `$502`-`$5CC`: opcodes (`addq #8`/`#1`, `add.l`/`sub.l`), displacements | `$5E2`-`$600`, the span loop | `$5DC` |
| v1.53 | 12 | `$6FA`-`$738`: `bclr`/`bset #6` on two opcodes (`add.l`/`sub.l`) | `$78A`, `$790` | `$748` |
| v1.53 | 14 | `$30`-`$42`: four immediates | `$2F2`, `$2FA`, `$336`, `$36C` | `$48` |
| v1.50 | 12 | as v1.53 | `$5DA`-... | `$5D4` |
| v1.50 | 12 | `$6F0`-`$740`: an opcode byte and two immediates | `$7E8`-`$7F8` | `$746` |
| v1.50 | 12 | `$790`, `$838`, per pixel: the index d4 (0-3) into a displacement byte | `$79F`, `$847` | `$796`, `$83E` |
| v1.50 | 14 | `$2A`-`$36`: three immediates | `$2B6`, `$2BE`, `$37E` | `$3C` |

With the instruction cache on and the slave skipping the game's switch-off, V1.01's
renderer ran stale code: with WHDLoad's `CACHE` the first hole drew no landscape, and the
a1200-030 with 24-bit fast RAM crashed with an illegal instruction in hunk 3.

## Slave patches

PatchSeg offsets count the segments' data end to end.

| Version | Offset | Hunk | Patch | By |
|---|---|---|---|---|
| v1.50 | `$2DA` | 0 `$2DA` | skip to `$2E8`: the `CACR` write | StingRay |
| v1.50 | `$1546C`, `$15476` | 13 | `jsr getFIB`/`getFIB2`: the course list reads into the slave's FileInfoBlock instead of one it overwrites, so every course is listed | StingRay |
| v1.53 | `$2E4` | 0 `$2E4` | skip to `$2F2`: the `CACR` write | StingRay |
| v1.53 | `$15478`, `$15482` | 13 `$170`, `$17A` | as v1.50 | StingRay |
| v1.50 | `$2A879`, `$2A87F` | 44 `$A61`, `$A67` | the sample end count `-2` becomes `-3` (below) | Vesuri |
| v1.53 | `$2AA8B`, `$2AA91` | 44 `$A6B`, `$A71` | as v1.50 | Vesuri |

On a 68020 or later (`PLCACHE150`, `PLCACHE153`, Vesuri):

| Version | Offset | Hunk | Patch |
|---|---|---|---|
| v1.53 | `$14544`, `$146B0`, `$1597C` | 12 `$5DC`, 12 `$748`, 14 `$48` | `jsr _flushcache` over the `jmp`: the cache is flushed after each modification |
| v1.50 | `$14520`, `$14692`, `$15964` | 12 `$5D4`, 12 `$746`, 14 `$3C` | as v1.53 |
| v1.50 | `$146DC`, `$14784` | 12 `$790`, 12 `$838` | the per-pixel `move.b d4,` into the displacement of `move.b (0,a6,d0.w),d6` and its `jmp` become `adda.w d4,a6`, the read, `suba.w d4,a6`, `bra.s` on: no code is modified, no flush per pixel |

`title` (`PLTITLE`, Vesuri): `PL_S` at `$2614` (hunk 8 `$78`, 12 bytes). The intro's music
routine sets two channel counters with `move.b #-2,(0,a2,d0.w)` and `(1,a2,d0.w)` (a2 hunk 8
`$1A6`), but d0 holds the sample's length in words there, not the channel as in the game's
copy of the routine (golf hunk 44 `$A64`). Each sample start, from the audio interrupt,
wrote two `$FE` bytes up to 64 KB past hunk 8: under WHDLoad into the 9500-byte buffer that
follows it (hunk 0 `$C04`), from which `P1.BLK`, `P2.BLK` and `P3.BLK` (`INTROGFX.LZ`) are
unpacked into the panorama (hunk 0 `$BEC`). A sample starting while a picture sat there broke
its byterun stream: the bottom rows of that picture became noise, at random, more often on
fast machines. Nothing reads the counters, so the writes are skipped.

The same music routine stops channels 0 and 1 mid-sample when the intro ends or is clicked
away (hunk 8 `$F6`, called from hunk 0 `$774`), and on the audio interrupt that reloads the
list's last sample (hunk 8 `$BA`). Paula holds its last output byte at volume 64 (the
interrupt path clears channel 0's volume only): a level left on until the game's first
sample. `PL_PS` at `$2692` (hunk 8 `$F6`) and at `$2656` (hunk 8 `$BA`, then skip to `$D2`)
call `_audiooff`: channel 0's interrupt off (else the request the current word's end raises
can start the next sample before the click path disables it at hunk 8 `$FE`), DMA off, the
two channels' interrupt requests cleared, and a zero word written to `AUD0DAT` and
`AUD1DAT`. Paula plays that word after the current one, sets the request and idles on 0. The
interrupt path also keeps the list pointer (hunk 8 `$128`) on the `-1`, so a later interrupt
stops again instead of reading past the list. The intro always ended before the list did in
the captures, so the `$BA` path was never reached there.

`PL_PS` at `$259C` (hunk 8 `$0`, the music's start) calls `_introstart`, which centres every
intro sample first ([samples](#samples)), and at `$25E8` (hunk 8 `$4C`) `_sndprep` gives the
player the sample's length.

`golf` with a chip memory word (`PLCHIP150`, `PLCHIP153`, Vesuri; skipped if `_bootdos`
cannot allocate the 8 cleared bytes of chip memory `SILENT`):

| Version | Offset | Hunk | Patch |
|---|---|---|---|
| v1.50 | `$2A8A4` | 44 `$A8C` | `jsr _silence`, then skip to `$AA8` |
| v1.53 | `$2AAB6` | 44 `$A96` | `jsr _silence`, then skip to `$AB2` |

After starting a sample the game loops both channels on two zero words in hunk 44 (`$1236`
v1.50, `$123C` v1.53) and counts the first channel's audio interrupts from -2 (v1.53 hunk 44
`$A68`; the handlers from `$AF8`), switching the pair off on the second. Two faults left the
channels holding a level while off, which Paula keeps outputting: a pop at the end of each
sample, and another when the next one set its volume.

- The second interrupt comes when Paula has fetched the sample's last word, before the zero
  words play, so the channel stopped on the sample's last byte, and only the first
  channel's volume is cleared. This happens on every machine. Counting from -3 plays one
  silent block first.
- Hunk 44 is not a chip memory hunk, so from fast memory Paula fetched whatever chip memory
  lay at that address. `_silence` loops on `SILENT` instead.

An audio capture of the first hole on the a1200-fast (`SDL_AUDIODRIVER=disk` with
`--audio_driver=sdl`, AmigaXDev's `headless-fsuae.md`) showed it: with 2.0b's first build a
bird sample left the outputs at +2046 and +472 until the next sound, about 2 s; with the count
from -3 they returned to 0.

`golf` also has `PL_PS` at `$2A834` (v1.50, hunk 44 `$A1C`) and `$2AA46` (v1.53, hunk 44
`$A26`): `_sndprep` reads the sample's length for the player.

`title` and `golf` then go through `MoveCode` ([caches and fast memory](#caches-and-fast-memory)).

### Samples

The samples (`INTROSND.LZ`, `SOUNDS.LZ`) have a 32-byte header (`STEVEH`, the rate index at
5, the length at 7-8 little-endian) and data that holds 0-69, with silence at 35 (the game's
sounds start and fade to 34-36), played as signed bytes. Every sound therefore sat on a level
of +35 × volume (+2240 at 64), which each start and end of a sample stepped to and from: the
pops at the start and end of every sound and the offset under the intro's music, on every
Amiga. Most samples end in a zero byte. Both programs find the samples by walking the headers
(length + 32 to the next `ST`: title hunk 0 `$B1C`, golf hunk 44 `$856` v1.53, `$858` v1.50),
and the last sample of each group `golf` loads gives a length 32 bytes too long, so it ran on
into the next group's header, loaded over its end: noise at the end of four sounds.

`_sndprep` (a0 the header) returns the length cut at a header in the sample's last 40 bytes,
and on a sample's first play subtracts 35 from its data, but the trailing zero bytes, and marks
the header `STEVEh`. The header's length is left alone: both walks read it. In the game the
first play does the work (up to 6365 bytes); the intro's samples (about 112 KB) are centred
at the music's start instead, not in its audio interrupt.

In audio captures of the first hole (a1200-fast, v1.53 and v1.50, and the a1200-030 with
`CACHE`), the birds' average output went from +1640..+1900 to -3..-16, and the step at their
ends from 310-1544 to 15-62, at the same spread. The intro's music averages about -300 to -450
(its samples average about 30 rather than 35) instead of +1200 to +2500.

## Caches and fast memory

`MoveCode` (after the patches) moves the code part of each `MEMF_CHIP` hunk to fast memory
and leaves the DMA data in chip memory:

| File | Hunk | Moved part | Stays in chip |
|---|---|---|---|
| `golf` v1.53 | 2, 20, 24 | `$0`-`$373`, `$0`-`$5B3`, all `$144` | sprites, the copper list |
| `golf` v1.50 | 2, 20, 24 | `$0`-`$373`, `$0`-`$55D`, all `$144` | as v1.53 |
| `title` | 3 | `$0`-`$125` | the pointer table and copper data |

Hunk 27 (sprite data only) stays. `MoveCode` loads the file again, allocates each moved
part (`MEMF_FAST`, plus 8 longword slots), copies it, and walks the file's `HUNK_RELOC32`
blocks: a reference into a moved part gets the new address, and a reference *from* a moved
part is fixed in the copy. A `lea d16(pc),An` in a moved part that points into the chip
part cannot reach it, so it becomes `movea.l slot(pc),An` with the address in a slot:
`golf` v1.53 2 `$19E`, `$20E`, 20 `$228`, `$384`, `$398`, `$3A4`; v1.50 2 `$19E`, `$20E`,
20 `$21E`, `$32E`, `$342`, `$34E`; `title` none. The old chip copies stay allocated, unused.
Without fast memory the allocation fails and that hunk stays where it is.
