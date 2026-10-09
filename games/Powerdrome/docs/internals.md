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
  12,345 to its caller. Trace its demo transition before relying on it as a gameplay route.
- RNG seeding at `$11db4` mixes the clock into `a6+$62`, then pilot-name words are XORed in.
  Reproducibility is unproven; verification may need a deterministic seed.

## Measurements

The initial ten-field capture validates the profiler only: 88,274 records with PCs,
1,421,008 recorded cycles (approximately 142,102 per PAL field). Its screenshots show the
pit screen, so it is **not a racing baseline**. No performance improvement or racing FPS is
claimed. The game has also been observed rendering a moving cockpit view.

A500-equivalent configuration: 68000, 512 KB chip, 1,536 KB slow, no fast RAM; PAL,
WHDLoad 20.0, original slave. The native unmodified game's behavior on 68020 is unmeasured.
