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
4. **The chunky-to-planar conversion** (`_c2ppatch`, `src/c2p030.s`, `src/c2p040.s`): hunk
   2 `+$2e84` [`$199b8`], START's row loop, starts with `move.w d6,<hunk 2 +$2db6>`
   (`33c6`, checked first with its address), which becomes `jmp _c2p030`, or `jmp
   _c2p040` when WHDLoad's `AttnFlags` (`WHDLTAG_ATTNFLAGS_GET`) have the 68040 or 68060
   bit. `_c2p030` is Kalms' `c2p1x1_8_c5_030_2` with each pass writing through two bases
   (START's planes 0-1 are in the slave's reserved block, 2-7 elsewhere) and a row driver
   with START's strides. `_c2p040` is his one-pass `c2p1x1_8_c5_040`, its one plane
   pointer moved by deltas computed from START's eight plane addresses at each call, run
   once per row, without his cache-line touches (`tst.b`, which read up to 17 bytes past
   the row: the chunky buffer is the fast pool's top block). In both, widths that are not
   a multiple of 32 pixels go back to START's loop. `tools/rr_c2pcheck.py` checks both
   against START's loop byte for byte under Unicorn (as a 68020 and a 68040). The test
   define `C2P040_OFF` keeps `_c2p030` on every CPU.
5. **The sky copy by longwords** (`_skypatch`, `src/sky030.s`): hunk 1 `+$e262`-`+$e291`
   [`$1270e`], START's row loop copying the sky (a resource in the chip heap) into the
   chunky view a word at a time, checked byte for byte (with the address of `<hunk 1
   +$edfe>` at `+$e272`), becomes `jsr _skyrows` and `bra.w +$e292`. `_skyrows` copies the
   same segments (the sky wraps around at its row's end) with aligned longword reads, two
   words a chip access. `tools/rr_skycheck.py` checks it against START's loop under
   Unicorn, the view and the registers the code after `+$e292` reads.
6. **The world on the cap's grid** (`_worldpatch`, `docs/performance.md`, plan step 7): in
   3D mode (hunk 1 `+$ee03`) the objects run by a world count W instead of the VBL count
   ("Objects and the scheduler" below), so they keep the game's own rhythm however long the
   drawing takes. W goes up by the cap (`+$ee6a`) per pass, and each pass waits at its
   end for the VBL count to reach it, so the next list runs at its time and the next
   drawing starts as soon as that list has run (plan step 10; before it the wait was at the
   frame routine's start, where START's cap wait is); at the list's end, while W is a pass or more behind the count,
   MAIN goes round the list again without the frame routine (a catch-up pass), at most
   twice in a row; three passes or more behind (a load, a pause) W is set to the count less
   the cap. Out of 3D mode, or with a cap of 0, the count is the VBL count and the cap wait
   START's; W starts from the count after START's cap wait when 3D mode starts. Hunk 1
   `+$257e` [`$6a2a`] `movea.l <+$ee6c>,a3` (`2679` and the address: the scheduler's due
   test) becomes `jsr _wa3` and `+$6480` [`$a92c`] `movea.l <+$ee6c>,a0` (`2079`, op
   `$36`) `jsr _wa0`, each giving the count; `+$250e` [`$69ba`] `bsr.w +$49b2` and `bra.s
   +$251a` (`6100 24a2 6006`, the list's end) become `jsr _listend`, which returns to
   `+$251a` either way; `+$49e8` [`$8e94`] `move.b <+$ee6a>,d0` (`1039` and the address,
   the cap for the wait at `+$49ee`) becomes `jsr _capwait`, which in 3D mode gives 0 for
   START's wait and notes the drawing's time (W plus the cap, the next pass's count, which
   steps 8 and 9 interpolate to); `+$4b54` [`$9000`] `movem.l (sp)+,d0-a6` and `rts`
   (`4cdf 7fff 4e75`, the frame routine's end) become `jmp _passend`, which waits for W.
   All five are checked first.

7. **The camera between the followed object's runs** (`_view`, `_isample`, part of
   `_worldpatch`; `docs/performance.md`, plan step 8): hunk 1 `+$4b8e` [`$903a`] `jsr
   +$a3a6` (the 3D view's drawing, checked first) becomes `jsr _view`. At each list's end
   `_listend` samples the pose of the object the view follows as `+$48b8` reads it (the
   position words `+0`/`+8`/`+16`, the angles `+24`/`+32`/`+40` plus `+64`/`+68`/`+72`); a
   new pose keeps the one before it, the world count of the change and its interval (since
   the last change, at most the object's period on the cap's grid, 9 fields for the
   player). Before the drawing `_view` moves the camera (`+22`-`+26`, `+52`-`+56`) back by
   (new - old) x (1 - alpha), alpha = (the drawing's time - W of the change) / the
   interval, angles the
   short way round and within ±360; when that camera differs from the last one drawn it
   marks the view changed (bit 7), the view is drawn, and the camera is put back, so
   scripts and `+$48b8` see the game's own. A frame drawn only for the staging then takes
   the changed path (`+$4b94`: the other views' redraw and the swap), so `_view` does the
   unchanged path's per-frame flags for it (`+$4ba8`-`+$4be6`: `+$eef5` from bit 2 of
   the view's `+1`, `+$ef2b`, and the countdown `+$ef2a` of a view with bit 5 set), and
   first marks the view's elements to be projected again as `+$4992`-`+$49ae` does on the
   game's own changes (`_emark`: each in the view's chain, from d3 through `+6`, in state 0
   with byte `+33` not negative set to state 2; the drawing's walk `+$a732` projects only
   state 2 elements, `+$a7d4`, and puts them back in depth order in state 0). The view's
   velocity (`+$4980`, on changed frames only) stays on the game's own changes. No
   interpolation across a jump (a position step over 128, about four of the player's
   walking runs, or an angle over 45 degrees), for a new view or followed object, or out of
   3D mode. The test define `INTERP_OFF` holds alpha at 1.

8. **The other moving objects between their runs** (`_emove`, `_eplan`, `_eapply`,
   `_eundo`, part of `_worldpatch`; `docs/performance.md`, plan step 9): hunk 1 `+$4880`
   [`$8d2c`] `movea.l <+$ed86>,a1` (`2279` and the address, checked first; `+$4792`
   reaches it only when the object moved or turned, with the position's step in d4-d6 and
   the new heading in d7, the old one at `+$edb8`) becomes `jsr _emove`, which keeps the
   step, the world count and the interval (as for the camera) for up to eight objects in a
   table allocated at install (none: no patch). For each drawing `_view` stages those
   objects' 3D elements (chained from the object's `-24` through `+4`): each moved back by
   step x (1 - alpha), its heading (`+36`) too where it is the object's, and put back after
   the drawing; they are projected through the view's marking (item 7). While the camera
   stays, a frame is drawn for the staging only when a staged
   element's screen box (`+12`/`+14`, size `+40`/`+42`, `+16` negative when not
   projected) meets the view's (`+14`/`+16`, size `+18`/`+20`); otherwise the game's own
   redraw of a moved element's region stays (the unchanged path `+$4be8`, `+$5094` → `jsr
   +$a5b6`). Each slot's object is looked up in MAIN's object table at each drawing, so a
   freed object is dropped. No interpolation across a jump (as for the camera: `human`'s
   178-degree turns in the jungle are drawn as the game draws them).

9. **The map in fast memory** (`_mappatch`, `_rowalloc`, `_maprows`, `_mapoff`,
   `_maprect`, `_mapfill`, `_mapinit`; `docs/performance.md`, plan step 10.2). The
   landscape (hunk 1 `+$d88c`) reads the map, a script object's grid of word cells (512 rows
   of 256 in the jungle, 256 KB in the resource heap in chip; the object's `-972` rows,
   `-970` cells a row, `-964` bytes a row, the data behind a handle when `-1` is negative),
   through the row table at `<+$a1de>`, loaded once at `+$d908`; the spans and the far
   samples read through its cell pointers, `+$b986` uses bit 1 of a cell's address, and
   the shading reads the next row (`+$ba8e`). Six sites, all checked first:
   - `+$a30e` [`$e7ba`], the row table's allocation (`jsr _fastalloc` since item 3, with
     a fast pool), becomes `jsr _rowalloc`: START's table, a fast row table and room for a
     copy of the map and the row after it in one block from the top of the fast pool when
     they fit (a3 is the map's object there), freed with the view; START's table alone
     otherwise. Allocated at install instead, 270 KB less in the pool hung the game at the
     Silmarils logo.
   - `+$d908` [`$ddb4`] `movea.l <+$a1de>,a2` (`2479` and the address) becomes `jsr
     _maprows`: while START's table is that block and the map fits, the fast table, into a
     copy at the map's address modulo 16. The copy is made again in full when the map's
     address, size or stride changes or a write below asks for it, the rectangle op's
     writes are copied, and the row after the map is copied at every call.
   - `+$de74` [`$12320`] and `+$df78` [`$12424`], a cell plus the offset of its tile
     (`move.w (22,a1,d1.w),d2` and `adda.l (16,a1,d1.w),a0`, in either order; tiles with a
     negative flag stand on another cell, 89,192 bytes on in the jungle), become `jsr
     _mapoff` and a `nop`: the cell is taken back into the map in chip first, so no offset
     leaves the copy.
   - `+$3b22` [`$7fce`], in the rectangle op (`lea (0,a1,d0.l),a1`, `move.w -964(a0),d1`),
     becomes `jsr _maprect` and a `nop`: the bytes it writes into the map are kept and
     copied at the next drawing. `+$3b74` [`$8020`], the fill op (`movea.l a0,a1`, `tst.b
     -1(a1)`), becomes `jsr _mapfill`, and `+$3540` [`$79ec`], a grid object's set-up
     (`move.l #4,-988(a0)`), `jsr _mapinit` and a `nop`: the copy is made again. These are
     the only writes to a grid in START (the handle's other users, `+$39a0`, `+$aa26`,
     `+$b264`, `+$e828`, read it).
   The test define `MAPCHECK` compares the whole copy with the map at every drawing.

10. **The shade table in fast memory** (`_shadeset`, `_shadeupd`, with item 9's patch;
    `docs/performance.md`, plan step 10.2). The spans shade each colour through the table
    at `<+$ef3c>` (16 levels of 256 colours in the jungle, 4 KB in the resource heap in
    chip), indexed by a level and the colour. The table is set only at the end of the
    view's shade set-up (`+$3056`-`+$30ba`), which also writes the view's `+154` (the
    table), `+158` (the far level) and `+160` (the levels). Each drawing's level steps from
    a start level (levels − 1, 6, 0 or the far level, `+$e622`-`+$e67a`) to the far level
    over the rows and three steps on (`+$dcc2`, the row loop to −3 at `+$de18`), each step a
    fraction of a level, so the spans read the table's first max(levels, far + 1, 7)
    levels. Three sites, all checked first, patched only with item 9's:
    - `+$30b4` [`$7560`] `move.l a1,<+$ef3c>` (`23c9` and the address) becomes `jsr
      _shadeset`, which stores it as before and records how many bytes the spans read when
      those are the table's own: at most 32 levels and a level to spare above the far level
      of every set-up so far.
    - `+$baac` [`$ff58`] and `+$be7e` [`$1032a`] `movea.l <+$ef3c>,a0` (`2079` and the
      address) read `_sshade` instead. `_maprows` (item 9) sets it at every drawing, before
      the spans: a copy in an 8 KB room of `_rowalloc`'s block, 16-aligned, made when the
      table's address changes; the table itself when the row table is not that block or
      the set-up did not allow a copy.
    `MAPCHECK` also compares the copy with the table at every drawing.

11. **The swap without the beam wait** (`_swappatch`, `_swap`, `_pstart`, `_pblock`,
    `_bflush`, `_bblock`, `_bshow`; `docs/performance.md`, plan step 10.2). START's 3D swap
    (hunk 1 `+$4b30` [`$8fdc`] `jsr <hunk 0 +$13e0>` [`$140c`]) waits for line 256, writes
    the plane pointers at the copper list's start (`+$13f6`) and clears INTENA's COPER
    bit, which the list's next move after the pointers sets again (no copper interrupt is
    requested: the bit is a flag). A pass then waits for that bit (`+$49cc` `jsr <hunk 0
    +$13c0>` [`$13ec`]: the new screen shown) and, in the block `+$4a0a`-`+$4a7c`, for the
    VBL's pointer redraw on it (`+$4a14`, `<+$ed99>`, under the lock `<+$ed98>`), copies
    last pass's rectangles from the shown screen into the back one (`+$525a`), puts back
    the background under the pointer there (hunk 2 `+$4ec`) and empties the rectangle list
    (`+$4a76`, `<+$ee08>`). The copper takes the pointers at the field's start, so the
    line of the swap does not change the field the frame shows in. All checked first,
    with `_view` (item 8):
    - `+$4b30` [`$8fdc`] becomes `jsr _swap`: the pointers are written at once, except
      within lines 310 to 1, where the copper takes them; then the bit is cleared.
    - `+$49cc` [`$8e78`] becomes `jsr _pstart`, which puts off the wait and the block
      (with `<+$edd0>` set, the palette's turn at `+$35a4`, both run as before), and
      `+$4a0a` [`$8eb6`] `tst.b <+$ed97>` becomes `jmp _pblock`: the block then, unless it
      was put off, and on at `+$4a80`.
    - The block put off (`_bflush`: the wait for the bit, then START's block, keeping the
      drawing's rectangle `<+$edda>`-`<+$ede3>`, which `+$525a` leaves at the last one it
      copies) runs before the pass's first access to the back screen, at the first of: the
      conversion (hunk 2 `+$2e02` [`$19936`] `movea.l <+$10>,a1` becomes `jsr _c2pld`), a
      2D view (`+$4b5e` [`$900a`] `movea.l <+$ed86>,a1` becomes `jsr _viewent`; bit 1 of a
      view's `+1` clear), the end of the 3D view's drawing (`_view`), and the views' end
      (`+$4ada` [`$8f86`] `clr.b <+$edcf>` becomes `jsr _vend`). The only rectangles are
      added by `+$521e`, from the views' element paths (`+$4dea`-`+$4fa8` through
      `+$5094`), after those points. The 3D drawing's own copy of the view from the shown
      screen (`+$a4fe` [`$e9aa`], with `<+$a1ff>` set) now comes before the block instead
      of after it; both copy from the shown screen under the lock.
    - The back screen's other loads that draw into it (`movea.l <+$10>,An`, each becoming
      `jsr _g10aN`, which waits for the bit after a swap, at most two fields): hunk 0
      `+$1394` [`$13c0`], `+$184e` [`$187a`], `+$1896` [`$18c2`], `+$1994` [`$19c0`],
      `+$1ad8` [`$1b04`], `+$1b50` [`$1b7c`], `+$1b98` [`$1bc4`], `+$1bd4` [`$1c00`],
      `+$1c26` [`$1c52`], `+$1c66` [`$1c92`], `+$1c9e` [`$1cca`], `+$1e20` [`$1e4c`],
      `+$1e7e` [`$1eaa`]; hunk 2 `+$3e` [`$16b72`], `+$618` [`$1714c`], `+$67e` [`$171b2`],
      `+$884` [`$173b8`], `+$9a4` [`$174d8`], `+$a62` [`$17596`], `+$3c1e` [`$1a752`],
      `+$3d5e` [`$1a892`], `+$4364` [`$1ae98`]. Without the beam wait the scripts run
      while the old screen still shows; these keep anything they draw from showing a
      field early. Not hunk 2 `+$4fc`, the VBL's pointer, which runs at the field's start.

12. **Frames between world passes** (`_present`, `_pwhen`, `_now`, `_pneed`, `_cdown`,
    `_prespatch`; `docs/performance.md`, plan step 11). After a world pass's frame,
    `_passend` (item 6) draws more frames until the next pass is due, then waits for it as
    before. Each one is START's frame routine entered at hunk 1 `+$49c2`, as on a pass on
    which no object came due. Entering there skips `+$49b2`-`+$49bc`, which reads four
    operands from the list's script stream (`+$294a`, while `<+$ed37>` is set). Only
    with items 7, 8 and 11 patched. Per-pass work stays on world passes:
    - The countdown of a view with bit 5 set (`+$4bd6` [`$9082`] `subq.b #1,<+$ef2a>`,
      checked first with the `bne.w +$4be8` after it): it becomes `jsr _cdown`, which
      skips it in a presentation frame and leaves Z clear, so a count still running stays
      running. `_view` skips it too in the staged frames it completes (item 7). The count
      is set by a script op (`+$3bd6`).
    - The view's velocity (`+$4980`): it is added only on the game's own changes, and
      `+$48b8` finds the camera unchanged when no object has run.
    - The objects' sampling (`_listend`, items 7 and 8): it runs only at a list's end.
    - The rectangles' copy, the pointer's background and the locks (`+$4a0a`-`+$4a7c`,
      item 11): they run for every frame, as START runs them for every frame routine.
      A frame routine with nothing changed copies an empty list.

    A presentation frame is drawn only when all three hold:
    - The last frame drawn was staged (`_pneed`: the camera, or one of item 8's
      slots). A frame that was not staged shows every pose as the game left it, and no
      object has run since.
    - The field it would show in is later than the last frame's.
    - It is expected to swap at least an eighth of a field before the next pass is due.

    A presentation frame that does not swap (the view unchanged) ends them for that pass.
    The drawing's time (`W_DRAWT`, items 7 and 8) is the field the frame will show in, at
    most W plus the cap (the next pass's count) for a pass's frame, and the next pass's
    count for a presentation frame. Times are in lines: the VBL count × 313 plus the
    beam's line, one field more when VERTB is still requested in the field's first half
    (START's VBL routine counts the field first thing, hunk 1 `+$99ea`). The estimate
    starts from the last frame drawn. Its first access to the back screen came that
    long after its start (`_bflush`, item 11). The access waits for the last swap to
    show, and the swap came that long after the wait. The test define `PRESENT_OFF`
    leaves the frames those of item 11: no presentation frames, the drawing's time W
    plus the cap.
13. **The sky in fast memory** (`_skycopy`, `_skyset`, `_skyget` in `src/sky030.s`, with
    item 5's patch; `docs/performance.md`, plan step 12). The sky's image is a resource in
    the chip heap (its width − 1 at `+2`, its height at `+4`, the pixels from `+8`; 10,248
    bytes in the jungle), the view's `+164` set by the script op `+$30bc`, the row's source
    found at `+$e252` [`$126fe`] and the image's address pushed at `+$e22a`. `_skyrows`
    reads the rows from a copy: `_skyget` makes it when the image's address or size
    differs from the last copy's, at the image's address modulo 16 (the longword
    alignment of the rows is START's), in a 32 KB room `_skycopy` takes from the fast
    memory list at install (none: the image itself, as do images over 32 KB). The two
    single bytes the routine reads for the rows above and below the sky (`+$e1d2`,
    `+$e2c4`) still come from the image. `+$30e0` [`$758c`] `move.l d2,164(a0)` and
    `bsr.w +$7b58` (checked first) become `jsr _skyset` and a `nop`: the image set as
    before, the copy to be made again. `MAPCHECK` also compares the copy with the image at
    every drawing; `tools/rr_skycheck.py` runs every other case from the copy.
14. **The objects' images in fast memory** (`_objpatch`, `_objimg`, `_heapadd`,
    `_heapsub`, `_heapset`; `docs/performance.md`, plan step 13). The 3D view's sprite
    routine (hunk 1 `+$ea3a`) finds an object's image at `+$ea4a` [`$12ef6`] (`adda.l
    (a2),a2` on the object's `+8`): an image of the resource heap in chip (type 28 or 30
    at `+0`, width − 1 at `+2`, height − 1 at `+4`, the pixels from `+8`), 23 of them
    and 33 KB drawn in 27 fields of the jungle's walk. The routine reads it only through
    `a2`: the header, the scaled pixels (`+$eb5c` [`$13008`], `+$ec88` [`$13134`]) and the
    pick test's pixel (`+$ebf4`). `adda.l (a2),a2` and `cmpi.b #28,(a2)` become `jsr
    _objimg`, which gives the routine a copy in fast memory with the flags of the compare:
    a cache of up to 128 images and 64 KB from the fast memory list (taken at install),
    each copy at its image's address modulo 16 and with 64 bytes after the image, found
    by the image's address; a full cache is emptied, an image over 32 KB read where it
    is. The heap changes only through its top `<+$ed60>`: an allocation (`+$9540`
    [`$d9ec`] `add.l d1,<+$ed60>`), the compaction that moves the blocks above a freed
    one down (`+$92ee` [`$d79a`] `sub.l d1,<+$ed60>`) and its reset (`+$8d42` [`$d1ee`]
    `move.l d0,<+$ed60>`). Each becomes a `jsr` to the same store, which also has the cache
    emptied at its next use. All sites are checked first. `MAPCHECK` also compares each copy given with its
    image.
15. **The landscape's inner loop in the instruction cache** (`_landpatch`, `_landinst`,
    `_lloop` in `src/land030.s`; `docs/performance.md`, plan step 15). The landscape (hunk 1
    `+$d88c`) takes a near and a far sample a step in its inner loop, `+$d9ba` [`$11e66`]
    to `+$dbaf`, 3,600 steps a frame in the jungle. `_landinst` checks the loop's words (a
    checksum, its six addresses of hunk 1 taken back to their offsets), copies `_lloop`, the
    loop's common path alone, into a 16-byte aligned block `_landpatch` takes from the fast
    memory list at install (none: no patch), relocates the copy's addresses of hunk 1, and
    makes the loop's two entries jumps into it: `+$d9ba` (the step's start, from the row's
    set-up and the loop's end) and `+$db8e` [`$1203a`] `move.w d3,<+$a226>` (the step's
    end, from the tile objects' path `+$e0e2` and the edges' paths). The copy's 254 bytes fit
    the 68030's 256-byte instruction cache. It uses the 68020's scaled index for the row
    table and the cell (`movea.l (a2,d6.w*4),a0`, `lea (a0,d7.w*2),a0`) and computes the far
    sample's larger and smaller height (`+$db44`-`+$db62`) in four bytes less. Every other
    branch, the map's edges (`+$d9f8`, `+$da14`, `+$daa8`, `+$dac4`), the tile objects
    (`+$db76`) and the row's end (`+$dbb0`), goes back to the same instruction in START's
    loop, which is otherwise unchanged and comes back through the two entries. Its stores,
    calls and flags at every branch are START's. `tools/rr_land.py` checks it against
    START's loop from `tools/rr_snap.py`'s snapshots. The test define `LAND_OFF` leaves it
    out.

## ECS improvements

The changes after v1.2, in the order of `docs/performance.md`'s plan:

1. **The chunky-to-planar conversion** (`_c2ppatch`, `src/c2p000.s`): hunk 2 `+$1a5e`
   [`$1606e`], the start of START's row loop, `move.w d6,a4 / move.w a4,d6` (`3846 3c0c`,
   checked first with the routine's end `+$1b98`, `movem.l (sp)+,d0-a6`, and the address
   of the chunky modulo `<hunk 2 +$46>` at `+$1b8c`), becomes `jmp _c2p000`. It converts
   the same rectangle into the same planes a longword at a time: each pair of chunky
   longwords packed into one longword of nibbles, then four exchanges into the four plane
   words. `tools/rr_ecsc2pcheck.py` checks it against START's loop byte for byte under
   Unicorn.
2. **The sky copy by longwords** (`_skypatch`, `src/sky000.s`): hunk 1 `+$c8b8`-`+$c8e7`
   [`$101b0`], START's row loop copying the sky into the chunky view a word at a time,
   checked byte for byte (with the address of `<hunk 1 +$d454>` at `+$c8c8`), becomes
   `jsr _skyrows` and `bra.w +$c8e8`. `_skyrows` copies the same two segments a row by
   jumping into an unrolled run of `move.l (a0)+,(a1)+`. `tools/rr_skycheck.py ecs` checks
   it against START's loop under Unicorn.

## The AGA's sites in the ECS game

Both STARTs are one program at other offsets (`docs/performance.md`, ECS plan step 6): the
ECS game's hunks 0-2 hold the same code as the AGA's, shorter where it draws 4 planes
instead of 8; its hunk 3 is 4,304 bytes of code of its own, and its hunk 4 is the AGA's
hunk 3 (4,436 bytes of zeros). `tools/rr_sites.py` finds
the ECS site of each AGA improvement's checked bytes: the one place where they stand, with
relocated longwords and the site's own branch displacements left out, chosen by the code
around it when there are several, and with every relocated operand and branch target
mapped one way over all sites. Where the checked bytes differ it checks the ECS site found
by reading both against its own bytes. Hunk offsets, AGA → ECS; items as in "AGA
improvements":

| Item | Sites, AGA → ECS | ECS differences |
|---|---|---|
| 1 | hunk 0 `+$196` → none | START keeps its fast pool (hunk 0 `+$3be`-`+$406` allocates the pool it sized; nothing discards it) |
| 3 | hunk 0 `+$36ee` → `+$2be8`, the free `+$3748` → `+$2c42`; hunk 1 `+$a2b2`, `+$a2ce`, `+$a30e` → `+$891c`, `+$8938`, `+$8978` | the free tests for a null handle first: `48e7 8080 4a80` for `48e7 8080 2040` |
| 4 | hunk 2 `+$2e84` → none | the ECS game's own 4-plane conversion ("ECS improvements" 1) |
| 5 | hunk 1 `+$e262` → `+$c8b8` | ("ECS improvements" 2's site) |
| 6 | hunk 1 `+$257e`, `+$6480`, `+$250e`, `+$49e8`, `+$4b54` → `+$d22`, `+$4b44`, `+$cb2`, `+$30ac`, `+$3218` | |
| 7 | hunk 1 `+$4b8e` → `+$3252` | |
| 8 | hunk 1 `+$4880` → `+$2f44` | |
| 9 | hunk 1 `+$d908`, `+$de74`, `+$df78`, `+$3b22`, `+$3b74`, `+$3540` → `+$bf5e`, `+$c4ca`, `+$c5ce`, `+$21e6`, `+$2238`, `+$1cd6` | |
| 10 | hunk 1 `+$30b4`, `+$baac`, `+$be7e` → `+$184a`, `+$a116`, `+$a4de` | |
| 11 | hunk 0 `+$13c0`, `+$13e0` → `+$c9e`, `+$cbe`; hunk 1 `+$4b30`, `+$49cc`, `+$4a0a`, `+$4a14`, `+$4a1a`, `+$4a2c`, `+$4a46`, `+$4a76`, `+$4a80`, `+$4ada`, `+$4b5e` → `+$31f4`, `+$3090`, `+$30ce`, `+$30d8`, `+$30de`, `+$30f0`, `+$310a`, `+$313a`, `+$3144`, `+$319e`, `+$3222`; hunk 2 `+$2e02` → `+$19ea` | |
| 11, the back screen's loads | hunk 0 `+$184e`, `+$1896`, `+$1994`, `+$1ad8`, `+$1c26`, `+$1c66` → `+$1104`, `+$114c`, `+$12a4`, `+$1366`, `+$13d0`, `+$1404`; hunk 2 `+$3e`, `+$618`, `+$67e`, `+$884`, `+$9a4`, `+$a62` → `+$4c`, `+$3b0`, `+$416`, `+$584`, `+$6b6`, `+$786`; ECS only hunk 0 `+$1232` | `+$1366` found by hand (the loop after it uses word arithmetic where the AGA's is long). None for hunk 0 `+$1394`, `+$1b50`, `+$1b98`, `+$1bd4`, `+$1c9e`, `+$1e20`, `+$1e7e` (8-plane loops, planes 4-7, masks the ECS START does not build) or hunk 2 `+$3c1e`, `+$3d5e`, `+$4364` (the 64,000-byte chunky screens). `+$1232`, the 4-plane copy of a planar image (bit 4 or 5 of its flags), has no AGA site. Every other ECS load of `<hunk 1 +$10>` is one of these, except the VBL's pointer (hunk 2 `+$2ba`, the AGA's `+$4fc`) |
| 12 | hunk 1 `+$4bd6` → `+$329a` | |
| 13 | hunk 1 `+$30e0` → `+$1876` | |
| 14 | hunk 1 `+$ea4a`, `+$9540`, `+$92ee`, `+$8d42` → `+$d0a0`, `+$7b20`, `+$78ce`, `+$7322` | the sprite routine's images are types 24 and 26 for the AGA's 28 and 30: `d5d2 0c12 0018` |
| 15 | hunk 1 `+$d9ba`-`+$dbaf` → `+$c010`-`+$c205` | one `bsr.w` (hunk 1 `+$db68`, to `+$b6ea` → `+$9d54`), so `src/land030.s`'s checksum and its relocated addresses' offsets differ |

The sites' operands, AGA → ECS: hunk 0 `+$13c0` → `+$c9e`, `+$13ce` → `+$cac`, `+$13e0` →
`+$cbe`, `+$13f6` → `+$cd4`, `+$36ee` → `+$2be8`; hunk 1 `+$10` → `+$10`, `+$251a` →
`+$cbe`, `+$49b2` → `+$3076`, `+$4a14` → `+$30d8`, `+$4be8` → `+$32ac`, `+$525a` →
`+$391e`, `+$7b58` → `+$6238`, `+$a1de` → `+$8848`, `+$a20e` → `+$8878`, `+$a21e` →
`+$8888`, `+$a220` → `+$888a`, `+$a226` → `+$8890`, `+$a3a6` → `+$8a10`, `+$b6ea` →
`+$9d54`, `+$d86e` → `+$bec4`, `+$d888` → `+$bede`, `+$ed60` → `+$d3b6`, `+$ed86` →
`+$d3dc`, `+$ed97` → `+$d3ed`, `+$ed99` → `+$d3ef`, `+$edcf` → `+$d425`, `+$edfe` →
`+$d454`, `+$ee05` → `+$d45b`, `+$ee08` → `+$d45e`, `+$ee6a` → `+$d4c0`, `+$ee6c` →
`+$d4c2`, `+$ef2a` → `+$d580`, `+$ef3c` → `+$d592`; hunk 2 `+$4ec` → `+$2aa`; hunk 3
`+$740` → hunk 4 `+$740`. The slave's routines also use offsets outside the checked bytes
(MAIN's object table `+$ed6c` → `+$d3c2`, `tools/rr_objects.py`; the 3D flag `+$ee03`,
the frame routine's other entries and variables): those are found with each step's patch.

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

### Objects and the scheduler

MAIN's loop (hunk 1 `+$24f8`-`+$25e0`) walks the object table (`+$ed6c`: per object a
longword frame pointer, `a6`, and at `+4` the word offset of the next entry; MAIN is entry 0)
and, at the list's end, calls the frame routine (`+$250e` [`$69ba`] `bsr +$49b2`). For each
object:

- **Every pass** (`+$2530`-`+$256a`): when its flags `-36(a6)` have bit 7 set and bit 1
  clear and its program has a pass handler (header `+10`, the header at `-20(a6)`, whose
  first word is the program's slot), that handler runs.
- **Timed** (`+$256e`-`+$25dc`): when its state `-4(a6)` is not 0 and the VBL count
  (`+$ee6c`, counted at `+$99ea`; the slave's world count W in 3D mode, "AGA improvements"
  6) is past its next run (`-62(a6)`), the next run becomes the
  count plus its period (`-58(a6)`, `+$257e` [`$6a2a`]-`+$2590`) and its program runs on from
  `-8(a6)` until it yields (op `$42`), then its post handler (header `+6`). Op `$36`
  (`+$6478`) sets the period and the next run to the count plus it (`+$6480` [`$a92c`]).
  A period-0 object runs once per pass, but at most once per field.

Lateness is not carried: an object runs at the first pass after it is due and is due again
a period after that. When MAIN keeps up, the frame routine's cap wait (until `+$ee6b`, the
fields since its last start, reaches the cap `+$ee6a`, 3 in game) puts the passes on a grid
of 3 fields, and an object runs every period + 1 fields rounded up to a multiple of 3:
measured standing still in START's code (`tools/rr_objects.py`), every 3 fields for the
period-0 objects, 9 for period 7, 6 for period 3, 12 for period 10, 18 for period 15. In
START's code a longer frame routine delays everything due during it (`docs/performance.md`,
"Objects' rhythm"); the slave's world count keeps the grid standing, turning and walking.

An object's frame holds its pose: positions at `+0`, `+8`, `+16` (16.16 longwords, the
integer word first), angles at `+24`, `+32`, `+40` (words, whole degrees, kept within
±360), velocities as bytes at `+52`, `+56`, `+60`, and the angle offsets the view adds at
`+64`, `+68`, `+72`. Ops `$4c`/`$4d` set or add the position, `$f0`/`$f1` the angles, `$90`
adds the velocities, `$fa` adds them turned by the angles, `$fb` turns towards a heading;
`$f9` gives the position plus the turned velocities, `$f7` and `$fd` query the map, `$f8`
moves with a collision check and `$b2` finds objects within a radius. Before a timed run
`+$4762` copies the pose's six words to `+$edac`-`+$edb8`; after it `+$4792` [`$8c3e`]
brings the angles within ±360 and, when the object has moved or turned, moves its 3D
elements (`+$ed86`'s table, chained from `-24(a6)`) by the difference, marking them changed.

The views are part of MAIN's frame (`+$eda8` points at both): the first at `+$edd6`, chained
at `+4`; flags at `+0` (bit 7 changed, bit 6 skipped) and `+1` (bit 1: 3D), the camera
position at `+22`-`+26` and angles at `+52`-`+56`, the followed object at `+96` (its offset
in `+$ed6c`) with follow flags at `+132` (bit 0 position, bit 1 angles) and offsets at
`+134`-`+144`. Per frame routine, for each view, `+$48b8` sets the camera from the followed
object's pose plus the offsets and marks the view changed when the camera moved; when
changed, `+$4980` adds the view's velocity (`+42`-`+46`) to the camera and `+$a3a6` draws
the 3D view (`+$a470`); unchanged, it copies the shown planes into the back buffer once.
Scripts read the views like any of MAIN's variables (the walk's camera heading is MAIN's
word `$18a`).

In the jungle start (the walk, `tools/rr_objects.py`) nine objects run:

| Entry | Slot | Program | Period | What it does there |
|---|---|---|---|---|
| 0 | 0 | MAIN | 0 | the game's phases |
| 6 | 2 | `souris` | 0 | the pointer |
| 12 | 15 | `heros` | 7 | the player; the 3D view follows it. Turning stores its heading (7 to 9 degrees a run); walking takes two sub-steps a run through ops `$f9`, `$f7`, `$b2`, `$fd` and `$f8` |
| 18 | 3 | `yoda` | 0 | about 53 ops a run (not examined) |
| 24 | 9 | `time` | 0 | adds 1 to MAIN's word `$1a08` at every run (180 of 180 traced) and switches on it; MAIN's byte `$1922` went from 2 to 4 in 182 fields (a game clock counted in passes, INFERRED) |
| 30 | 29 | `caporal` | 3 | |
| 36 | 75 | `sjungle` | 0 | three ops a run: the jungle's sounds (INFERRED from the name) |
| 54 | 85 | `skyjun` | 15 | the jungle's sky (INFERRED from the name) |
| 138 | 21 | `human` | 10 | moves (its position changed between snapshots) |

Walking on, other objects start (a trace of 329 fields walking saw three more run).

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
