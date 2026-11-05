Legends Of Valour - WHDLoad slave 1.1b
Beta release (the b suffix signifies beta).
Reworked by Vesuri, based on the work of CFou!

Changes in 1.1b
-------------
Rendering optimizations are enabled automatically, with routines selected for
68000/68010 or 68020 and later processors. The chunky buffer uses PUBLIC memory,
allowing the system to use fast RAM when available. Allocation failure retains
the original allocation path. Chunky-to-planar conversion uses routines by
Mikael Kalms, adapted for this game.

The WHDLoad options are:

  Character creation             CUSTOM1=1
  Frame-independent game timing  CUSTOM2 bit 6 (value 64)

Use CUSTOM2=64 to enable timing; it is optional and off by default. Rendering
optimizations and one-degree mouse precision need no custom tooltypes.

Frame-independent timing advances simulation at 25 ticks per second and
corrects animation pacing. On slower machines this can reduce rendering speed.
The existing display cap and beam synchronization are retained.

Direct mouse control always uses one-degree heading and rendering precision
when the finer ray table can be allocated. UI turn buttons retain their native
increments and repeat behavior. This works with or without the timing option.

Requirements and compatibility
------------------------------
WHDLoad 17 or later, an A500 Kickstart 1.3 image and its matching RTB file.
The slave reserves 512 KiB chip memory and 656 KiB other memory; allow additional
memory for WHDLoad, game allocations and optional features. Fast RAM is useful.
This version was validated against the English game supplied in the 0837
archive. The original release's other language/version support is recorded
below but has not been revalidated for the new patches.

F10 quits (or use the WHDLoad QuitKey tooltype).

Original installation notes and credits follow. The memory requirement has
been updated for this slave. The bundled legacy source, where present, is
unchanged and describes the original 1.0 slave.

