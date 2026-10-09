# Powerdrome internals

## Inputs and loader

Supported input: PAL original, Retroplay `Powerdrome_v1.0_0140.lha`, Galahad/Fairlight slave 1.0 (22 May 2003).
Both supplied archives contain the same 1,592-byte slave; neither contains source.
`whdload/original/Powerdrome.s` reconstructs it and rebuilds byte-identically with vasm.

The header declares WHDLoad interface 15, flags `NoError|EmulPriv`, BaseMem `$80000`,
ExpMem `$40000`, loader `$132`, F10 exit (`$59`), and no CUSTOM options.
It is an OS game: the old slave loads Kickstart 1.3 through `resload_LoadKick`, patches it,
and boots an OFS disk image. Expansion memory is entirely the Kickstart image; the game
and OS live in 512 KB chip RAM. Disk startup is `loadwb` then `endcli >nil:`.

The LoadSeg callback at slave `$142` identifies `endcli`; its hunk offset `$4` starts with
`movea.l $164(a2),a4` (`286a0164`). The slave replaces six bytes with a jump to slave `$18c`,
which opens dos.library and loads `Powerdrome:PD`. It searches PD for `2f0e4dfa` and replaces
six bytes at game `$843c` with a jump to slave `$1ca`. This returns Copylock value `$766cc95c`;
the legacy registered-user check precedes it. No renderer or simulation patches exist.

`pd` is 111,072 bytes. It has one CODE hunk, file offset `$20`, length `$18548` (99,656 bytes),
followed by HUNK_RELOC32 (2,841 relocations to hunk 0) and HUNK_END. Code and mutable data share
this hunk. Entry jumps to game `$4fc0`. It is predominantly assembly with absolute relocated
references, so routine names use static and observed call targets rather than C prologues.

## Original Kickstart patches

These offsets are relative to the Kickstart image; targets are slave-hunk offsets.
The patch list starts at slave `$254`. It adapts memory/Exec, graphics, trackdisk reads and
writes, disk changes and LoadSeg. No source-level meanings are inferred beyond the decoded list.

| Kickstart offset | Patch | Argument |
|---|---|---|
| `$00132` | `W` | `0000` |
| `$0061a` | `P` | `slave:0326` |
| `$00592` | `P` | `slave:032a` |
| `$0025a` | `W` | `0000` |
| `$00546` | `P` | `slave:0332` |
| `$01354` | `P` | `slave:0338` |
| `$015b2` | `PS` | `slave:0342` |
| `$014b6` | `PS` | `slave:035a` |
| `$00422` | `PS` | `slave:036a` |
| `$03012` | `I` | `` |
| `$004f4` | `L` | `ffffffff` |
| `$04cce` | `S` | `0x4` |
| `$06d70` | `PS` | `slave:039e` |
| `$06d86` | `PS` | `slave:03b6` |
| `$0ad5e` | `PS` | `slave:03d6` |
| `$0aecc` | `S` | `0x18` |
| `$0af96` | `P` | `slave:03c0` |
| `$0b00c` | `P` | `slave:03c4` |
| `$0d5be` | `PS` | `slave:03f4` |
| `$2a3b4` | `P` | `slave:0428` |
| `$2a5d8` | `I` | `` |
| `$2a0e2` | `P` | `slave:04d8` |
| `$29cfa` | `P` | `slave:0428` |
| `$2a6d6` | `PS` | `slave:04e4` |
| `$2af68` | `I` | `` |
| `$2af6e` | `I` | `` |
| `$2a19c` | `I` | `` |
| `$2960c` | `P` | `slave:0516` |
| `$04984` | `P` | `slave:0418` |
| `$33ef0` | `PS` | `slave:05ae` |
| `$3c9b6` | `PS` | `slave:05b6` |
| `$36e4c` | `PS` | `slave:056e` |

## Display and timing: static findings, pending gameplay validation

- Game `$5684` is the installed VBL server. It samples mouse/input state, increments the long
  at game `$48fe`, and sets `a6+$494` as a VBL handshake. The main state base is game `$a6e`.
- Game `$59b6` reads CIA-A TOD high/middle/low, differences the prior sample at game `$f9a`,
  multiplies the delta by four and adds it to the clock at game `$f96`. This is called from
  the VBL server every fourth field and from main code. Other code can adjust this clock.
- Game `$7f7a` updates the clock, differences the previous frame timestamp (`a6+$218`), clamps
  that delta to 8..50 and stores the word at `a6+$21c`. It then exchanges bitmap pointers.
  Physics reads this word at `$ccf2` and `$d56c`; a constant-step model would be incorrect.
- Game `$8056` calls `$7f7a`, calls graphics.library ScrollVPort and clears the VBL handshake.
  It is a candidate frame marker, but multiple non-racing paths call it. Frame validation is pending.
- The renderer waits for the VBL handshake at game `$112a6`.
- The menu's idle timeout at `$12ec6` compares elapsed clock units with 18,000 and returns
  12,345 to its caller. This enters the recorded title demo, not a race.
