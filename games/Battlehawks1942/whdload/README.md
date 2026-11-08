# WHDLoad 20.0 source baseline

The slave builds with `kick13.s` (and `kickfs.s`), `whdload.i` and `whdmacros.i` from the
official WHDLoad 20.0 developer archive, taken from the shared WHDLoad 20.0 tree that AmigaXDev
installs (`$WHDLOAD`, default `~/.local/share/amiga/WHDLoad-20.0`: `Src/sources/whdload/` and
`Include/`). The small `include/lvo/` aliases adapt the official sources' include names to the
host NDK. The slave follows `Src/slave-examples/kick13.asm`.
