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
| v1.53 | `$1446E`-`$14534` (16) | 12 `$502`-`$5CC` | `PL_PA`: the set-up's writes into the span loop (`$5E2`-`$600`: its first instruction, three displacements, `adda`/`suba` and three `add`/`sub`) go to `_sp1` |
| v1.53 | `$14544` | 12 `$5DC` | `jsr _span1` over the `jmp`: the loop from `_sp1`'s values, the signs on registers; returns to `$60C` |
| v1.53 | `$14666`-`$1469E` (4) | 12 `$6FA`-`$738` | `PL_PA`: the `bclr`/`bset #6` on the opcodes at `$78A` and `$790` go to `_sp2` |
| v1.53 | `$146B0` | 12 `$748` | `jsr _span2` over the `jmp`: the pixel loop `$74E`-`$796`, `d6` and `d7` negated where `_sp2` says subtract; returns to `$798` |
| v1.53 | `$1597C` | 14 `$48` | `jsr _flushcache` over the `jmp`: the cache is flushed after each modification |
| v1.53 | `$14A5A` | 12 `$AF2` | `jsr _copyscr`: the picture to the screen (below) |
| v1.50 | `$14520`, `$14692`, `$15964` | 12 `$5D4`, 12 `$746`, 14 `$3C` | `jsr _flushcache` over the `jmp` |
| both | `$154A6` (v1.53), `$1549A` (v1.50) | 13 `$19E` | `jsr _lzwbuf`: the unpacker's input and dictionary (hunk 23 `$350`, `$348`) in `LZWBUF` instead of the game's chip buffer (below) |
| both | `$179F8` (v1.53), `$17AC8` (v1.50) | 23 `$0` | `jmp _lzw`: the unpacker (below) |
| v1.50 | `$146DC`, `$14784` | 12 `$790`, 12 `$838` | the per-pixel `move.b d4,` into the displacement of `move.b (0,a6,d0.w),d6` and its `jmp` become `adda.w d4,a6`, the read, `suba.w d4,a6`, `bra.s` on: no code is modified, no flush per pixel |

