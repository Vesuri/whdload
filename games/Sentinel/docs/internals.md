# Internals

## Loading

A direct slave (`ws_Version` 17, `WHDLF_NoError|WHDLF_ClearMem|WHDLF_EmulTrap`): 512 KB
base memory, no ExpMem, quit key F10, data from the RawDIC image `Disk.1`. It turns on the
instruction cache (`resload_SetCACR` 1, 1; the data cache stays as WHDLoad sets it), loads
the first `$B400` bytes of the image to `BASE` = `$57FE4` and identifies them by CRC16
(`$67E7`, SPS 3025; anything else `TDREASON_WRONGVER`). The image has 10 sectors a track
of which the game uses 9, so the slave packs the first nine tracks to 9 sectors each in
place. It sets CIA-A's LED bit, enables interrupts (`INTENA` `$C000`), patches the program
and jumps to `BASE+$10D4`.

Every later load goes through the game's track loader, which the slave replaces: the
parameter block at `BASE+$C98` holds the start track, the length in tracks and the
destination, and the slave reads `(track-2)*5120` bytes in from the image (tracks of 10
sectors).

## Slave patches

Offsets are into the program as loaded, from `BASE` (so the file offset into the packed
9-sector stream).

| Offset | Patch | By |
|---|---|---|
| `$A3E` | `rts`: drive motor off | Harry |
| `$A78` | `rts`: drive motor on | Harry |
| `$ADC` | `rts`: step to track 0 | Harry |
| `$B9C` | `rts`: read the protection track | Harry |
| `$669C` | jump to `Loader`, the image loader above | Harry |
| `$4B2` | `jsr CheckKeys`: stores the key at `$58C6B`, handshakes the keyboard with a 3-line delay, and quits on the quit key | Harry |
| `$51C` | `rts`: the game's CPU-timed keyboard delay | Harry |
| `$C0A` | skip to `$C6C`: the protection track check | StingRay |
| `$30C` | `jsr` a blitter wait before writing `BLTCON0` `$09F0` (not with CUSTOM1) | StingRay |
| `$6D4` | `jsr`: acknowledge the vertical blank interrupt twice, for 68040/060 and fast chipsets | StingRay |

CUSTOM1 (`C1:B:Disable Blitter Waits`) drops the `$30C` wait.

## Limitations

The 68060 draws wrongly ([open-work.md](open-work.md)).
