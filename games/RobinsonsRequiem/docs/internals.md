# Internals

What CFou!'s v1.2 slaves do, from their source (`src/`) and the installed executables.
Offsets are into the game's `START` executable: hunk data offsets, with the file offset in
brackets, and for the AGA game's MAIN script, offsets from a name in it. `docs/performance.md` has the
measurements and the renderer's functions by cost.

## How it loads

Both slaves are KickEmu `BOOTDOS` slaves (`HDINIT`, WHDLoad interface `slv_Version` 17, the
AGA slave 20 for `ws_MemConfig`; `WHDLF_NoError|WHDLF_Examine|WHDLF_ClearMem`, quit key F10). The current directory is the
version's data drawer (`slv_CurrentDir`: `data-ecs` or `data-aga`); `_bootdos` opens
dos.library, reads the first 300 bytes of `start` and takes their `resload_CRC16` against
`$dd8e` (the abort on a mismatch is commented out, so the check does nothing), `LoadSeg`s
`start`, applies the game patches below to the loaded segments (the `resload_PatchSeg` list
is empty), and calls the first hunk with the argument line `"\n"`.

The game is Silmarils' engine of the period (Ishar 3 shares the AGA bitplane patch): a
script interpreter in `START` with the data files (`*.CO` for ECS, `*.DO` for AGA, `*.DAT`,
`*.IO`) loaded through dos.library.

