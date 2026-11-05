# Kalms four-plane converters for Legends of Valour

Vendored from Mikael Kalms' public-domain collection:
https://github.com/Kalmalyzer/kalms-c2p
commit `d8ecf79a3325615305dd800ae7704b518e0d9dda`.

Files used:

- `bitmap/c2p1x1_4_c5_bm_word.s` (2022-03-19), selected for 68000/68010.
- `bitmap/c2p1x1_4_c5_bm.s` (2016-09-01), selected for 68020 and later.

Upstream `readme.txt` places everything outside `others/` in the public domain.
The build uses only these local copies, not the shared checkout.

Every local change:

- Trim upstream trailing blank lines at EOF.
- Remove the `section code,code` directive: include in the slave's single code hunk.
- High-nibble pixels: the word routine's `$0f0f0f0f` masks become `$f0f0f0f0`.
  Every first-merge pair shifts the second input right four bits instead of shifting
  the first left. This covers both prologues and both loop copies.
- The longword routine has **no upstream nibble masks**. Explicit `$f0f0f0f0`
  masks are added to all eight loaded longwords in both paths and their loop copies;
  each first merge similarly shifts the second input right four bits. These masks
  add instructions; the plan's equal-cycle estimate does not apply to this file.
- Add a stack-local source modulo `192 - chunkywidth` (word value in a long slot).
  Local-frame size grows from eight to twelve bytes; stack allocation and cleanup
  use `lea` instead of `subq`/`addq`.
- In the destination-modulo path, stop at the actual source row end, flush its
  pending plane writes, then add the source modulo, advance the end pointer by
  192, add destination modulo and restart the row prologue. This removes upstream's
  speculative load of the next row's first block before finishing the current row.
  The non-modulo path is unused by this game's 40-byte bitmap and <=192-pixel views.

The slave adapter uses the current view pointers, depth four, 40 bytes per row,
zero offsets, and a width enclosing the view in multiples of 32. Left edges are
aligned to 16 pixels (word aligned). Smaller views use a private 192-byte-stride
staging area with black padding each call, preserving the renderer's source origin
and never accessing bytes before it. The large view reads the game buffer directly.
The beam wait and one-shot view-change paths stay in the game.

VERIFY + CUSTOM2 bit 0 + CUSTOM5 bit 1 enables a pixel twin: the relocated original
routine writes scratch planes seeded from the screen, the replacement writes the
screen, and all 40 bytes of each enclosing row are compared. The test reports the
first differing plane-byte index and aborts. CUSTOM5 bit 0 independently enables
input-tape playback. Performance captures use CUSTOM5=1, correctness runs use 3.

The twin also XORs each view pixel's low nibble with `$0f` before both conversions,
then restores it after comparison. This tests ignored low bits even when texture
preprocessing has duplicated the colour into both nibbles. High colour bits and
all source bytes after a successful test are preserved.

The adapter saves/restores extra destination bytes on smaller views. At the first
medium conversion, those bytes still hold the earlier large view's pixels (the
pixel twin caught this); black padding alone is insufficient during transitions.
The active view and all surrounding screen bytes therefore remain pixel-exact.
