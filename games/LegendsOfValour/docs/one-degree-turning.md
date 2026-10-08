# One-degree turning (CUSTOM2 bit 7)

Optional slave patch, labelled "1 degree turning", read once at launch. The player can face
and render every whole-degree heading. A tap turns one degree; held turning keeps the game's
original speed. With the bit off, every hooked byte stays original and turning stays at five
degrees. The bit is independent of the 25 Hz simulation (bit 6); both combinations work.

## How the game turns

- The raw heading is at `h11:08c28`; the displayed heading at `h11:08c22` is rounded with the
  five-degree unit at `h11:06010` (`h5:01e8e`–`01e96`). The existing sine/cosine routines already
  take integer degrees.
- Wall setup at `h12:0229e` stores the row stride 4 × (view width + 8) at `h12:0003a` and the
  angle unit at `h12:00038`. At `h12:028d8`–`02904` the renderer folds the heading into a half
  turn, divides by the unit and selects a row of the ray table at `h11:05faa`; consumers follow
  from `h12:0290c`.
- Each view loads a 36-row table: large 192 × 92 `mt0.dat`, medium 112 × 64 `mt2.dat`, small
  80 × 48 `mt3.dat`. With 180 rows the large table is 144,000 bytes.
- Row format: each ray is the rotated vector `(focal, (width-1)/2 - column)`. A row starts
  with an octant, then per column `floor(65536*minor/major)` and `round(65536/major)`. A zero
  word moves to the preceding octant. Padding after the last column is unrelated data and is
  not ray geometry.
- Save/load copies the fourteen bytes `h11:08c1c`–`08c29` byte by byte (`h2:04cce` saves,
  `h2:04bde` restores, helpers `h2:04a5e`/`04a8a`). Headings are not quantized, so the save
  format does not change.

## Design

- **Runtime tables.** No game data in source. `_turn_generate` copies the 36 original rows,
  padding included, to every fifth angle. It builds the other 144 rows with Q22 sine constants
  (`turning_trig.s`, `round(sin(deg) * 2^22)`) and 68000 integer arithmetic: no FPU, no library.
  The legacy rows therefore stay byte-exact. The new rows match the floating-point model's
  projection words exactly, with slope error at most 1/65536.
- **Near-axis slope minimum of 2.** Zero is the octant marker, and one overflows the original
  `65536 / slope` DIVU. The error this introduces is below 0.002°.
- **Ownership.** The game keeps its own table and its load/free paths, and they never see ours.
  Only the renderer's row selector uses the slave buffer: one 144,000-byte MEMF_PUBLIC buffer
  per run, reused when the view changes and released by the game-cleanup helper.
- **Atomic publish.** The table is generated at view setup, outside the render loop. Pointer,
  stride and both angle units (`h11:06010`, `h12:00038`) are published together only after the
  build succeeds.
- **Fallback.** If allocation fails, both units stay at five and the active table pointer stays
  null. A one-degree index is never used with a five-degree table.
- **Memory reserve.** KickEmu's expansion pool cannot fit the table, so `FASTMEMSIZE` in
  `LegendsOfValourHD.s` is 512 KiB + 144 KiB. The reserve applies even with the bit off.
  Physical host fast RAM does not enlarge KickEmu's fixed pool.
- **Input.** The first press turns one degree. Repeats are suppressed for `TURN_REPEAT_FIELDS`
  = 8 PAL fields (160 ms), measured in consumed simulation fields when bit 6 is on. After that,
  the view's original held increment applies. A 40-field press gives steps `[1,0,0,0]` followed
  by five-degree steps, so taps do not slow sustained turning to a fifth. Mouse headings
  normalise to 0–359 in both directions. The displayed heading equals the raw heading.

## Source files

