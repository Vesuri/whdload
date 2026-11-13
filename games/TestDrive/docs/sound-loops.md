# Race sound loops

Current 2.0b (13.11.2026) removes the click heard on every pass of the race's looping
sounds, with either `CUSTOM2` setting.

## Cause

Each `Sfx` file starts with a 6-byte header: the sample length (long) and its rate
(word). The race start at h4 $A370 starts three loops through root $24C4
(`-32514(a4)`): Squeal on channel 1 (period 358, the tyre squeal, volume from the
envelope at h4 $A526), TheTurbo on channel 2 and TheEngine on channel 3 (periods from
RPM at h4 $A44E). It passes the loaded file's address with the header's length, and
$24C4 writes them to AUDxLC/AUDxLEN through the channel table at -31672(a4)
(30 bytes per channel; started at root $26F8). Paula therefore looped the header plus
all but the last 6 sample bytes. The one-shot wrapper at root $246A passes the file
address + 6.

The header bytes as samples (for Squeal `00 00 03 88 27 10`) put a spike into every
pass. Worst step around each loop seam, against the sample's own steps:

| Loop | Before | After | Sample median / 99th percentile step |
|---|---|---|---|
| Squeal | 159 | 27 | 21 / 76 |
| TheTurbo | 139 | 80 | 24 / 80 |
| TheEngine | 101 | 37 | 11 / 42 |

## Fix

`TestDriveHD.s` hooks the three `move.l sample,-(sp); jsr -32514(a4)` pairs at h4 $A390,
$A3B0 and $A3DA in `instrument_patches` (installed after every h4 load in both modes).
Each hook passes the file address + 6, or 0 when no sample is loaded, as before. The
length is still the header's, so each loop now covers exactly the sample. Pitch, volume
and timing are unchanged, and no sample bytes are modified.

After the fix, no seam is sharper than steps that already occur inside its sample.
Neither engine sample repeats cleanly at any shorter loop length: the best match over
the last 3000 bytes differs from the start by about one median step RMS. Shortening
the loop or smoothing the sample end is therefore not done.

## Verification

In an attract race on a1200-030, the channel table for channels 1-3 was read from a
memory snapshot (scratch `tmp/loop/loopcap.py`). Before the fix it held each file's
address (loop = file bytes 0..len-1); after it, file address + 6 (loop = exactly bytes
6..end of each file, matched byte for byte against the data files). The hook,
simulation, render and audio audits pass. Not yet listened to on real hardware.
