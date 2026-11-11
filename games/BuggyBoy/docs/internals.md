# Internals

What is known from reading Codetapper's 1.3 slave (`src/BuggyBoyHD.s`) and the installed
files; nothing here has been traced or measured yet.

## Slave header

`ws_Version` 17, flags `WHDLF_NoError|WHDLF_EmulTrap`, `ws_BaseMemSize` `$80000` (512 KB,
the whole game in chip memory), no ExpMem, no Kickstart: a direct slave. Quit key `$59`
(F10). `ws_config`: `C1` trainer ("Infinite Time"), `C2` frame rate (below), `C3` CD32
joypad, `BW` button wait. `resload_Control` reads `CUSTOM1`–`CUSTOM3` and `BUTTONWAIT`,
but nothing tests `CUSTOM1`, and `_SetCheat`, which would stop the high-score save, is never
called.

## Versions

The slave tells the versions apart at start:

| Version | Detected by | Path |
|---|---|---|
| Retail, DOS files (the installed archive) | `data/bug.p` exists, CRC16 `$134F` over 46328 bytes | decrypt, relocate, patch |
| Les Fous crack, DOS files | `bug.p` with CRC16 `$1084`, or `bug.o` when there is no `bug.p` | relocate, patch |
| Tenstar pack | `disk.1` boot code: `$14BC00FF` at boot offset `$156` | boot and game patch lists |
| Tenstar pack, second release | the same longword at `$166` | its own lists |
| The Story So Far compilation | `$08280002` at `$102` | its own lists |

Anything else is `TDREASON_WRONGVER`. The installed archive also has a 3392-byte `bug.o`
(a hunk file); because `bug.p` is checked first, it is not loaded.

## How the DOS version loads

1. `resload_LoadFileDecrunch` of `bug.p` to `$3E0`: its 32-byte hunk header ends at
   `$400`, where the code starts. Program offsets below are from `$400`; the `bug.p` file
   offset is the program offset + `$20`.
2. Retail only: decrypt `$2A6C` longwords from `$400` in place. Each nonzero longword gets
   the key `$49946CFD` added, its 32 bits reversed (`roxl`/`roxr` loop) and the key
   subtracted; zero longwords stay.
3. Relocate: the zero-terminated table at program `$A9BC` lists offsets of longwords that
   get the load address added.
4. The patch list below, plus `PL_BugOP_CD32` with `CUSTOM3`. The trainer list
   `_PL_BugOP_Tr` (initial time 0 at `$64E`, no time decrement at `$1626`, no lap bonus at
   `$1E4E`) is assembled but never applied.
5. The `trap #15` vector `$BC` points at the high-score save, the keyboard
   handler is installed (`keyboard.s`), a one-word copper list `$FFFFFFFE` at `$3CC`, colour
   0 black, DMACON `$83D0`, then `jsr $400`.

The game's `AllocMem` calls get a bump allocator from `$10000`, cleared, 16-byte aligned.
Running past `$80000` writes `MEM ERR ` at address 0 and quits.

## Patches (DOS version)

Program offsets (from `$400`).

| Offset | Original | Patch |
|---|---|---|
| `$8`, `$24`, `$40`, `$5C` | `AllocMem` calls (67102, 240000, 63702, 57088 bytes) | `jsr _AllocMem` |
| `$D4` | | `_LoadHighs`: clear the table (`$5D4`), load `BuggyBoy.highs` (640 bytes, XORed with a falling counter) to `$8EA4` |
| `$5E0` | | `'IAN'` fills the default high-score names |
| `$1C86`, `$1C8A` | `lea $FFFF824C,a2` (Atari ST palette) | `$DFF18C`, `nop nop` |
| `$2572`, `$257C`, `$259E`, `$25A8`, `$2610`, `$261C` | dos.library open, check, `Delay`, `Disable`, `CloseLibrary` | `nop nop` |
| `$260A` | `move.l #200,d1` | `jsr _Delay`: 1 s, or until a button with `BUTTONWAIT` |
| `$2622` | error exit (no memory, file error) | `jmp _debug` |
| `$262E` | the file loader | `jmp _LoadFile`: `resload_LoadFileDecrunch`, path before `:` stripped |
| `$2682` | `move.l (a1,d0.w),$DFF080` | `jsr _LockFrameRate` (below) |
| `$29C2` | `clr.b (a0)` after name entry | `trap #15`: the same `clr.b`, then save the table unless the trainer flag is set |
| `$4B9A`, `$4DA6`, `$6696` | INTENA values `$4000`, `$C020`, `$C000` | `$C008`, `$C028`, `$C008`: PORTS enabled for the keyboard |
| `$4BAA`, `$4C72` | BPLCON0 `$4000` | `$4200`: colour bit set (1.1) |
| `$4DB0` | `lea $DFF000,a0` | `jsr _CountFrames`: count one, then the same `lea` |
| `$6650`, `$6674` | `move.w $1E(a0),d0; and.w d4,d0` | `jsr _SoundFixOrig`: the same test, retried for up to 8 raster lines (the lockup when hitting rocks) |
| `$2538` (`CUSTOM3`) | joystick store | `jmp _CD32_Read`: CD32 pad red = fire, forward/reverse = up/down, reverse+forward+play = quit |

The disk versions get the same kinds of patches at absolute addresses (the game loads at
`$70000`), with their own loaders through `resload_DiskLoad` (`$18A8`-byte tracks) and
their trainer lists, which are applied unconditionally. The second Tenstar release has no frame-rate patch and an empty
trainer list (commented out in the source).

## Frame rate control (1.3)

`_CountFrames` counts the routine at `$4DB0`, presumably once per field (unverified).
`_LockFrameRate`, before the game writes COP1LC, waits until the count reaches N and
resets it, which caps the game at one frame per N+1 counts:

| `CUSTOM2` | N | Label |
|---|---|---|
| 0 ("Default speed") or above 7 | 4 | 10 fps |
| 1 to 7 | `CUSTOM2` | 25, 17, 13, 10, 8, 7, 6 fps |

So "Default speed" is the same cap as `CUSTOM2=4`; the labels assume 50 counts a second.
The wait is a busy loop on the counter.
