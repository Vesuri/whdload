# Gunship time model (static analysis + flight1 trace counts)

Notation: `+xxxxx` = gamemule hunk-0 offset (code at $985CD8). `D+xxxx` = data hunk 6 offset
($9951F8, also the a4 base). Variables in other gamemule hunks are given as the relocated absolute
address seen in this dump (`$97EE1C`, `$994DA8`, ...); `+0xxxx` is also used for variables that sit
inside the hunk-0 range (e.g. `$9923FC` = `+0C724`).

## Answer

**The simulation is fixed-step per rendered frame pair, not real-time.** One simulation tick
(flight model, controls, AI, weapons, damage, every-16-tick housekeeping) runs once per pass of
the main loop at `+0563A`, and each pass renders exactly `ceil(D+1548 / D+154A)` frames
(6/3 = 2 frames here), the extra frame interpolated between the previous and new camera state.
Elapsed real time (the VBL counter) is measured once per tick, but only to feed a debug
frame-rate meter whose result is thrown away. No dt, no catch-up loop, no frame cap beyond the
WaitTOF inside Intuition's RethinkDisplay. **On a faster CPU the game runs faster** in proportion
to the frame rate: tick rate = fps / 2.

## 1. Time sources (complete list found in hunk 0)

| Source | Where | Use |
|---|---|---|
| timer.device | OpenDevice("timer.device", unit 1 = UNIT_VBLANK) at `+032A4`, request ptr in `D+4C64`; only closed again at `+033D0..+033F0` | **Never sent.** No DoIO/SendIO/BeginIO goes to it from game code |
| VBL interrupt server | AddIntServer(5, `D+4C86`) at `+03362..+0336A`; Interrupt code = `+00F14`, pri -60 | Real-time counters, see below |
| VBL counter `$97EE1C` (long) | `+00F52 addq.l #1,$97EE1C` (only while IntuitionBase->ActiveScreen == game screen `$9999A8`) | Read only at `+0420A` (delay), `+0427A` (init), `+04470` (FPS meter), `+08182` (code-entry screen wait) |
| CIA | `+010AE move.b $BFE0FF,d0` | Fire buttons (CIA-A PRA mirror), not a timer |
| $DFF004/006, VBeamPos, DateStamp, VBlankFrequency | none | `jsr -384(a6)` at `+000D2` is exec WaitPort (startup), not graphics VBeamPos |

The 0.44 timer.device BeginIO calls per field in the profile are **not game code**. Their call
paths (attrib.pkl) go `... exec:-30 (Switch) > ROM $FE612E/$FE618C > timer.dev:-30` or appear
"inside" arbitrary game functions (`+06642 > ROM $FE612E > timer.dev:-30`), i.e. another task
(input.device, which ticks via timer.device) runs after a task switch and the stack rebuild
attributes it to the game task. The other exec IO calls in the binary (`+0EE78` DoIO stub, used at
`+0335E/+033A4`) go to the input.device request `D+4C5C` with command 9/10 = IND_ADDHANDLER /
IND_REMHANDLER (input handler `+00D60`, pri 51).

### What the VBL server does each field (`+00F14` -> `+04B48`), all real-time and cosmetic/UI
- `+04B52 bsr +04DC6`: latches fire-button edges into `$98AAFE/$98AB00`.
- Rotor/engine sound pitch with random jitter (`+04B60..+04BA4`, audio through `+00A88`).
- `subq.b #1,$99948E` and `$9994EE` (sound effect timers).
- `+04C12 jsr +0A1C8` (sequencer for message/radio state, `$990125`), `+04C18 jsr +045B0`
  (sprite animation step whose rate comes from player byte `D+3BA3`, likely the rotor-blur sprite).
- `+04C1E addq.b #1,$99010C` (consumed by `+0A37C`, which acts only when > 3, i.e. every 4 fields).
- `+04C24 addq.w #1,$98AAF2` (never read by game code).
- `+04C2A..`: `subq.b #1,$9994EF` (screen-flash duration, gates `+09B9A` in the frame function;
  set to 64/128 at `+09E22/+09E48` when hit).
- `+04C3E..+04C58`: `subq.b #1` on six bytes `$9923FC..$992401` (`+0C724..`), the blink timers of
  six warning lamps, reloaded with 8 in `+0BE5A` (called from the frame function).
- `+04C6A jsr +015A2` (sound), then `+01068` (joystick/mouse read into `$97EE00..`).
These run per field, not per frame, so they stay real-time on any CPU.

## 2. How time becomes simulation steps: it does not

Main loop (sim tick) `+0563A .. +05A0C`:
```
+0563A  lea     $998D80,a5          ; player/heli struct = D+3B88
+05640  addq.w  #1,12(a5)           ; tick counter D+3B94, +1 per tick, unconditional
  ... controls/flight model on a5 fields (4(a5),6(a5) decay at +0594C/+0597A, etc.) ...
+057E2  move.w  0(a5),$994DA8       ; build new camera/state vector ($994DA8..)
+05830  jsr     +04288              ; render ceil(D+1548/D+154A) frames, returns
+05884  jsr     +04E3C              ; keyboard/command handling (bmi = leave loop)
+0588E  jsr     +0937C / +0979C / +09C5C / +09F74   ; AI, weapons, etc. (per tick)
+058AC  move.w  12(a5),d0 ; andi.w #15,d0 ; bne ...  ; every 16 ticks: +07F80 ...
+05A0C  bra.w   +0563A
```
Render/interpolate `+04288`:
```
+0430C..+0431E  delta = new - prev   (27 words at $994DA8 minus $97FF52)
+0433C  move.w  D+154A,d1 ; add.w D+154C,d1 ; move.w d1,D+154C   ; acc += step (3)
+0434E  cmp.w   D+1548,d1 ; bge full                          ; denom (6)
+0435C  divu.w  D+1548,d1 ...        ; frac = acc/denom
+04380..+04392  out = prev + delta*frac  -> $998AFC ; jsr +05C04 (frame) ; loop
full:   prev = new, out = new, acc -= denom (and -= step if non-zero) ; jsr +05C04
+04470  move.l  $97EE1C,d0 ; move.l $97FF48,d1 ; move.l d0,$97FF48
+04482  sub.l   d1,d0 ; move.l d0,-(sp) ; jsr +02276 ; addq.w #4,sp   ; result ignored
```
`+02276` (FPS meter): `D+4B3C[i] = (D+1548/D+154A) * 60000 / elapsed_fields`, averaged every
3 ticks (`D+0596` counter) into d6, which is dropped; the caller discards d0 too. The 60000 assumes
60 Hz (value = frames per second * 1000 at NTSC rate). Snapshot: D+4B3C..44 = 6315 each =
2*60000/19, i.e. 19 fields per tick.

