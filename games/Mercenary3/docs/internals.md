# Internals

Addresses are offsets in `Disk.1` unless marked as slave patch-list offsets. The game
image loads to a fixed chip address, so the slave's absolute addresses map to `Disk.1`
by one constant (below).

## Slave

`Mercenary3.Slave` (1,148 bytes, Harry, Graham and Wepl, version 1.2, 29.07.2004) is
identical in the full install and the official installer. The installer's
`src/Mercenary3.slave.asm` is an earlier state of its source: the shipped slave also
has the `PL_W $716` and `PL_P $A858` patches below, a `_waitvb` subroutine where the
source expands the `waitvb` macro inline, and the build date. `src/Mercenary3.islave.asm`
is the RawDIC imager.

`whdload/original/Mercenary3.slave.asm` is the reconstruction: the installer source
with those additions and with Barfly's optimised encodings written out (`moveq`, short
branches, PC-relative `lea`, `cmpi` and an `abs.w` operand). vasm `-no-opt` rebuilds the
shipped slave byte for byte (`make original`).

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
| `$716` | `PL_W $8200` | the operand of the game's `move.w #$8380,dmacon`: enable master DMA only, without copper and bitplanes |
| `$1E30` | `PL_S 8` | skip a ROM access |
| `$205A` | `PL_P _subd0` | replace an empty `dbf` delay with a raster-line wait |
| `$29A6`, `$29BC`, `$29C6` | `PL_P _patch_aud1` | AUD1 interrupt exits: poll the keyboard, acknowledge, `rte` |
| `$2AC0`, `$2C9E` | `PL_P _patch_vertb` | VERTB interrupt exits: the same |
| `$5E8A` | `PL_P _loadgame` | load `Mercenary3.saveN` from the install directory |
| `$5F26` | `PL_P _savegame` | save `$2056` bytes from chip `$5550` |
| `$A858` | `PL_P _dmaon` | enable copper and bitplane DMA after a vertical blank, then copy six bytes and return |

`$A858` is inside the frame publication routine (below): every frame it copies 34 bytes
from chip `$7CC0` to the pointer at `$72B4` with an unrolled `move.l (a1)+,(a0)+` run, and
the patch replaces its fifth to seventh moves. `_dmaon` then copies six bytes and returns, so
each frame copies 22 bytes instead of 34: the moves at `$A85E` and `$A860` never execute
(0 of 75 frames in the profile window). What the last 12 bytes hold is not yet checked.
`_dmaon` also rewrites DMACON and waits for a vertical blank on every frame, not once.

The slave installs its own level-2 handler at `$68` for the keyboard. Its keyboard
poll (`_checkkeyboard`) busy-waits three raster lines for the handshake and stores the
key code at chip `$8`, with `$FF` at `$9`.

## Running

The title picture is followed directly by gameplay: the prison cell on Metis, with the
on-screen clock running from `00-00-00` and the chief prison officer's scripted messages.
There is no attract demo. Walking uses the port-1 joystick (up walks, left and right turn);
`R` toggles running. The cell door opens on the game clock from about two seconds after the
entry; walking into it earlier gives "LOCKED".

## Frame loop and game time

Offsets are `Disk.1` offsets; chip variables are BaseMem addresses, which do not move.

- **Frame publication** (`$5E4B0`): writes `COP1LC` with one of two copper lists, waits
  for the VERTB counter at chip `$529F4` to change (`$5E4D6`), counts the frame in chip
  `$7180` (`$5E4DE`), and stores the fields since the previous frame in chip `$52954`
  (`$5E4F0`). Then the copy that the slave's `_dmaon` patch interrupts.
- **World ticks** (`$5E040`): the fields since the previous frame, clamped to 4..8, are
  stored in a word inside the code (`$5DF46`); the loop `$5E060..$5E082` runs that many
  ticks (`$5A644`, `$5C8F8`, `$5F724`, `$5F328`). One tick is one field of game time:
  walking moves the player (chip `$714E`) 6 units, turning changes the heading (chip
  `$7156`, 1024 per turn) 2 units. A separate path at `$5C9EA` adds velocity times the
  unclamped field count to the position.
- **In-game clock**: chip `$57B0..$57B3`, the displayed seconds in `$57B3` and a 16-bit
  fraction in `$57B0`. It advances by the same amount every field (`$A790` per 25 fields,
  about 1.31 game seconds per real second) whatever the frame rate.

So game speed depends on the frame rate outside 6.25..12.5 fps:

| Frame rate | Fields per frame | Ticks per frame | World speed |
| --- | --- | --- | --- |
| below 6.25 fps | over 8 | 8 | slower than real time |
| 6.25 to 12.5 fps | 4 to 8 | equal to fields | real time |
| above 12.5 fps | under 4 | 4 | faster than real time |

Measured with `tools/sim_speed.py`, same input on the same fields: in the walk the
A500-equivalent published a frame every 13–14 fields and moved 48 units per frame
(8 ticks); `a1200-fast` every 5–7 fields and moved 30–42 (5–7 ticks). Over the route the
A500-equivalent walked at 62% and turned at 71% of `a1200-fast`'s speed while the clock ran
identically. No measured frame was shorter than 5 fields, so the lower clamp is read from
the code, not observed.

## Measurements

`a1200-fast` (68EC020 14 MHz, 2 MB chip, 8 MB fast, cycle-exact), the 500-field route of
`tools/route_profile.py` from the game entry. Two boots gave identical call stacks,
per-field totals, frame timestamps and final screenshot; three adjacent instructions
differed by 3 cycles in total.

| Item | Share of CPU cycles |
| --- | --- |
| slave `_waitvb`, from `_dmaon` once per frame | 14.7% |
| game's wait for the VERTB counter (`$5E4D6`) | 6.3% |
| other game code (all in chip RAM) | 78.8% |
| WHDLoad outside the slave | 0.2% |

- 75 frames in 500 fields: 7.51 fps, 6.66 fields per frame.
- Chip-bus DMA slots: CPU 38.8%, bitplane 22.3%, refresh 1.8%, audio 0.3%, copper 0.1%,
  free 36.8%. No `STOP`.
- The game and its data sit in the slave's 512 KB chip BaseMem, so on this machine every
  game instruction fetch and data access competes with display DMA; the fast RAM holds
  only WHDLoad and the slave.
- The game is assembly with one supervisor stack for its main loop and interrupts, so the
  reconstructed call tree roots everything under interrupt frames; use the self-cycle
  tables. Outside the waits no single routine exceeds 1.5%.
