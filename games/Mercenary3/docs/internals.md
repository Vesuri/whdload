# Internals

Addresses are offsets in `Disk.1` unless marked as slave patch-list offsets. The game
image loads to a fixed chip address, so the slave's absolute addresses map to `Disk.1`
by one constant (below).

## Slave

`Mercenary3.Slave` (1,148 bytes) is identical in the full install and the official
installer, whose `src/Mercenary3.slave.asm` is its source (Harry, Graham and Wepl,
version 1.2, 29.07.2004). Whether that source rebuilds the shipped bytes is not yet
checked. `src/Mercenary3.islave.asm` is the RawDIC imager.

| Field | Value |
| --- | --- |
| `ws_Version` | 10 |
| `ws_Flags` | `NoError`, `Disk`, `EmulTrap` |
| `ws_BaseMemSize` | `$80000` (512 KB, all chip) |
| `ws_ExpMem` | 0 |
| KickEmu | none: a direct (no-OS) game |
| `ws_keyexit` | raw `$41` (Backspace; the source comment says F10). Raw `$78` also quits |
| Options | none |

Boot sequence in `_boot`:

1. `resload_DiskLoad` `Disk.1` `$0..$7D80` to chip `$4000`: a title picture whose
   palette and four planes are shown for one second (`resload_Delay 50`).
2. Clear chip `$100..$80000`, then load `Disk.1` `$9000..$767B0` to chip `$5350`.
   A chip address `A` in the game image is therefore `Disk.1` offset `A + $3CB0`.
3. Point four game variables at the slave's keyboard bytes (chip `$8`/`$9`). On a 68040
   or later only, rewrite eight code locations to use vectors at chip `$C0..$CC`.
4. If the word at `Disk.1` `$5DE60` is `jsr abs.l` (`$4EB9`), this is the copy-protected
   version and the slave replaces the call with three `moveq #0,d0`. The supplied install
   is that version.
5. `resload_Patch` with base `$50000`, `resload_SetCACR` with the instruction cache on,
   then jump to `Disk.1` `$4EDB0` with SR `$2700`.

Patch list (offsets relative to `$50000`; add `$53CB0` for the `Disk.1` offset):

| Offset | Patch | Purpose |
| --- | --- | --- |
| `$1E30` | `PL_S 8` | skip a ROM access |
| `$205A` | `PL_P _subd0` | replace an empty `dbf` delay with a raster-line wait |
| `$29A6`, `$29BC`, `$29C6` | `PL_P _patch_aud1` | AUD1 interrupt exits: poll the keyboard, acknowledge, `rte` |
| `$2AC0`, `$2C9E` | `PL_P _patch_vertb` | VERTB interrupt exits: the same |
| `$5E8A` | `PL_P _loadgame` | load `Mercenary3.saveN` from the install directory |
| `$5F26` | `PL_P _savegame` | save `$2056` bytes from chip `$5550` |

The slave installs its own level-2 handler at `$68` for the keyboard. Its keyboard
poll (`_checkkeyboard`) busy-waits three raster lines for the handshake and stores the
key code at chip `$8`, with `$FF` at `$9`.

## Running

On the A500-equivalent machine the title picture is followed directly by gameplay:
the prison cell on Metis, with the on-screen clock running from `00-00-00` and the
chief prison officer's scripted messages. No attract demo has been seen. Traces from
the native build record PCs, in the game image and in the slave in slow RAM.

No code layout beyond the slave's view, timing model or performance measurement has
been established.