`D+1548` (denominator, 6 in this dump) is written only by the key handler at `+04EF2..+04F26`
(key code 12, probably raw key $0C "=": guess), which toggles it between its value and half of
it (6 <-> 3), i.e. interpolation on (2 frames/tick) or off (1 frame/tick). `D+154A` (step, 3) is
never written by code. So "detail/smoothness" toggling changes the game speed by 2x too.

Nothing scales velocities by elapsed time; no clamp/min/max on a dt exists because there is no dt.
Integer truncation of dt to 0 cannot happen.

Other per-frame (not per-tick) work: `+05C04` is called twice per tick; it builds the view and
cockpit, calls `+0BE5A` (lamp blink, VBL-timed) and `+0A37C` (VBL-timed via `$99010C`). I did not
find sim-state integration inside `+05C04` (it reads the interpolated `$998AFC` state), but its
callee tree (`+084E2`, `+07A1C`, `+05F8E`, `+05EA4`, `+0AA4C`, ...) was not audited exhaustively
(open item).

## 3. Frame-rate cap

None in game code. The only wait per frame is WaitTOF (graphics -270) inside Intuition
RethinkDisplay called from the buffer swap `+04496 > +00B7C > +00C38 > intuition:-390`
(profile: graphics:-270 0.11 calls/field = once per frame). That syncs to the next vertical blank,
so a frame takes at least about one field: max 50 fps PAL, hence max 25 ticks/s (50 with
interpolation off) versus about 2.7 ticks/s measured on the A500. The `+041FC` routine
(busy-wait `60*n` VBLs, "n seconds" assuming 60 Hz) has no direct caller found in hunk 0.

Prediction for a CPU that renders at 25-50 fps: flight, AI, weapons, tick-based timers and
anything counted in ticks (fuel/mission time if tick-based) run 5-10x faster than on the A500;
cockpit lamp blinking, hit flash, sounds, radio/message sequencing and sprite animation driven
from the VBL server stay at real-time speed. Even on the A500, speed varies with scene
complexity (16-20 fields per tick in the trace).

## Evidence: confirmed vs guessed

Confirmed (code + trace):
- No game use of timer.device, beam position, CIA timers, DateStamp or VBlankFrequency (whole
  hunk 0 disassembled and grepped; LVO calls listed).
- VBL counter `$97EE1C` and its readers as listed; the FPS meter result is discarded.
- Tick loop `+0563A`, 1 `+04288` per tick, 2 `+05C04` per tick: attrib.pkl calls = 27 `+04288`,
  27 `+02276`, 53 `+05C04` in 500 fields. A per-field trace scan (`pc == +0563A/+05C04/+04470/
  +00F52`) gives ticks at fields 12, 29, 45, 62, 79, 95, 114, 134, ..., 487 (16-20 fields apart),
  one interpolated frame in the tick's field and the final frame 8-10 fields later; `+00F52` runs
  in every field.
- Dump values: D+1548 = 6, D+154A = 3, D+154C = 3 (mid-tick), `$97EE1C` = 372, `$97FF48` = 368,
  D+3B94 = 20.

Guesses: what key 12 is; the exact meaning of `$9994EF`, `$99010C`/`+0A37C`, `+045B0`; whether
fuel and mission clock are tick-based (they are in sim code reached only from the tick loop, but
the variables were not identified); that `+05C04`'s subtree has no state integration.

## Experiment (gdb stub, read-only)

Sample these once per field (or every ~10 fields) for ~1000 fields on the 68000 config and on a
fast (68020/030 + fast RAM) config, with identical inputs (e.g. on the pad, then hovering):
- `$97EE1C` (long): field counter (reference clock; increments only while the game screen is active).
- `D+3B94` = `$998D8C` (word): sim tick counter.
- `D+1548` / `D+154A` (words): frames per tick (expect 6/3).
- `D+4B3C`, `D+4B40`, `D+4B44` (longs): FPS*1000 (60 Hz units) for the last 3 ticks;
  `$97FF48` = field count at the last tick.
- Player state `D+3B88`/`D+3B8A` (words, map X/Y), `D+3BA4` (word, 28(a5), altitude), heading
  bytes `D+3BBD..D+3BBF` (53..55(a5)), to compare distance moved per field.
Model to verify: `d(tick)/d(fields) = fps / 2` on both machines; distance and heading change per
tick are the same on both machines, per field they scale with fps. If game time were real-time,
`d(tick)/d(field)` would be constant across CPUs; I predict it rises from about 0.055 (A500) to
0.25-0.5 on the fast config. A second check: press the key that halves D+1548 and confirm the tick
rate doubles while fps stays the same.
