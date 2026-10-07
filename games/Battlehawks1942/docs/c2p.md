# The chunky-to-planar pass, and whether a Kalms c2p would help

Question (2026-10-07): would replacing the game's c2p (`bh:1a2c2`) with one of Mikael Kalms'
merge c2p routines (`~/.local/share/amiga/kalms-c2p`) raise the frame rate?

**Answer: no.** Measured: a full-frame merge c2p in Kalms' style makes the game 40 % slower
on the A500 (9.7 → 5.7 fps in level flight, 6.2 → 4.3 fps in a roll). The game's own pass
is a *delta* c2p, and in this game only 1–13 % of the view changes from frame to frame
(flat-shaded sky and sea), so comparing and converting only the changed longs beats any
routine that converts every pixel.

## What the game does

- View: 256 × 96 pixels (`-6054(a4)` = 32 longs per row, `-6052(a4)` = 96 rows), 4 bitplanes,
  at byte offset `-6048(a4)` = 644 in each plane (row 16, x 32), plane stride 40 bytes. Plane
  pointers at `26224(a4)`..`26236(a4)`.
- Chunky: 4 bits per pixel, 8 pixels per long, leftmost pixel in the top nibble. Two chunky
  buffers alternate (`bh:6ec6`); the pass gets (new, previous).
- Per long: `cmpm.l (a5)+,(a6)+; dbne d7` against the previous frame; a changed long is
  converted with 32 `add.w d4,d4; addx.b dN,dN` steps into 4 bytes, one per plane, written
  with `move.b dN,(0,aN,d4.w)` straight into the displayed planes (single buffer).

## Measurements (`tools/c2p_stats.py`, A500, chip-only slave, 100-field windows)

| window | longs changed per frame | c2p share of all cycles | compare | convert | other |
|---|---:|---:|---:|---:|---:|
| level flight (first 100 fields of the flight) | 1.0 % (19–37 of 3072) | 15.6 % | 12.8 % | 1.5 % | 1.2 % |
| roll (controller pushed right every 4 fields) | 7.2 % (5.0–12.6 %) | 16.2 % | 8.1 % | 7.1 % | 1.0 % |

Costs: 31.2 cycles per long compared, 381.7 cycles per changed long converted; one pass is
about 117,000 cycles in level flight (0.8 PAL fields at 7.09 MHz).

## The experiment (`make c2pfull`, `whdload/c2p_full.s`, VERIFY only)

A full-frame merge c2p written for this chunky format: Kalms' routines take a byte per pixel
and start by merging bytes into nibbles; here the nibbles exist already but in sequential
order, which needs six exchanges per 32 pixels (search over exchange plans: two 16-bit ones
done with word moves, then 4, 1, 8 and 2 bits). The group body was checked against the game's
conversion on 2000 random inputs (Python interpretation of the assembly text) before running
(but see below: the reference itself was wrong at first).

| window | original | full-frame merge c2p |
|---|---:|---:|
| level flight | 9.7 fps (18 frames / 93 fields) | 5.7 fps (10 / 87) |
| roll | 6.2 fps (11 / 88) | 4.3 fps (7 / 82) |
| cycles per c2p pass | ~117,000 (level) | 634,000 |

Break-even, from the measured costs: a full conversion at ~195 cycles per long only wins when
more than about 43 % of the longs change; the game peaks at 13 %.

The timed version had the pixel order wrong (the original's first `swap` brings the high word
into the low half, so the leftmost pixel is the top nibble; I had read it as words swapped,
and the interpreter check used the same wrong reference). The flat sky and sea hid it; the
user spotted the scrambled gun sight. Fixed: the same instructions with two exchange steps'
register roles and the store order changed, re-checked against the corrected reference, so
the cycle counts above stand.

## What is left in the c2p

- Compare loop (8–13 % of all cycles on the A500): unrolled `cmpm.l; bne.s` saves 2 of ~30
  cycles per long, about 1 % of all cycles. Not worth a patch on its own.
- Conversion (1.5–7 %): a table lookup (four 256-entry long tables) would save roughly a
  fifth of it: under 1.5 % of all cycles.
- With the slave's fast memory (now the default) the chunky buffers are in fast RAM: the
  compare reads fast RAM only and only changed bytes go to chip RAM, which is the right shape
  for faster CPUs. The frame rate is limited by the renderer and the simulation, not the c2p.