v1.53 draws a course view in hunk 12's driver (`$0`): the set-up, mostly hunk 23's LZW
unpacking of the hole (below), then `DRAWING
COURSE` (`$5E`), `DRAWING BACKGROUND` (`$74`), `DRAWING OBJECTS` (`$82`) into a picture
of a byte a pixel, 320 x 160 (hunk 19 `$1AC`), and `$AF2` to the screen (from `$90`).
`$AF2` takes each pixel's colour from its byte, its region (hunk 0 `$610`), the depth map
(hunk 12 `$BA6`) and a dither step (the table hunk 46 `$C2C`), and calls one of hunk 4's 64
routines (colour c: `bset` or `bclr` of bit c's plane, at `-8000`-`32000` from plane 1),
6 read-modify-writes of chip memory a pixel, straight onto the visible screen.
`_copyscr` runs the same colour code into a row buffer and puts each row into the planes
16 pixels a word (tables from `_c2pinit`, in `C2PBUF`, 3392 bytes allocated at start on
a 68020 or later; without it the game's own copy runs). The two span loops changed their
own code every span and needed a flush each, about 4700 in 25 fields; `_span1` and
`_span2` read the same choices from the slave. `tools/drawcheck.py` runs each against the
game's code in Unicorn: 2000 random spans and pixel runs, and 20 random pictures, equal
(registers, memory, planes).

Measured on the a1200-030 with `CACHE CUSTOM1=1`, from `$0` to `$B8` (the first hole,
one run each; the pin differs between runs), the game's VBL counter (hunk 20 `$4DE`)
read at each address through the gdb stub, before and after:

| Phase | Fields | |
|---|---|---|
| set-up | 35 | 34 |
| `DRAWING COURSE` | 49 | 27 |
| `DRAWING BACKGROUND` | 10 | 10 |
| `DRAWING OBJECTS` | 16 | 16 |
| to the screen | 27 | 2 |
| all | 137 | 89 |

`_lzw` then took the set-up from 34 fields to 8 (below).

On the cycle profiler's 68030 (aprof, `--uae_mmu_model=0`, no data cache) the same
phases took 34.7, 79.3, 11.0, 25.3 and 26.3 fields and 34.6, 53.9, 11.1, 25.3 and 4.2:
`resload_FlushCache` had taken about 23 of `DRAWING COURSE`'s fields and hunk 4's
routines 20 of the 26. v1.50 plots each pixel straight to the screen inside its span
loops (hunk 12 `$7BA`, `$85C`) and has neither change.

Every file the game loads goes through hunk 13 `$B6`: a 122-byte `MDmd` header (byte 5
set: packed, the size at 24), then the data, which hunk 23 `$1E0` unpacks through `$0`:
LZW, 9- to 13-bit codes least significant bit first, 256 clears the table and 257 ends.
It reads 16 KB at a time (dos `Read`, refilled once a code starts at byte 16374 or later)
into hunk 23 `$350`, keeps 8192 dictionary entries of a prefix word and a byte (hunk 23
`$348`), both in the game's 64 KB chip buffer (hunk 13 `$44E`, allocated `MEMF_CHIP` at
hunk 19 `$98`, also a scratch screen and sample buffer elsewhere), and puts each string on
the stack and out a byte a call (`$194`), which counts it and, with hunk 23 `$397` set,
stops at the count in `$35C` (hunk 31 `$1032`). The two versions' hunk 23 differ only in
the dos base's address (`$1C`). On a 68020 or later `_lzwbuf` points the input and
dictionary at `LZWBUF` (64 KB `MEMF_FAST` allocated at start, its last 16 KB each code's
string length), and `_lzw` unpacks with the same reads, output and variables, writing each
string backwards from its length by its chain. It skips dictionary entries from 8192 on,
which the original writes below the dictionary; no file gets there (each clears the
table when it is full). Without `LZWBUF` both run the game's code.
`tools/lzwcheck.py` runs both on every packed member of every file of the four drawers
(545, whole and with 2 random limits each) in Unicorn: registers, variables, output,
input, dictionary and the memory under it equal.

On the a1200-030 with `CACHE CUSTOM1=1`, from the ready screen's OK to the first hole's
view (one run each, the game's VBL counter at hunk 30 `$0`, `$1C0`, `$1E0` and hunk 12
`$0`, `$5E`, `$B8`), V1.01 (no `CACHE`), the 2.0b build before `_lzw`, and with it:

| Phase | V1.01 | before | 2.0b |
|---|---|---|---|
| the overview map's files (hunk 30 `$0`-`$1C0`) | 160 | 133 | 26 |
| the map's wait (to `$1E0`) | 39 | 62 | 157 |
| the description and the hole's files (to hunk 12 `$0`) | 289 | 234 | 37 |
| the course view's set-up | 43 | 34 | 8 |
| `DRAWING` and to the screen | 124 | 55 | 47 |
| all | 655 | 518 | 275 |

The map stays up at least 180 fields from hunk 30 `$12` (the counter hunk 20 `$52A`,
waited on at hunk 30 `$1C0`) unless clicked: by design, and now most of its time. The
description screen is shown while the hole loads, so now briefly.

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

`PL_PS` at `$7A4` (hunk 0, the top of the credits' scroll loop at `$7A0`) calls
`_creditpace`. The loop turns 98 times as fast as the machine runs, while the credits in it
change on the field timer hunk 3 `$120` (step 0 the first credit, 1 blank, 2 the second, 3
blank, from field 480 to 660); after it hunk 0 `$726` draws `COPYRIGHT ...` straight onto the
screen. With the original slave on the 68000 `custom` setup the loop took 490 fields (5 a
turn) and ended in step 3; with 2.0b's code in fast memory, the a1200-030 with `CACHE` took
388 and ended in step 2, so `COPYRIGHT` was drawn over the second credit. `_creditpace` waits
at the loop's top until 5 fields have passed since the last turn, on the VBL's fourth counter
(hunk 3 `$124`, which nothing else uses), and keeps the click flag's test (hunk 3 `$11D`): the
loop now ends in step 3 after 490 fields on the 68000 and 488 on the a1200-030 and a1200-040
with `CACHE` (read at hunk 0 `$718` through the gdb stub), and the scroll runs at the 68000's
speed.

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
`$A26`): `_sndprep` reads the sample's length for the player; and at `$2A678` (v1.50, hunk 44
`$860`) and `$2A87E` (v1.53, hunk 44 `$85E`): `_sndwalk` converts each sample of the group
loaded at the start as the walk enters it in the table.

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
and, if the header still reads `STEVEH`, converts the data (but the trailing zero bytes) and
marks the header `STEVEh`. The header's length is left alone: both walks read it. The
conversion is a 256-byte table (`SNDTAB`, built by the assembler): the game's sounds go from
35 to 0 scaled by 3.5 (-123..119, about the full 8 bits; some samples reach both 0 and 69, so
one factor serves all and keeps their balance), the intro's from 30, their average (the
music holds no silence), scaled by 3.25 (-98..126). Both are about 11 dB louder at the same
volume.

`golf` loads its samples two ways (hunk 44, v1.53): one group at its start (`$814`, into its
own 17000-byte chip buffer at `$CC8`, when 231144 bytes of chip memory are free), which
`_sndwalk` converts in the walk at `$856`; and the others one list at a time just before they
play (`$79A`, into the 14000-byte buffer at `$CCC`, dropped from the table after), which the
player's `_sndprep` converts. The marker keeps a sample the loader returns from its cache
(hunk 13 `$116`) from being converted twice. The intro's samples (about 112 KB) are converted
at the music's start (after the table's build), not in its audio interrupt.

In audio captures of the first hole (a1200-fast, v1.53 and v1.50, and the a1200-030 with
`CACHE`), centring on 35 took the birds' average output from +1640..+1900 to -3..-16, and the
step at their ends from 310-1544 to 15-62, at the same spread. With the scaling, the a1200-030
capture's peak went from 6028 to 10752 and its quiet stretches stay within 2 of 0, and the
intro's music averages -120 to -220 (-300 to -450 centred on 35 unscaled, +1200 to +2500
before). A game dump (a1200-fast) shows the start group converted (-98..105, averages about
-1) and the intro's samples at -95..126.

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
