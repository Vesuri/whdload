# English, German and French AMIGA2

Read this before adding or changing any game address in `src/`.

One slave runs all three AMIGA2 files that CFou!'s v1.0 install supports and that are
available here. All three get the enhancements:

| Version | Archive | `LOV_LANG` | Hunk sizes differing from English |
|---|---|---|---|
| English | `LegendsOfValour_v1.0_0837.lha` | 0 | none |
| German | `LegendsOfValour_v1.0_De_0525.lha` | 1 | h2 `$640c`, h11 alloc `$a4e0`, h12 `$17a4c` |
| French | `LegendsOfValour_v1.0_Fr_1768.lha` | 2 | h1 `$2c34`, h2 `$640c`, h12 `$17a4c` |

All three archives are pinned in `inputs.sha256`, and `make unpack` installs them as
`tmp/game/LegendsOfValour`, `LegendsOfValourDe` and `LegendsOfValourFr`. CFou!'s v1.0 also
supports a second English version, which is not available here. It and any other
AMIGA2 run as v1.0, with CUSTOM2 cleared.

## How the versions differ

The code is the same; only the layout and the text differ (`python3 tools/versions.py
summary`):

- **German**: the code hunks keep the English layout, except h2 and h12 (as French). h11
  (A4 = h11 + `$8000`) has longer text: offsets from `$6f0` move by 2, and from `$7f8` by 4,
  apart from the text tables. So most A4 displacements in the code differ by 4
  (`-8134(a4)` becomes `-8130(a4)`).
- **French**: h11 keeps the English layout. h1 code moves by 8 from `h1:00846`. h2 moves
  by 4 to 16 from `h2:0404c`. h12 moves by 80 to 122 from `h12:07f42`; after `h12:09afe` the
  shift is 122. German h12 is the same.
- Both versions: every absolute relocation and PC-relative displacement into a moved
  region differs too.
- CFou!'s manual protection compare is at `h1:013d8` in English and German, and at
  `h1:013e0` in French. `_patchgame` already looks in both places.

## Address symbols

Every game offset in `src/` is written as a symbol `hN_OFFSET`: OFFSET (five hex digits) in
hunk N of the English AMIGA2, as in the docs' `hN:OFFSET`. Examples: `(h12_054ce,a0)`,
`lea (h1_02a4a,a0),a2`, `dc.l h5_02358`. A4 displacements are h11 offsets minus `$8000`:
`(h11_0603a-$8000,a4)`. In a signature, a displacement field is written as its
expression. For example, `cmp.l #$39400000+((h11_0603a-$8000)&$ffff),(h1_01ba8,a2)` is
`move.w d0,-8134(a4)`, and `$4eba0000+((h1_02a4a-h1_02766)&$ffff)` is a JSR to h1:02a4a.
An offset relative to a moved hunk address (`(4,a2)` after `adda.l #h12_14224,a2`) is
allowed only inside a region that moves as a whole. Keep the encoding the same in every
language. A symbol of 0 still has to be written `(a2)`, so that vasm keeps the same
instruction size.

`src/offsets.s` is generated: `python3 tools/versions.py symbols` collects every
`hN_OFFSET` used in `src/` and writes its English, German and French value:

```
h1_01ba8	= LOV_EN*$01ba8+LOV_DE*$01ba8+LOV_FR*$01bb0
```

`tools/versions.py` aligns each code hunk instruction by instruction, with capstone and
with the numbers ignored. A code offset maps to the matching instruction, or to the same
place inside it. An h11 offset maps through the operands of aligned instructions: A4
displacements, absolute relocations into h11, and h11's own pointers. A stray use with
another base register is outvoted (`operand 5/6`). Offsets that cannot be decided stop
the generator; decide them by hand in `OVERRIDES`. Run `python3 tools/versions.py map
h11:0603a a4:-8640 h12:09452` to see single offsets and how each was mapped.

## Build and boot

`game.sh` `game_build` assembles the slave three times with `-DLOV_LANG=0/1/2
-DLOV_PASS1=1`. Each of these builds ends with an empty table. `tools/fixups.py` requires
the three builds to be the same size, and turns every 16-bit word that differs into an
entry: the slave offset and the German and French word. The final build is the English one,
with the table (`tmp/build/<build>/lov_fixups.s`) included after the `$VER` string.
`fixups.py --same` checks that the table moved nothing. A plain `vasm -DLOV_PASS1=1`
assembles an English-only slave.

At boot, `_lov_version` compares the 17 hunk sizes (alloc + 8, before each next-hunk link)
with the three tables in `_lov_hunk_sizes`. It stores the language in `_lov_lang`.
For German or French, `_lov_fixup` writes that column of the table over the English words
and flushes the caches. This happens before any installer reads an offset, and only
outside character creation (CUSTOM1). An unknown version clears CUSTOM2.

## Checks

- `python3 tools/versions.py check` (also run by `make check` when the foreign games are
  installed) confirms that `src/offsets.s` is current. It also confirms that every
  signature compare `cmp/tst #value,(hN_OFFSET,An)` evaluates, in each language, to that
  language's AMIGA2 bytes at the mapped offset.
- The English build must not change when you only rewrite addresses: compare the
  `tmp/build/<build>/lang0/` slave before and after.
- Runtime: boot the foreign drawers with
  `GAME_DIR=LegendsOfValourDe SLAVE_FILE=LegendsOfValourDe.Slave` (or `...Fr`) in front of
  any `tools/fixed_window.sh` command. The install checks abort on any wrong signature, and
  the VERIFY twins compare each enhanced routine with the original in the running game.
  Host-side analysers (`turning_check.py`, `lov_timing_fields.py`, `lov_report.py`) read
  English h11 offsets, so they are English-only.

## Results (08.11.2026)

Both foreign versions boot the VERIFY slave on the spin route to the tape anchor with all
nine enhancements (CUSTOM2=511). `_lov_lang` is 1 and 2, CUSTOM2 stays `$1ff`, and every
hook sits at the mapped offset.

`tools/render_validate.sh PREFIX 63`, with `GAME_DIR`/`SLAVE_FILE` set, passes on both CPUs.
It covers every twin over all three views (C2P pixels, wall and sprite columns, ray
reciprocals, chunky clear):

| Version, CPU | C2P pixel twins | Wall columns | Clear |
|---|---|---|---|
| German, 68020 | 873 | 43152 ×3 | 972/324/450 |
| German, 68000 | 407 | 23574/23573/23573 | 662/68/84 |
| French, 68020 | 894 | 44470/44469/44469 | 1012/326/450 |
| French, 68000 | 402 | 23680 ×3 | 684/36/84 |

The one-degree check passes in all views on both versions: the turning wall twin against
the original table, plus the 360-heading ray sweep (CUSTOM2=191, CUSTOM5=2621443,
VERIFY_WAIT_RESCUE build, `c2p-views.txt`). Routes need `VERIFY_WAIT_RESCUE`, as in
English: without it a French run stalled in a tape wait.