- RNG seeding at `$11db4` mixes the clock into `a6+$62`, then pilot-name words are XORed in.
  The title route repeats without a seed override; racing remains unverified.

## Development slave and reproducible title-demo profile

`whdload/Powerdrome.s` uses unmodified WHDLoad 20 KickEmu sources, interface 17, one disk,
512 KB chip for the guest and 256 KB expansion for Kickstart. It retains the EndCLI redirection
and Copylock replacement, with a signature check at game `$843c`. No cache enablement or
performance change is added. In VERIFY builds only, CUSTOM5 replaces the name-entry key-ready
and key-read calls at `$13772` and `$1377c` with ready/Return responses. The shipped original
and byte-identical rebuild both reach the name screen; the fixture-enabled modern rebase boots
through it into the automatic title demo. State equivalence against the original is pending. The old Copylock replacement also returns
the legacy registration tag in D2 (2001 with this WHDLoad); the development replacement only
sets D0. Audit that side effect before claiming equivalence.

The title demo's `$107d6` advances a recorded camera index (`a6+$292`) by its step
(`a6+$294`, initially 2) per rendered frame. It calls the shared 3D renderer and moves an
inset across the title background. `$1067e` is its post-render display-update call and the
capture anchor. This demo therefore plays faster when rendering is faster, independently
of the separate clock-delta-based racing motion; do not conflate the two timing models.

Fixed title-demo windows at revision `02dbc27` use the development VERIFY slave with CUSTOM5=1, PAL, WHDLoad 20.0
and 100 fields. Two fresh A500 boots have identical initial chip RAM, CPU instruction records
and DMA records throughout. Every image matches except the three rightmost host-border columns,
which the comparator excludes. An independent read-only breakpoint counter exactly reproduces
both machines' complete per-field frame patterns.

| Machine | Frame intervals / PAL fields | Demo fps |
|---|---:|---:|
| 68000, 512 KB chip, 1,536 KB slow, no fast | 18 / 93 | 9.7 |
| A1200, 68EC020, 2 MB chip, 4 MB fast, no slow | 25 / 95 | 13.2 |

The second machine still runs the game in chip RAM; fast RAM holds KickEmu and host support.
These are demo drawing rates, not racing baselines or a performance improvement.

On the A500, the trace records 100 game VBL callbacks and 408 level-3 entries. DMA slots: 31.2% free,
27.1% CPU, 17.2% blitter, 22.5% bitplanes (remainder refresh/copper).
Self attribution: game `$10df2` 21.8%, `$15ee8` 20.8%, `$1609c` 7.0%; verify boundaries with
instruction hotspots before selecting a replacement. KickEmu's complete WaitBlit routine
uses about 23.1% of recorded cycles, including its CIA delay reads. A detector counting only
busy-bit tests and branches substantially undercounts that wait. STOP instruction records
account for about 6.35% of cycles. These are recorded emulator costs, not hardware measurements.

On the 68020, complete WaitBlit accounts for 31.9% of recorded cycles and STOP records 11.6%.
DMA slots: 32.1% free, 20.0% CPU, 23.4% blitter, 22.5% bitplanes. There are 100 game VBL
callbacks and 100 level-3 entries. The trace cycle scale doubles with this CPU backend; do not
compare raw cycle totals across CPUs as elapsed PAL time. FPS comes from field counts.

## Practice input route and movement anchor

VERIFY `CUSTOM5=2` uses the same Enter hook as the title route, then replaces the native
menu key-ready/read JSRs at `$12f6a` / `$130a4` with one `3` keypress. The game's rectangle
table at `$432c` maps item 3 to the top-middle button; its normal dispatcher at `$1207a`
selects Practice. At the pit, `$13c50` / `$13cde` receive one Space keypress. Each hook covers
one complete six-byte JSR; no static branch enters an overwritten instruction's interior.
No input fixture is present in the normal build.

After accepting Space, the native code performs its stationary departure delay, then calls
`$1475c`. The first loop iteration at `$14764` is the capture anchor: it draws the ship at
successive vertical coordinates from `$144cc` (51, 50, 50, 45, ...), moving out of the pit.
The later `$1020e` routine handles the cockpit departure path. A capture starting at `$14764`
includes the visible pit launch, the screen transition and subsequent cockpit gameplay.

The A500 practice-launch capture has 500 consecutive PAL fields and 500 game VBL callbacks,
71,050,998 recorded CPU cycles, and 6,205,664 instruction records (all have PCs). Its first
100 fields match the short-cap reference's initial chip memory and CPU/DMA records exactly,
validating that lifting the host profiler command cap does not alter that portion of gameplay.
Self costs over the full launch window: `$15ee8` 26.7%, `$159e8` 12.6%, `$10df2` 8.5%,
`$15810` 5.9%; KickEmu WaitBlit 5.6%. These include departure/loading work and inferred routine
boundaries, so they should not be presented as steady-state racing costs or a speedup.
