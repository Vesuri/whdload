# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`.

## Inputs

`inputs.sha256` pins five archives; `make unpack` installs every drawer:

| Archive | Holds | Game |
|---|---|---|
| `Links_v1.01_2481.lha` (Retroplay) | `tmp/game/Links/` | v1.53 (SPS 2481), PAL |
| `Links_v1.01_NTSC_2010.lha` (Retroplay) | `tmp/game/LinksNTSC/` | v1.50 (SPS 2010), NTSC |
| `Links&DataDisks_v1.01_2481.lha` | `tmp/game/Links&DataDisks/`: v1.53 with the Bountiful and Firestone course disks | v1.53 |
| `Links&DataDisks_v1.01_NTSC_2010.lha` | `tmp/game/Links&DataDisksNTSC/` | v1.50 |
| `Links.lha` (whdload.de) | `tmp/game/Links_Install/`: installer, `Links.inf`, ReadMe, `Source/Links_WHD.s` | - |

Every archive ships the same slave (V1.01, SHA-256 `f3710938...`). The two versions differ
only in `data/golf`; `data/title` is the same file.

## The build

`src/Links_WHD.s` is the package's `Source/Links_WHD.s` (the import commit has it unchanged)
with the edits vasm needs, each commented in place: the `INCDIR` and the `Sources:` include
path go, `DEBUG` is commented out (the shipped slave has no debug strings and the release
`ws_CurrentDir`, `data`), `cmp.w #-1`/`#-2` are written `cmpi.w` (StingRay's assembler's
encoding), and the fake command line `"",10,0` is written `0,10,0`, because his assembler
emitted a zero byte for the empty string (the shipped slave passes three bytes).

This held for the setup (StingRay's V1.01 unchanged); 2.0b's changes are on top. The
build was not byte-identical: it includes the WHDLoad 20.1 `kick13.s`, larger than the
2013 one, so everything after it moves (a code hunk of `$13F0` bytes against `$12BC`; the
header offsets `CurrentDir`, `name`, `copy`, `info`, `kickname` and `config` by `$134`). The
equivalence is proved as the playbook asks: every other header field is equal (version 17,
flags `WHDLF_NoError|WHDLF_EmulPriv|WHDLF_Examine`, BaseMem `$80000`, ExpMem `$140000`, kick CRC
`$F9E3`); the slave's own part after the strings, 596 bytes, differs in three bytes only,
two PC-relative displacements into `kick13.s` (`_dosname`) and one `CNOP` padding word
that StingRay's assembler filled with garbage (`$6010`) and vasm with zero; the strings and
patch lists are byte-identical; and it booted both versions to the first hole.

## Driving it

`python3 tools/links.py serve` (or `make serve`) boots under the server, with the run
options from the environment; `tools/links.py` adds:

| Command | Does |
|---|---|
| `move DX DY` | moves the mouse by DX, DY counts, 20 a field |
| `click [N]` | holds the left button N fields (default 3), then releases it for N |
| `play` | from the title menu (CUSTOM1=1 skips the intro) to the first hole: START, the course list's OK, DEFAULT in the player file, OK, the ready screen's OK |

`tools/boot.sh SHOT [TITLE_WAIT] [GAME_WAIT]` boots, waits TITLE_WAIT seconds (default 12)
for the title menu, runs `play`, waits GAME_WAIT seconds (default 20), saves the screenshot
and stops its emulator. It needs `INSTANCE`:

```sh
INSTANCE=t SETUP=a1200-030 EXTRA_ARGS='--fast_memory=0 --zorro_iii_memory=32768' \
  WHD_ARGS='CACHE CUSTOM1=1' tools/boot.sh tmp/shots/030z3.png
```

The wait times are host seconds and the route's waits are fields, so a slow machine needs
both longer: the 68000 takes `TITLE_WAIT` 25 and `PLAY_SCALE=5`.
The route's mouse moves assume the pointer where the title menu leaves it; the player file
needs a click of 6 fields (3 is too short). The data cache halves the a1200-030's emulated
speed (AmigaXDev's `measurement-method.md`), so count fields there, not seconds.
`boot.sh` stops the emulator before the shot: on the a1200-040 WHDLoad's MMU fills the stub's
output with `68040 MMU:` lines, which break the capture otherwise. Parallel boots need
`NOBUILD=1` (they race in the build).

`python3 tools/drawcheck.py [N]` checks `_span1`, `_span2` and `_copyscr` against v1.53's
code on random inputs (internals.md, the course view); run it after changing them.

## Traps

- The plain a1200 (2 MB chip, no fast) and the a500-1.5m cannot allocate the ExpMem
  ("Can't allocate ExpMem.").
- The Barto profile records no instructions on the a1200-030's MMU core
  (`EXTRA_ARGS=--uae_mmu_model=0`) and none outside the 24-bit space (Zorro III).