| File | Role |
|---|---|
| `whdload/turning.s` | Bit-7 install, allocation/free, publishing table and units; hooks guarded by signatures |
| `whdload/turning_generate.s` | `_turn_generate`: D0 width, D1 focal length, A0 180-row destination, A1 36-row legacy table |
| `whdload/turning_trig.s` | Q22 sine constants 0..90°, computed from mathematics |
| `whdload/turning_input.s` | Tap/repeat policy (`TURN_REPEAT_FIELDS`) |
| `whdload/turning_verify.s` | VERIFY table oracle: checks copied rows, and new rows against a host-model checksum |
| `whdload/turning_pixels.s` | VERIFY wall twin (CUSTOM5 bit 19): runs `h12:02808` with the new and the original table at legacy headings and compares all chunky bytes |
| `whdload/turning_sweep.s` | VERIFY ray sweep (CUSTOM5 bit 21): all 360 headings through the real ray walker in every view |

`rays.s` (W5) and `walls.s` (W3) consume the published table through the original selector.
They need no turning-specific code.

## Invariants a change must keep

- Bit off: all six turning hook ranges stay original. `check_disabled.py` checks them.
- Legacy rows (every fifth angle) are byte-identical to the original tables, padding included.
- Table pointer, stride and both units change together, or none of them change.
- No slope word below 2; the zero word stays the octant marker.
- The game never frees the slave buffer, and the slave frees it exactly once.
- Hooks preserve all registers and condition codes.
- The wall twin shares the C2P staging buffer, so it needs W6's nested twin (CUSTOM5 bit 7) off.

## Verification

Run captures one at a time, with `JOY0=none`, in `amiga/.cap`. Use both the A500 equivalent and
the 020 machine (`KICKSTART=$KICKSTART_A1200` from `amiga/env.sh`; settings in
`docs/profiling.md`). Build VERIFY with `make -C whdload verify VASMFLAGS=-DVERIFY_WAIT_RESCUE=1`,
copy the slave and listing into each OUT, and pass `KEEP_SLAVE=1`.

- **Host model.** `python3 tools/turning_tables.py` reproduces every consumed column of all 108
  original rows (13,824 columns) from the local game files. The floating-point model needs the
  double just above π to reproduce the original asymmetric 90° truncation.
- **Tables, wall twins and full ray sweep together.** This passes on both CPUs in all views:

  ```sh
  KEEP_SLAVE=1 WHD_ARGS=CUSTOM2=191 TAPE_OPTIONS=2621443 SELFTEST_FRAMES=40 TURNING_CHECK=1 \
    TURNING_CHECK_ARGS="--require-all-views --require-wall-twins --require-ray-sweeps" \
    tools/fixed_window.sh OUT tools/tapes/c2p-views.txt
  ```

- **Lifecycle** (CUSTOM5 bit 22: allocate, free through the real shutdown helper, reallocate):
  run the spin route with `STATE_ONLY=1 TAPE_OPTIONS=4194305 TURNING_CHECK_ARGS=--require-lifecycle`.
- **Forced allocation failure** (CUSTOM5 bit 18): `TAPE_OPTIONS=262145 TURNING_CHECK_ARGS=--fallback`.
  Both units must stay at five and the table pointer null.
- **Input.** `python3 tools/turning_input_check.py --sweep forward|reverse` reads completed-tick
  observations from a timing-enabled capture. It requires exactly 360 unit steps, every
  heading, one wrap, and agreement with the historical mouse-counter deltas.

## Cost

Matched-pose stationary A/B on `tools/tapes/turning-still.txt` (heading 270), CUSTOM2 63 → 191:

| Machine | fps off → on | Renderer main cycles/call | C2P main cycles/call |
|---|---|---|---|
| A500 equivalent | 3.4 → 3.6 | 1,165,803 → 1,162,327 | 503,544 → 500,835 |
| 14 MHz 68020 + 4 MB fast | 16.8 → 17.0 | 560,145 → 560,753 | 143,587 → 143,748 |

Actor state differs between the off and on runs, so this shows no measurable per-frame cost,
not a speedup. Table generation is a setup cost per view change. Large view: 542 PAL fields
on the A500 and 87 on the 020. Medium: 304 and 50.

Reproduce:

```sh
FSUAE="$HOME/.local/share/amiga/fs-uae-arm/fs-uae" PROFILE_WINDOW=guest \
  tools/ab_window.sh one-degree 63 191 turning-still 'a500 a1200'
python3 tools/ab_summary.py one-degree
```
