# Stellar 7 internals

## Supplied version

The installed pack contains English Stellar 7, labelled NTSC, with Psygore's
1.0 slave (2 January 2008). Both archives contain an identical 3980-byte slave.
The installer contains no source. The `s7` executable is 186796 bytes.

Slave SHA-256: `b241c2656184ba17a6e5bfad3c335379b1e677c1df23731ceec296fc2aeef91d`.
Game SHA-256: `2360196317fc1d2a507c987834e9308f7368110194523c34b9376d606b606eb0`.

## Loader

The shipped slave requires WHDLoad 16, 512 KB base and 768 KB expansion RAM
(the latter includes the 256 KB Kickstart image). Its flags are NoError,
EmulPriv, ClearMem and Examine. It uses Kickstart 34.005, CRC $f9e3, and
current directory `data`. Keypad asterisk ($5d) quits. No CUSTOM options exist.

This is an OS game. The slave boots KickEmu 1.3, reads/decrunches `s7`, accepts
CRC16 $b9ea or $fcc4, frees the temporary file buffer, and LoadSegs `s7`.
It passes a newline argument and calls the loaded program. It applies no
patches to the game's hunks. Its patch list at slave:$60 instead adapts the
Kickstart image and filesystem. The game-specific loader is slave:$eb4–$f64.
It explicitly calls SetCPU with value $393d and mask $7f3f; actual cache state
must be checked before comparing fast-CPU measurements.

## Executable

| Hunk | Kind | File offset | File-backed bytes | Allocated bytes |
|---|---|---|---|---|
| 0 | Code | $24 | $25360 | $25360 |
| 1 | Data/BSS | $29f2c | $3558 | $823c |

Hunk 0 has 4833 relocation entries; hunk 1 has 323. Startup sets A4 to
hunk 1 + $8000. The code contains Aztec C `link a5` prologues and handwritten
assembly. Loaded-hunk identification must reject WHDLoad's PRELOAD file copy
and validate A4 against the next LoadSeg segment.

## Boot and measurement status

The original reaches the Dynamix logo and story introduction on the default
A500-equivalent machine. Gameplay, an attract demo, frame counting and the
game-time model are not yet verified. No performance claim is established.