| | ECS (`RobinsonsRequiem`) | AGA (`RobinsonsRequiemAGA`) |
|---|---|---|
| KickEmu | `kick13.s`, `kick34005.A500` | `kick31.s`, `kick40068.A1200` (or `.A4000`), `INITAGA` |
| Chip / ExpMem | `$100000` / `$40000` | `$1A0000` / `$100000` (`MemConfig=1`: `$40000`, v1.2's), `WHDLF_ReqAGA` |
| Options | `BLACKSCREEN`, `SETPATCH`, `IOCACHE=12000` | `CACHECHIPDATA` (v1.2: `CACHE`), `IOCACHE=11000`, `STACKSIZE=6000` |
| `START` | 102,068 bytes; hunks: 0 code `$2f30`, 1 data `$ea30`, 2 code `$1ec8`, 3 code `$10d0`, 4 code `$1154` | 121,452 bytes; hunks: 0 code `$3a30`, 1 data `$103d8`, 2 code `$543c`, 3 code `$1154` |

Hunk 1 is a DATA hunk but holds code, the interpreter among it.

## ECS slave patches

- **dos.library `Info`** (`-$72`) jumps to `int_dos`: it fills the InfoData with a
  validated (`$52`), 10,000-block `DOS\0` disk and returns -1.
- **Manual protection** (`PARADOX_CRACK`, the one assembled; `PRESTIGE_CRACK` is the other
  choice): hunk 1 `+$f98` [`$4890`], `addq.l #2,a3 / rts` (`548b 4e75`, checked first), becomes
  `jmp $100.w`; `$100` holds `jmp _crackPARADOX`. That routine checks the script bytes at
  `$12/$18/$19(a3)` for `$53/$62/$56`, writes `$1e` over all three, then does the replaced
  `addq.l #2,a3 / rts`. The unassembled Prestige variant would hook hunk 1 `+$dd6` [`$46ce`]
  (`101b 4880`), the same instruction the AGA slave hooks.
- After `LoadSeg`: INTENA `$7fff`, then `$e028` (master, EXTER, VERTB, PORTS only). This is
  probably the "speed problem fixed on ECS version" of the ReadMe's v1.2 entry.

## AGA slave patches

Before dos.library is opened (`_patch`):

- A 2 × 80 × 256-byte bitmap and a `$15a × 4`-byte screen structure are allocated (any
  memory) and set as `IntuitionBase->ActiveScreen` (`$38`), height 200, or 256 when
  `_monitor` is `PAL_MONITOR_ID`, plane pointer at `$c0`.
- intuition.library `SetPointer`, `MoveScreen`, `OpenWindow` and graphics.library `SetRast`
  return 0 without doing anything; `OpenScreen` allocates a screen structure and its planes
  (any memory) and returns it.
- dos.library `Info` fills a fixed InfoData (as the ECS one, plus 5 blocks used and 488 bytes per block);
  `DeleteFile` calls `resload_DeleteFile`.

After `LoadSeg`:

- **Bitplanes in chip memory** (`_TakeChipBPL1AdrFixPrep`): hunk 0 `+$452` [`$47e`],
  `move.l $c0(a0),d1` (`2228 00c0`: the game takes the Intuition screen's first plane for
  its own first two bitplanes) becomes `jsr $106.w`, and `$106` holds
  `jmp _TakeChipBPL1AdrFix`, which returns `$190000` (`CHIPMEMSIZE - $10000`), reserved with
  `AllocAbs($bb80)` (three planes of `$3e80` bytes, one more than the two needed); the slave quits with "No enough chip memory in
  KickEmul" when that fails. Under Kickstart 3.1 the plane read could be fast memory. The
  fragment `src/_fixBPL1&2-InFast-Silmarils.s` is the same fix with the offsets for Ishar 1,
  2 and 3 and a trainer `slv_config`; it is not assembled.
- **Manual protection** (`PRESTIGE_CRACK`): hunk 1 `+$2632` [`$6ade`],
  `move.b (a3)+,d0 / ext.w d0 / swap d0` (`101b 4880 4840`, the first longword checked),
  becomes `jsr _prepcrack`. When the byte at `-5(a3)` is 7 it compares the seven bytes from
  `-4(a3)` with two script signatures and, on a match, changes the byte their offset word
  points to from `$14` to `$0a`; then it does the three replaced instructions.
- FMODE (`$dff1fc`) is set to `$f` (64-bit bitplane and sprite fetch) just before the call.

The low-memory jumps at `$100` and `$106` sit in the CPU vector table (user vectors 64 and
65).

## AGA improvements

The changes after v1.2, in the order of `docs/performance.md`'s plan:

1. **START's fast pool kept** (`_fastpool`): with the 1 MB ExpMem (not with `MemConfig=1`),
   hunk 0 `+$196` [`$1c2`], `move.l #0,<hunk 1 +$f4>` (`23fc 0000 0000`, checked first),
   becomes `bra.s +$1a0` (`6008`), so the pool START sized is kept ("Memory" below).
2. **Caches on**: `CACHECHIPDATA` instead of `CACHE`. Without WHDLoad's MMU, `CACHE` left
   both caches off on the 68030 (CACR `$2000`); `CACHECHIPDATA` turns them on with BaseMem
   write-through. The game's one blitter use (hunk 2 `+$5b6`) copies the shown planes into
   the back planes, which the CPU only writes, so no cached data goes stale.
3. **The 3D view's buffers in fast memory** (`_fastblocks`): the block allocator's calls for
   the chunky buffer (hunk 1 `+$a2b2` [`$e75e`]), the renderer's tables (`+$a2ce` [`$e77a`])
   and a table of longwords (`+$a30e` [`$e7ba`]), each `jsr <hunk 0 +$36ee>` (checked first, with the allocator's
   and the free's first instructions), become `jsr _fastalloc`: the same blocks, header
   and handle from the top of the fast pool (hunk 1 `+$100`) down to the objects' frames'
   end (`+$ed82`), 16-byte aligned; from chip as before when there is no pool or no room.
   The free, hunk 0 `+$3748` [`$3774`] (`48e7 8080 2040`), becomes `jmp _fastfree`, which gives a
   block back to whichever pool it is the lowest block of. The hunk 2 64,000-byte chunky
   screens (`+$380e`, `+$38b8`) are left in chip: this walk never allocates them.
4. **The chunky-to-planar conversion** (`_c2ppatch`, `src/c2p030.s`): hunk 2 `+$2e84`
   [`$199b8`], START's row loop, starts with `move.w d6,<hunk 2
   +$2db6>` (`33c6`, checked first with its address), which becomes `jmp _c2p030`. It is
   Kalms' `c2p1x1_8_c5_030_2` with each pass writing through two bases (START's planes 0-1
   are in the slave's reserved block, 2-7 elsewhere) and a row driver with START's
   strides; widths that are not a multiple of 32 pixels go back to START's loop.
   `tools/rr_c2pcheck.py` checks it against START's loop byte for byte under Unicorn.
5. **The sky copy by longwords** (`_skypatch`, `src/sky030.s`): hunk 1 `+$e262`-`+$e291`
   [`$1270e`], START's row loop copying the sky (a resource in the chip heap) into the
   chunky view a word at a time, checked byte for byte (with the address of `<hunk 1
   +$edfe>` at `+$e272`), becomes `jsr _skyrows` and `bra.w +$e292`. `_skyrows` copies the
   same segments (the sky wraps around at its row's end) with aligned longword reads, two
   words a chip access. `tools/rr_skycheck.py` checks it against START's loop under
   Unicorn, the view and the registers the code after `+$e292` reads.
6. **Frame pacing** (`_pacepatch`, `docs/performance.md`, "Workload and instruments" and
   step 6): in 3D mode (hunk 1 `+$ee03`), when the frame routine ends and the object the
   view follows (MAIN's object table `+$ed6c` at the view's `+96`) has a period and comes
   due within the cap (`+$ee6a`), the slave waits until the VBL count passes its next run;
   the next pass, which draws its frame, skips the cap wait. Hunk 1 `+$4b8e` [`$903a`]
   `jsr +$a3a6` (the view's drawing) becomes `jsr _view`, which notes the view's object;
   `+$4b54` [`$9000`] `movem.l (sp)+,d0-a6` and `rts` (`4cdf 7fff 4e75`, the frame
   routine's end) become `jmp _passend`; `+$49e8` [`$8e94`] `move.b <+$ee6a>,d0` (`1039`
   and the address, the cap for the wait at `+$49ee`) becomes `jsr _capwait`, which gives
   0 after a pacing wait. All three are checked first.

## Memory (AGA)

START divides memory itself (hunk 0 `+$162`-`+$290`); the hunk 1 variables:

- **Fast pool** `+$f0`-`+$f8`: `AvailMem(MEMF_FAST|MEMF_LARGEST)` - 50,000, none under
  100,000. v1.2 discarded it (`+$f4` := 0 at hunk 0 `+$196`); kept, it holds MAIN's object
  table and the objects' variable frames (hunk 1 `+$8c7c`: `+$ed6c`-`+$ed82`, 87 KB in the
  jungle), from `+$fc`. `+$100` is set to the pool's end and not used.
- **Chip pool** `+$e4`-`+$ec`: `AvailMem(MEMF_CHIP|MEMF_LARGEST)` - 14,000 (the game ends
  under 295,000). The resource heap grows up from `+$104` (`+$ed5c` base, `+$ed60` top,
  hunk 1 `+$9532`: every loaded file, 969 KB in the jungle), and a block allocator grows
  down from `+$ec` (`+$108` the lowest block): hunk 0 `+$36ee` takes a size in `d0`, puts
  an 8-byte header (size) before the block and returns a handle, an entry of the 16-entry
  table at hunk 1 `+$ef42` whose first longword is the address; hunk 0 `+$3748` frees a
  handle, giving the memory back only when the block is the lowest. Without the fast pool
  the object table is at the heap's base.
- Bitplanes, the copper list (`+$d4`) and the screen structures come from the OS
  (`AllocMem`, the slave's `OpenScreen`), not from the pools.

In the jungle the block allocator holds, from the top: 256 KB and 4 KB for MAIN's scripts
(hunk 1 `+$3480`; the 3D objects' graphics are in the first), the 3D view's chunky buffer
((width + 1) × (height + 1) + 320 bytes, hunk 1 `+$a2b2`), the renderer's tables (34,592
bytes, `+$a2c8`) and a 2 KB table (`+$a30e`).

## The script interpreter (AGA)

`START` holds no game logic: it runs bytecode programs, loaded by name and unpacked into
chip memory. `MAIN.DO` is loaded at boot and holds every phase (logo, language, intro,
options menu, game set-up, level loads); the other `*.DO` are resources and programs that
MAIN loads into numbered slots. Each running program is an object with its own bytecode
pointer (`a3`) and variable frame (`a6`); a frame's bytes are the program's variables.

- Dispatch: hunk 1 `+$25e4` reads an opcode byte and jumps through the word table at
  `a2` (hunk 1 `+$2142`); `$00`-`$ff`, with a second page behind a prefix.
- Some opcodes: `06 w`/`07 l24` call (16/24-bit offset from the next op), `08 b`/`0a l24`
  branch, `11` return, `14 l24` branch when the last expression was 0, `1e`/`1f` evaluate
  an expression (operand types through the table at `a5`, hunk 1 `+$234e`; `06 w` is a byte
  variable of the frame) and store it (types through hunk 1 `+$23f8`), `2f` switch,
  `3d w` free slot, `40 w` create an object from slot `w`, `42` yield a frame, `45 w name`
  load file `name` (`.AO`, mapped to `.DO`) into slot `w`.
- The file-open wrapper is hunk 0 `+$2540` (`Open` at `+$255e`, `MODE_NEWFILE` at
  `+$267e`, `Lock` at `+$2590`); `a3` there points at the name inside the op that loads it.
- MAIN's frame is `[hunk 1 +$eda8]`. Its language byte is `$e68` (0 French, 1 English,
  2 German). The options menu (`prefs`, `prefsu`, `prefsd`: one program per language)
  shows and changes MAIN's `$3838`-`$383f`: difficulty `$383a` (0-2), background sounds
  `$383b`, 3D window `$383d` and level of detail `$383e` (0 HIGH, 1 LOW). Both are 0 at
  boot; the menu starts them at LOW. Neither is saved: `CONFIG.INF` is only read.
- An Esc during the Silmarils logo sets MAIN's `$3928`; MAIN then calls the language
  screen and skips the intro (`flags` goes straight to `baratin*`, `param`, `init3d`,
  `prefs*`). Later, Esc ends the running part only.

### Direct start

`_directstart` (developer builds) replaces hunk 0 `+$2540`'s `bsr.s $24da / bsr.w $294a`
(`6198 6100 0406`) with a `jsr` to a hook that calls both afterwards. At two loads it checks
MAIN's bytes and writes a branch, offsets from the name (`a3`):

| Load | Checked | Written |
|---|---|---|
| `logo.AO` | `+8` `40 0001 0839 38` (create the logo object), `+$603` `96 0000 42` (the path after an Esc in the logo) | `+8` `0a 0005f7`: that path; MAIN's `$e68` = 1 |
| `init3d.AO` | `+$20` `2f 06 0e68 02` (load the menu by language), `+$5f` `07 00051d`, `+$97` `40 0054 0839 38` (create the menu, wait for it), `+$cc` `3d 0054` (free its slots) | `+$20` `0a 00003b` to `+$5f`; `+$97` `0a 000031` to `+$cc` |

The ECS slave's `_directstart` does the same through hunk 0 `+$1af0` (`bsr.s $1a8a / bsr.w $fe`,
`6198 6100 e60a`). Its MAIN differs: the options menu is one program (`prefs`), and the logo
part also loads the pointer, `souris`, into slot 2, which `init3d` creates an object from.
Branching over that load leaves the object's handle at -1, and `init3d`'s next store through
it is an address error (hunk 1 `+$6dfa`), so the logo is skipped in two branches:

| Load | Checked | Written |
|---|---|---|
| `logo.AO` | `+8` `40 0001 0839 20` (create the logo object), `+$6c` `45 0002 "souris.AO" 00 1e 00 ff` (load the pointer; language := none), `+$47b` `a1 96 0000 42` (where an Esc's branch lands) | `+8` `0a 000060` to `+$6c`; `+$79` `0a 0003fe` to `+$47b`; MAIN's `$e68` = 1 |
| `init3d.AO` | `+$32` `45 0054 "prefs.AO" 00` (load the menu), `+$55` `40 0054 0839 20 42 42 42 42` (create it, four yields), `+$6d` `94 0054 0839 20 42` (wait for its end), `+$9f` `3d 0054` (free its slots) | `+$32` `0a 000008` to `+$3e`; `+$55` `0a 000006` to `+$5f`; `+$6d` `0a 00002e` to `+$9f` |
