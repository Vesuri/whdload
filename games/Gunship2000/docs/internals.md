# Internals

How each version loads, memory, and every slave patch. Offsets are into the named file's
first code hunk (its data starts at the file offset given) unless another hunk is named.

## Loading

All three slaves are JOTD's KickEmu slaves with `BOOTDOS`: WHDLoad boots the Kickstart image,
the slave's `_bootdos` makes the assigns and runs the game's program from `data/` through
`dos.library` `LoadSeg`, and quits with `TDREASON_OK` when it returns. `PRELOAD` holds the
files.

| | ECS | AGA | CD32 |
|---|---|---|---|
| KickEmu | `kick13.s` (`kick34005.A500`), `SETPATCH`, `BLACKSCREEN` | `kick31.s` (`kick40068.A1200`), `INITAGA` | `kick31.s`, `INITAGA`, `FORCEPAL`, `DEBUG` |
| Assigns | `gs_dsk1`-`gs_dsk4` | `gs_dsk1`-`gs_dsk4`, `ENV:` to `RAM:` | `CD0`, `Gunship_2000`, `ENV:` to `RAM:` |
| Runs | `Gunship 2000 Intro` (unless `CUSTOM1`), then `Gunship 2000` | `Gunship 2000` | `Gunship 2000` |
| Patches by | `_cb_dosLoadSeg` (name `gs...`) and `patch_main` on `Gunship 2000` | `_cb_dosLoadSeg`: `gs`, `gs2.run`, `Gunship 2000` | `fakepad.s` (lowlevel.library) |

`Gunship 2000` is the front end; it runs `gs` (the base and menus) and `gs2.run` (the
flight). The CD32 slave loads `lowlevel.library` and `nonvolatile.library` from disk
(`USE_DISK_LOWLEVEL_LIB`, `USE_DISK_NONVOLATILE_LIB`), saves the roster through
`nonvolatile.library` to the game drawer, and `fakepad.s` replaces lowlevel's
`ReadJoyPort` (the pad from a joystick and the function keys) and `GetLanguageSelection`
(WHDLoad's language; `CUSTOM4` forces English).

## Memory

| | BaseMem (`CHIPMEMSIZE`) | ExpMem (`FASTMEMSIZE`) | Flags | `slv_Version` |
|---|---|---|---|---|
| ECS | $100000 | $100000 | `NoError`, `Examine`, `EmulTrap` | 16 |
| AGA | $100000 | $100000 | `NoError`, `Examine`, `ClearMem`; stack 13000 | 16 |
| CD32 | $1ff000 | 0 | `NoError`, `Examine` | 16 |

The quit key is $5d (numeric `*`); the ReadMe says F10 and gives the older memory figures.

## Slave patches

ECS, `data/Gunship 2000` (code hunk $800 bytes at file offset $28), by `patch_main`:

| Offset | Original | Patch | Why |
|---|---|---|---|
| $66c | `movea.l $2a,a6; jsr ...` (the install check) | `jmp move1d0rts` (`moveq #1,d0; rts`) | the check passes |
| $78e | `suba.l a1,a1; movea.l $2a,a0` (the second check) | likewise | likewise |

ECS, `data/gs`: `_cb_dosLoadSeg` searches the first 500 bytes of each hunk for
`$43edfffa12d866fc` (`lea -6(a5),a1; move.b (a0)+,(a1)+; bne.s`), the manual-protection
code entry. It is in hunk 98 (code, $cbc bytes at file offset $2a730), at $d0:

| Offset | Patch | Why |
|---|---|---|
| $d0 | `jsr $c0.w`, a `jmp _crackit_1` there | writes the right code for the asked word into the entry buffer (`compute_correct_code`), then the `lea` it replaced |
| $55c | `jsr $de.w`, a `jmp _crackit_2` there | the same for the second prompt (`lea -42(a5),a1`) |

AGA, `_cb_dosLoadSeg` first clears long 0 (`clr.l 0`) on every `LoadSeg`, then by name:

| File, offset | Original | Patch | Why |
|---|---|---|---|
| `gs` (code $5ee0 at file $228), $4970 | `move.l -4(a5),d0` (the code entered) | `jsr $d0.w`, a `jmp crack` there | once five digits are in, replaces the entry with the right code (protection removed) |
| `gs2.run` (code $19014 at file $30), $12780 | `jsr -270(a6)` (`WaitTOF` before `LoadView`) | two `nop` | |
| `gs2.run`, $12834 | `lea $dff000,a5` | `jsr set_copperlist` | writes the copper end `$fffffffe` to address 0 (the game's `COPJMP2` to 0), sets `COP1LC` from the game's copper-list variable |
| `Gunship 2000` (code $6a4 at file $28), $122 | the `Install Gunship 2000` test | skip to $13e | |
| `Gunship 2000`, $16c | an `OpenLibrary` and the test after it | skip to $1f4 | |

`_patch_exe` tells the AGA `Gunship 2000` by `$2c79` at $512; with `$2c79` at $66c (the ECS
layout) it applies the ECS install-check patches instead.

CD32: `_patch_gs2000` returns at once, so its patch list (`$154` two `nop`, `$168` `bra`) is
not applied; the game runs unpatched apart from `fakepad.s`.
