# Internals

The program, its display and game time, every slave patch (as offsets into the game's code
hunk or file), current measurements and known limitations.

## Loading and memory

A direct slave in 512 KB of chip memory (`ws_BaseMemSize` $80000, no ExpMem). The slave
loads the boot block's loader from disk offset 0 to $60000, patches it and jumps to $6000C;
the loader loads the main program (about $3658-$1E000) and calls the slave's `Patch`, which
patches the program and jumps to its entry at $3658. Files are decrunched by the program's
streaming loader at $1D798; `Decrunch` wraps it. Addresses here are BaseMem addresses: the
program is loaded at fixed addresses, so they are its file layout too. The data disk's
program differs from Vroom's only in its init code ($3600-$4400) and a few data words.

## The original slave's patches

| Where | What |
|---|---|
| loader $60030, $6007A, $6020E | trap #0 for the loader, `move.l a1,a2` removed, `Patch` called |
| loader at $6EE88 | the track loader replaced by `Load` (`resload_DiskLoad`), MFM decoding skipped |
| $39C2 (data disk $395E), $81A8, $81BE, $6534, $13126, $1D9F6 (data disk) | disk protection |
| $3E00-$3F00, $11000-$19C00, $11DD6 | blitter waits after `move.w Dn,$58(a6)` (`WaitBlit0`-`6`, `WaitBlit7`) |
| $19EBE, $19F8C, $1A23E, $19F02, $19FC2, $1A264 | self-modified `move.l (a4,d0.w),(a5)`/`(a6)` moved to the slave |
| $1D0F8 | `Decrunch`: re-removes the protection after a reload to $439C |
| $1D16C-$1D24A | drive head moves and delays removed |
| $1D280, $1D3D8 | highscore save (`resload_SaveFileOffset`) and track loads |
| $A1D4 | keyboard: quit key, F9 |
