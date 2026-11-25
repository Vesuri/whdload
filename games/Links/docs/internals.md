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

With the instruction cache on and the slave skipping the game's switch-off, the renderer
runs stale code: on the a1200-030 and the a1200-fast with WHDLoad's `CACHE` the first hole
draws no landscape, and the a1200-030 has also crashed with an illegal instruction in hunk 3.

## Slave patches

PatchSeg offsets count the segments' data end to end.

| Version | Offset | Hunk | Patch | By |
|---|---|---|---|---|
| v1.50 | `$2DA` | 0 `$2DA` | skip to `$2E8`: the `CACR` write | StingRay |
| v1.50 | `$1546C`, `$15476` | 13 | `jsr getFIB`/`getFIB2`: the course list reads into the slave's FileInfoBlock instead of one it overwrites, so every course is listed | StingRay |
| v1.53 | `$2E4` | 0 `$2E4` | skip to `$2F2`: the `CACR` write | StingRay |
| v1.53 | `$15478`, `$15482` | 13 `$170`, `$17A` | as v1.50 | StingRay |

`title` is not patched.

## Limitations

With WHDLoad's `CACHE` the game draws no landscape ([open-work.md](open-work.md)).
