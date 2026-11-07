#!/usr/bin/env python3
"""Rebuild the emulated audio of a field-shot capture (fixed_window.py --shot-windows).

FS-UAE cannot record its sound, so this plays back what Paula fetched: each audio DMA
word (two signed 8-bit samples) is held for the channel's current period, scaled by its
current volume, both taken from the CPU's AUDxPER/AUDxVOL writes in the same trace.
Channels 0/3 go left and 1/2 right, as on the Amiga. Output: a 22050 Hz stereo WAV,
plus a report of each channel's sample starts (AUDxLC writes) and the fields with sound.

A trace slot is a DMA record index, so fetches are placed by their fraction of the NTSC
field; hold times use the colour clock. This reproduces the data stream to within one
scan line; Paula's output filter and exact fetch-to-output latency are not modelled.
"""
import argparse
import json
from pathlib import Path
import wave

import numpy

CLOCK = 3579545  # NTSC colour clock, Hz
FIELD = 262.5*227.5/CLOCK  # NTSC field, s
RATE = 22050


def rebuild(folder, start=0, end=None):
    fields = json.loads((Path(folder)/'shots.json').read_text())['fields']
    fields = fields[start:end]
    assert fields and 'audio_fetches' in fields[0], 'capture has no audio records'
    total = len(fields)*FIELD
    out = numpy.zeros((2, int((total+.1)*RATE)+1))
    period, volume, starts = [428]*4, [0]*4, {c: [] for c in range(4)}
    events = []
    # A slot is a DMA record index; place it by its fraction of the field.
    for i, f in enumerate(fields):
        at = lambda slot: (i+slot/f['slots'])*FIELD
        for slot, register, value in f['audio_writes']:
            events.append((at(slot), 0, register, value, f['field']))
        for slot, channel, value, _ in f['audio_fetches']:
            events.append((at(slot), 1, channel, value, f['field']))
    events.sort()
    location = [0]*4
    active = {c: set() for c in range(4)}
    for time, kind, a, value, field in events:
        if kind == 0:
            channel, register = (a-0xa0)//16, (a-0xa0) % 16
            if a == 0x96 or not 0 <= channel < 4:
                continue
            if register == 6:
                period[channel] = max(value, 1)
            elif register == 8:
                volume[channel] = min(value & 0x7f, 64)
            elif register == 0:
                location[channel] = value << 16
            elif register == 2:
                location[channel] = (location[channel] & 0xffff0000) | value
                starts[channel].append(dict(field=field, address=f'{location[channel]:#x}'))
            continue
        channel = a
        if not 0 <= channel < 4:
            continue
        active[channel].add(field)
        side = 0 if channel in (0, 3) else 1
        for half, byte in enumerate((value >> 8, value & 0xff)):
            sample = (byte-256 if byte > 127 else byte)*volume[channel]/(128*64)
            t0 = time+half*period[channel]/CLOCK
            i0, i1 = int(t0*RATE), int((t0+period[channel]/CLOCK)*RATE)
            out[side, i0:max(i1, i0+1)] += sample
    return out, starts, {c: sorted(v) for c, v in active.items()}, total


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('capture', type=Path)
    p.add_argument('--wav', type=Path, help='default: CAPTURE/audio.wav')
    p.add_argument('--start', type=int, default=0, help='first field')
    p.add_argument('--end', type=int, help='field after the last')
    a = p.parse_args()
    out, starts, active, total = rebuild(a.capture, a.start, a.end)
    pcm = (numpy.clip(out/2, -1, 1)*32767).astype('<i2').T.copy()
    target = a.wav or a.capture/'audio.wav'
    with wave.open(str(target), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    spans = {c: (f'{v[0]}-{v[-1]} ({len(v)} fields)' if v else 'silent') for c, v in active.items()}
    print(json.dumps(dict(wav=str(target), seconds=round(total, 3), channel_fields=spans,
                          sample_starts=starts), indent=1))


if __name__ == '__main__':
    main()
