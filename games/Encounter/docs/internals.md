# Internals

What is known from reading JOTD's 1.2 slave (`src/EncounterHD.s`) and the installed
`disk.1`; nothing here has been traced or measured yet.

## The installed game

`tmp/game/Encounter/disk.1` (473088 bytes) is Harry's Patcher image of the original disk
(the install package's `encounter.imager`; its source, `source/encounterimager05.asm`,
ships in `Encounter.lha` but is not in JOTD's repository). The game is a non-DOS
trackloaded program: no hunks, no files, absolute addresses. Offsets below are `disk.1` file
offsets, with the address the slave loads them to.

## Slave header

`ws_Version` 10, flags `WHDLF_Disk|WHDLF_NoError|WHDLF_EmulTrap|WHDLF_EmulDivZero`,
`ws_BaseMemSize` `$80000` (512 KB, the whole game in chip memory), no ExpMem
(`USE_FASTMEM` is never defined), no Kickstart: a direct slave. Quit key `$5D`
(numeric `*`). `resload_Control` reads `CUSTOM1` (unused) and `BUTTONWAIT`.

## How it loads

The slave does the original boot's work with `resload_DiskLoad` (disk 1) and skips the
boot block's own MFM trackloader:

| Step | `disk.1` | Address | What |
|---|---|---|---|
| 1 | `$8C00`, `$400` bytes | `$400` | the boot block code (`DOS\0` at `$400`) |
| 2 | `$0000`, `$7E00` bytes | `$68000` | the title picture: 16 colours at `$68004`, planes from `$68080` |
| 3 | `jsr $4BC` (file `$8CBC`) | | the boot code's title routine: copies the four planes to `$78000`, sets DMA, sprites, the copper list at `$528` and the palette, returns |
| 4 | | | with `BUTTONWAIT`, waits for the left mouse button or the port 2 fire button; otherwise the title is shown only while the next load runs (under `WARP=1` it is gone within a few seconds) |
| 5 | `$9000`, `$69530` bytes | `$1AD0`–`$6B000` | the program and its data (file offset = address + `$7530`) |
| 6 | | `$6000`–`$13000` | decrypted in place: per word, a 16-bit shift-register key (seed `$3491`; `asl #3`, `eor`, two `roxl`, `eori #$AAAA`) XORed into the word. This replaces the original protection, which failed on 68020+ (Harry's 1.1) |
| 7 | `ENHIGH`, `$90` bytes | `$91E2` | the high-score table, when the file exists |
| 8 | | | the patches below, DMACON `$8390`, ADKCON `$B500` (as the boot code sets them), cache flush, `jmp $D7E2` (file `$14D12`: the game's start, stack at `$7FFFE`) |

Because of step 6, the file bytes at the patched addresses are encrypted; the original
instructions below are read from the decrypted image.

## Patches

All are written to memory after the decryption; addresses with their `disk.1` offsets.

| Address | File | Original | Patch |
|---|---|---|---|
| `$6C` | | (unset) | level 3 vector to `INT3`, which clears INTREQ `$0380` and returns, until the game installs its own (`$804E`, at `$E1A0`, file `$156D0`) |
| `$94C6` | `$109F6` | `clr.b $939B` (6 bytes) | `jsr SAVEHIGH`: the same `clr.b`, then `resload_SaveFile` of `$91E2`, `$90` bytes, to `ENHIGH` |
| `$C4D2` | `$13A02` | `moveq #75,d1; dbf d1,*` (6 bytes): the keyboard handshake delay, a CPU-speed loop | `jsr keyhp` (below) |

Inside `keyhp` (the raw key, already decoded, is in `d0`):

- `DBFD1` with `d1 = $50`: `divu #$28` gives 2, so it waits for three changes of the
  vertical beam position byte (`$DFF006`), two to three raster lines, independent of the
  CPU.
- The quit key (`_keyexit`, `$5D` unless `QUITKEY` overrides it) calls `resload_Abort`
  with `TDREASON_OK`.
- Key `$5B` (the ReadMe's numeric `]`) writes 0 to `$DFF101` (BPLCON0's low byte), BPLCON2
  and BPLCON3, and `$0011` to BPLCON4: the workaround for the rare white-colours bug the
  ReadMe mentions, which on an AGA machine looks like stale AGA bitplane control state.

The game's own exception vectors make the header flags work: the boot block runs a
`trap #0` through `$80` (at `$420`, file `$8C20`), and the game points the division-by-zero
vector `$14` at an `rte` (`$E288`, file `$157B8`, set at `$E1BE`, file `$156EE`). With the VBR moved by WHDLoad, `EmulTrap` and
`EmulDivZero` forward those exceptions to these vectors; this is the ReadMe's "no more need
for NOVBRMOVE (division by zero avoided)" in 1.2.

The source's `ifeq 1` block (clearing `$69666`–`$6B000`, patching `$69A8A` and
`$69A9C`) and the commented-out quit patch at `$D7F6` are not assembled.

## Limitations

- No caches beyond the instruction cache (`resload_SetCACR` enables only `CACRF_EnableI`).
- 512 KB chip only; nothing is relocated to fast memory.
- The white-colours bug is unexplained (ReadMe).
