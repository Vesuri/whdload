# Plan

The ordered work from today's state to the goal: better performance on every supported
machine, with rendering up to 50 fps while world simulation and game logic keep their native
rates. Any agent can pick up the first step whose dependencies are done. Background is in
[internals](internals.md) and [open work](open-work.md); the rules are in `AGENTS.md`.

## Conventions

- **Step IDs** are `<phase letter><number>` (A1, B3, ...). Commits and docs refer to them.
  A step is done when its **Done when** holds and its result is in the docs. Mark it
  `[x]` here in the same commit.
- **Addresses** follow `AGENTS.md`: code as `Disk.1` offsets, variables as chip (BaseMem)
  addresses. A chip code address `A` is `Disk.1` `A + $3CB0`.
- **Options**: every behaviour change sits behind a `Custom1` bit (or `Custom2` once
  `Custom1`'s bits run out) in `whdload/Mercenary3.slave.asm`, declared in `_config`. With
  every option off the slave runs the shipped code paths. Instruments go in the `VERIFY`
  build only (`IFD VERIFY`).
- **Builds**: each step that touches the slave runs `make original` (byte-identical), `make
  slave` and `make verify`.
- **Measurement**: compare a change only against the same build with the option off, on
  the same route and machine, with fps from frame counts (`route_profile.py`, or `fps.py`
  from A2). No performance claim without a measurement. A change under 2% on every CPU
  class is dropped unless it is free. Run the full machine matrix only at checkpoints (the
  ✓ steps). Never rerun the emulator without a source change in between.
- **Regression gate**: with every option off, `a500-1.5m` must give the shipped slave's
  frame count on the route (38 frames, 3.82 fps today), and the picture must match.
- **Decisions** marked **(U)** belong to the user. Ask, record the answer under
  [Decisions](open-work.md#decisions), then continue.

## Targets

| Class | Setup | Memory | What can help |
| --- | --- | --- | --- |
| 68000 | `a500-1.5m` | 512 KB chip, 1.5 MB slow | B1, B4, E |
| 68020, chip only | `a1200` | 2 MB chip | B1, B2, B4, E |
| 68020 + fast | `a1200-fast` | 2 MB chip, 8 MB fast | all |
| 68030 | `a1200-030` (with and without `MMU`) | + fast | all, plus B5 |
| 68040 / 68060 | `CPU=68040-NOMMU` 25 MHz, `68060-NOMMU` 50 MHz | + fast | all, plus B5 |

The 50 fps goal is only reachable where drawing fits in about a field (68030/50 and up, after
C and E). Phase D makes every machine run the world at native speed whatever its frame
rate. It also makes the extra frames smooth on machines that draw faster than 12.5 fps.

## Phase A: instruments and baselines

**A1. Reliable route entry on the 68030, without changing its MMU backend.**
- Diagnose the missed entry breakpoint and establish bounded boot-to-gameplay observation.
- Share checked entry anchoring, deadlines and owned-process cleanup between route tools.
  If the entry breakpoint cannot be recovered, validate a counter anchor and its route
  alignment against the entry anchor on `a1200-fast` before using it.
- Use `fps.py` and `sim_speed.py` for counter/state evidence on the 030. Give
  `route_profile.py` an explicit untraced mode; instruction costs remain unavailable
  on the MMU backend and must never be reported as zero.
- **Done when** the full untraced route completes on `a1200-030` in both
  `route_profile.py MODE=counter` and `sim_speed.py`, with matching frame counts, and
  `a1200-fast` retains A2's 90-frame entry-anchored reference for `Custom1=1`.
- The original requirement that the instruction profiler run on the 030 was invalid:
  its MMU backend does not record instructions. The user requested completion without
  changing that backend. Boot diagnosis recovered the original entry breakpoint by
  disabling deterministic directory I/O; no counter fallback or route shift is needed.
  **Done:** both 030 tools count 89 frames over 500 fields; the 020 counter and
  instruction profiler retain 90. Publication breakpoints also work on the 030.
  See [A1 validation](internals.md#a1-anchor-investigation) for evidence and limits.

**A2. Frame counting without traces.** The 040/060 cores record no instruction trace.
- Add `tools/fps.py`. It boots, anchors as in A1 and drives the route untraced, then
  reports:
  - the frames (chip `$7180` at the end minus at the start) and fps;
  - fields per frame from the field stamps at chip `$52954`, read at a breakpoint at
    `Disk.1` `$5E4DE`, or from `PER_FRAME` samples where breakpoints work.
- Give each boot a deadline.
- **Done when** on `a1200-fast` the counter delta agrees with a contemporaneous
  `route_profile.py` run of the same build and options. **Done:** both count 90 frames
  for `Custom1=1` in 500 fields. The original 89-frame expectation is not reproduced
  by the current profiler either; [A2 validation](internals.md#a2-frame-counting-without-traces)
  records the evidence and runtime identity. This corrects the expected reference count,
  not the counter output. A2 uses the existing entry breakpoint; A1 extends that validated boot path to the
  030 without instruction recording.

**A3. Machine matrix script.** Add `tools/matrix.sh SLAVE "WHD_ARGS..." OUTDIR`.
- It runs `fps.py` once for each setup in the table above, one at a time.
- Use the cycle-exact 030 options with the frequency set for the 030/040/060 cells.
- It writes a table: setup, options, frames, fps.
- Sanity check: an 8 MHz 040 run must be slower than a 25 MHz one.
- **Done when** the table renders for the shipped slave.

**A4. Cache state per cell.** Add a `VERIFY` instrument that logs `CACR` right after
`resload_SetCACR` with `resload_Log`. Run it only on the 68020 and later; `resload_Log`
needs WHDLoad 18.
- **Done when** each matrix cell's actual cache state is recorded in `internals.md`.

**A5. ✓ Baseline matrix.** Run A3 for each of these:
- the shipped slave;
- the performance slave with every option off;
- `Custom1=1`, `3`, `5` and `7`.

Record the tables in `internals.md`.

**A6. Committed-state recorder.** Add `tools/state_trace.py`, a breakpoint at the main
loop head (`Disk.1` `$5E992`). On every pass it records:
- the pose block, chip `$7142..$7161`;
- the clock, chip `$57B0..$57B3`;
- the frame counter `$7180` and the field stamps `$52952`/`$52954`;
- the collision flag `$6F56`;
- the object tables (chip `$AF36..`, `$B31E..`; extend once D4 maps them);
- a hash of chip `$5350..$68000`, which is the game image without the display buffers.

`--compare A B` reports the first differing pass and the differing fields.
- **Done when** two boots of the same build give identical records.

**A7. Lockstep mode** (`VERIFY` only, `Custom2` bit 0). It makes each frame's world
advance independent of the frame's duration:
- the publication's elapsed-field store (`Disk.1` `$5E4F0`) always writes 4;
- `state_trace.py` drives the joystick by pass number, not by field.

The same build at any speed then reaches the same world state at every pass. Display
buffers can be compared frame by frame: add a `--buffers` dump of chip `$68000..$6FD00` /
`$78000..$7FD00` at publication.
- **Done when** lockstep `a1200-fast` and lockstep `a500-1.5m` give identical state traces
  and identical display buffers over the route. This is the check that every later
  rendering change must pass.

**A8. A scene-stable route.** Add a route that walks out of the cell and then stands still
facing outside. Add a per-call report of cycles per call for the drawing routines (`Disk.1`
`$577BE`, `$5410E`, `$5AFAA`, `$593A6`, `$5E840`). With it, renderer changes are judged by
cycles per call, independent of where the faster build ends up.
- **Done when** `route_profile.py ROUTE=...` gives per-call figures within 1% across two
  boots.

## Phase B: low-risk slave options

**B1. Settle option bit 0** (one-time DMA enable and full palette copy).
- Test every screen class for display faults: title, prison, outdoors, buildings, the
  map, vehicles, a flight, game over and restart, save and load.
- **Done when** the screen walk is recorded in `internals.md` with no fault.

**B2. Settle option bit 1** (FMODE 3 on AGA).
- Search every executed copper list for display-window writes (`$008E`/`$0090`/`$0092`/
  `$0094`/`$0100`/`$0108`/`$010A`) in all screens of the B1 walk, not just in the two
  in-game lists (`Disk.1` `$56780`, `$567CC`). Every other list that sets a fetch window
  needs its own `DDFSTOP` patch, or FMODE must go back to 0 while it is shown.
- Check the picture on `a1200` (stock) and `a1200-fast`.
- **Done when** the walk shows no fault and the A3 matrix gives the gains per cell.

**B3. Settle option bit 2** (the stack in expansion memory).
- Confirm that the three stack setups (`Disk.1` `$5DE66`, `$5DE88`, `$5DEEA`) cover every
  entry: new game, load game, game over.
- Confirm that the stack never exceeds the 4 KB. Add a `VERIFY` guard that fills the block
  with a pattern at boot and reports the low-water mark on exit.
- Change `ws_ExpMem` to optional (a negative value) and fall back to the chip stack when
  WHDLoad gives no memory.
- **Done when** the guard shows enough headroom and the fallback boots.

**B4. Blitter back-buffer clear** (new bit).
- Replace the CPU clear (`Disk.1` `$5E840`, about 52,000 cycles per pass on `a1200-fast`)
  with a D-only blit of the 3D view's rows.
- Start the blit at the clear's call. Wait for the blitter before the first CPU access
  to the back buffer: put a blitter wait at the entry of every drawing routine that can
  run first.
- Measure `BLTPRI` on and off.
- Measure on 68000, `a1200` and `a1200-fast`. Gate it to the CPUs where it gains.
- **Done when** A7's buffer comparison is identical and the gain is measured per class.

**B5. Data cache on 68030+ (U).**
- The slave requests the instruction cache only. Measure `resload_SetCACR` with the data
  cache added on 030/040/060, behind an option.
- First audit coherency:
  - the game's self-modifying code (C2);
  - copper list and palette writes, which are read by DMA;
  - on the 040/060, copyback against the display buffers.
- The playbook leaves cache policy to the user: present the measurement and ask.
- **Done when** measured and decided.

**B6. ✓ Checkpoint.** A3 matrix with B1–B5 on and off, regression gate, picture walk.

## Phase C: hot code in fast RAM (68020+ with real fast RAM)

The largest remaining chip cost on `a1200-fast` is code fetch: half of the CPU's chip
accesses. 95% of the missed fetches come from 18.5 KB of code.

**C1. Fetch census per routine.** Extend `bus_audit.py` to attribute instruction-fetch
misses to routines.
- Take routine starts from every static `jsr abs.l`/`bsr` target in the image plus the
  traced call targets.
- Report each routine's range, size, misses per field and cumulative share.
- Known hot pages: `Disk.1` `$4EDB0..$4EFAF` and `$5B5B0..$5B9AF`.
- **Done when** a list of routines covering 95% of misses is in `internals.md`.

**C2. Reference audit of the candidate routines.** Add `tools/reloc_audit.py`, which
statically decodes the whole image (Capstone) and lists:
- every branch, `jsr`, `jmp`, `lea`/`pea` and absolute operand that points into a
  candidate range;
- every PC-relative operand inside a candidate that points outside it;
- every jump table and data word inside a candidate;
- every executed write into a candidate. The write audit found code words written by the
  drawing: chip `$459BA` (`Disk.1` `$4966A`), `$4F700..` (`$533B0..`) and `$4F9C2..`
  (`$53672..`).

The slave's 68040 path already rewrites four of these sites to load the target from
vectors at chip `$C0..$CC` (`movea.l ($C0).w,a0` / `jsr (a0)`). Find out:
- whether that variant covers every self-modifying site in the candidates;
- whether it runs correctly on every CPU.
- **Done when** each candidate is classed as "movable as is", "movable with N fixups" or
  "not movable", with reasons.

**C3. Relocation at boot** (new bit; requires the 68020 or later from `WHDLTAG_ATTNFLAGS_GET`
and expansion memory in real fast RAM: not below `$200000`, not `$C00000..$DFFFFF`).
- Raise `ws_ExpMem` (optional) to fit the stack, the code and alignment.
- At boot, after `resload_Patch`:
  - copy each movable routine from the loaded image into expansion memory;
  - apply its fixups from a table of offsets in the slave (offsets only, never game bytes);
  - write `jmp abs.l` to the fast copy at each original entry;
  - enable the `$C0..$CC` variant for self-modifying sites (C2), or redirect their writers
    to the copies;
  - `resload_FlushCache`.
- Generate the fixup table with `tools/reloc_audit.py --emit whdload/reloc.i` and include
  it. The generated file contains offsets and lengths only.
- **Done when** the game boots and plays the route with the option.

**C4. Verify C3.**
- A7 lockstep: identical state traces and display buffers with the option on and off, on
  `a1200-fast` and the 030.
- A `VERIFY` guard checksums the original chip copies of moved routines at every pass.
  Nothing may write them once moved, except the redirected self-modifying sites.
- **Done when** both hold over the route and the B1 screen walk.

**C5. Measure C3** on the 020+fast, 030, 040 and 060 cells. Extend the moved set while
each extension gains at least 2%.

**C6. Hot CPU-only data.** Use the census (data reads in the image: 19% of the CPU's chip
accesses, a third of them the publication spin) to find hot read-only tables used by moved
code. Copy them to fast RAM and retarget only the moved copies' references.
- Same verification as C4.
- **Done when** measured, and kept only if it gains.

**C7. ✓ Checkpoint.** A3 matrix, regression gate.

## Phase D: separate logic passes and presentation frames (up to 50 fps)

The design and decisions are in [open work](open-work.md#design-native-logic-passes-separate-presentation-frames):
- logic passes run natively, once at least 4 fields have passed;
- presentation frames run in between;
- the player's presented pose is extrapolated, other objects are interpolated.

**D1. Logic gating** (new bit), at the main loop head (`Disk.1` `$5E992`, a 6-byte `jsr`).
It applies only when walking mode is active (chip `$7122` = 1). Fewer than 4 fields since
the last logic pass: skip the pass (for D1 alone, wait for the next field). Otherwise:
- run the native pass;
- give it the true elapsed count in chip `$52954`, so its tick count (clamp 4..8) and
  velocity scaling stay native.

This alone stops the world from running fast above 12.5 fps.
- **Done when**:
  - a `sim_speed.py` run on the fastest cell walks and turns at the native per-field rates
    (6 units and 2 heading units per field);
  - on `a1200-fast`, A6's per-pass state with D1 on matches the A7 lockstep run of the
    option-off build (every pass 4 fields), given the same input per pass.

**D2. Presentation frame, camera only.** When fewer than 4 fields have passed, run the
presentation sequence:
1. snapshot the bytes in the restore set below;
2. run the camera derivation (`Disk.1` `$5D844`);
3. run the view setup (`$5E0BA`, `$5DA50`, `$5A91E`, `$469C4`/`$469C8`);
4. publish (`$5E458`), clear (`$5E840`) and draw (`$5410E`, `$593A6`, `$5AFAA`, `$577BE`);
5. restore the snapshot.

The restore set is the write audit's union for these calls:
- the render scratch at chip `$0340..$4000`;
- variables such as `$719E`, `$71AE..$71E9`, `$7220..` and `$727C`;
- the object-table areas;
- the self-modified code words.

Exclude the display state, which must follow the screen: chip `$72B2`/`$72B6`, `$42C00`/
`$42C01` and the copper list contents. Keep the frame counter `$7180` at the logic-pass
count (blinking). Never run the collision test (`$5AAB0`) in a presentation frame.
- Add a `VERIFY` instrument that hashes chip `$5350..$68000` before step 1 and after step
  5; any difference outside the display state is a failure, logged with its address.
- **Done when**:
  - the hash check passes over the route;
  - A6 shows committed state identical with D2 on and with D1 alone;
  - the frame rate exceeds 12.5 fps on a cell that can draw that fast.

**D3. Player extrapolation.** Stage a presented pose in chip `$7142..$7161` before step 2.
- Position and heading are the committed values plus the per-tick rate times the fields
  since the last pass. The rates are walking 6 units, running at its measured rate, and
  turning 2 heading units per tick, taken from the input held at the last pass and the
  pose delta of that pass.
- Snap to the committed pose on a collision (`$6F56` set), a mode change (`$7142`), a pose
  jump larger than one pass's maximum, or a stop.
- **Done when** a per-frame `sim_speed.py` trace shows presented poses monotonic between
  passes while walking and turning, and equal to the committed pose at each pass.

**D4. Map the other objects' poses.**
- From the drawing's reads, find the per-object position and orientation fields: watch
  the object tables (chip `$AF36..`, `$B31E..`) and the lists the drawing routines walk.
- Find which tick routine (`Disk.1` `$5A644`, `$5C8F8`, `$5F724`, `$5F328`) moves them.
- Document the layout, the object count field, and how objects appear and vanish.
- **Done when** `internals.md` has the layout and a tool prints every visible object's pose
  per pass.

**D5. Interpolate other objects.**
- Keep the previous pass's poses in a slave buffer.
- In a presentation frame, stage poses interpolated between the last two passes, with
  alpha = fields since the last pass / that pass's length. Restore afterwards with the
  rest of the restore set.
- Snap new and vanished objects and large jumps.
- Extend the D2 hash check to the object tables.
- **Done when** moving objects (vehicles, doors, lifts on the route) move smoothly in
  per-frame screenshots and the committed state still matches D1 alone.

**D6. Other movement modes.**
- Extend the write audit and the route to the other loop paths (`Disk.1` `$5E214`,
  `$5E3CA`): vehicles, flight, lifts, transport.
- For each mode, decide one of:
  - gate it like walking (it moves per tick);
  - leave it native (it moves one step per frame and so follows the frame rate);
  - give it a per-mode presentation path.

  Those modes run fast on fast machines today; gating them changes game speed back to
  native, which needs the user's agreement **(U)**.
- **Done when** every mode is classified, each enabled mode passes D2's checks, and the
  rest run natively with the option on.

**D7. Pacing and latency.**
- Publish at most one frame per field (the existing VERTB wait already caps it).
- Check that the input read at each logic pass is unchanged.
- Measure input-to-screen delay in fields for the player (extrapolated: no added delay)
  and for objects (one pass).
- **Done when** recorded in `internals.md`.

**D8. ✓ Checkpoint.**
- A3 matrix with the frame rate and the fields per logic pass on each cell. The logic
  pass must be 4..8 fields everywhere, and equal to the shipped slave's on the A500.
- Regression gate.
- A play session on the fastest cell, with screenshots per field over a turn.

## Phase E: faster drawing on every CPU

**E1. Classify the drawing routines.**
- Name what each of `Disk.1` `$577BE`, `$5410E`, `$5AFAA`, `$593A6` draws (sky and ground,
  polygons, objects, palette), using A8's cycles per call and per-routine self cycles.
- Find the inner loops: span fill, edge stepping, the pixel plotter at the read-modify-write
  hot rows.
- **Done when** `internals.md` lists each routine's role and its inner loops' share per
  CPU class.

**E2. Inner-loop replacements, one at a time.**
- For each loop worth 3% or more, write a replacement in the slave:
  - 68000: long or `movem` stores for span fills;
  - 68020+: a cache-sized loop, 32-bit stores and bitfield instructions where they help.
- Gate each per CPU class and keep the original where it doesn't measure better.
- `VERIFY` pixel twin: draw with the replacement into a guarded shadow buffer, draw with
  the original into the real one, compare every plane and the surviving registers.
- **Done when** each kept replacement passes the twin over the route and A7, with a
  measured gain on each class it is enabled for.

**E3. Draw in fast RAM, copy to chip** (68020+ with real fast RAM).
- Point the drawing at a fast-RAM staging bitmap of the 3D view. After drawing, wait for
  the publication handshake, then copy it with `movem` into the chip back buffer.
- Measure with and without C. The playbook's Powerdrome case gained only with the code
  moved too.
- **Done when** measured on the 020+fast, 030, 040 and 060 cells, and kept only where it
  gains.

**E4. Triple buffering (U).**
- The publication's wait for the next field costs 7–10% on `a1200-fast`. A third buffer
  needs 32 KB of chip RAM beyond the 512 KB BaseMem; raising `ws_BaseMemSize` would drop
  machines with 512 KB of chip RAM.
- Present the measured wait per cell and the trade-off.
- If approved:
  - add the buffer;
  - rotate the three copper lists and buffer pointers in the publication (`Disk.1`
    `$5E458`);
  - wait only when the next buffer is still shown.
- **Done when** decided, and, if built, measured and A7-identical.

**E5. ✓ Checkpoint.** A3 matrix, regression gate.

## Phase F: release

**F1. Option layout (U).** Propose one player-facing toggle that enables every verified
option valid for the machine, plus a developer build with the individual bits. Ask for the
default (on or off).

**F2. Requirements and ReadMe.**
- Memory requirements (expansion memory size and fast RAM for C/E3).
- What each option does, and the original game being one switch away.
- The slave's `_info` version string.

**F3. ✓ Final checks.**
- Full A3 matrix.
- Functional boots with the MMU on (`CPU=68040`, `68060`) and with WHDLoad's `NoCache`.
- The B1 screen walk with the release options.
- Regression gate.
- Results in `internals.md`.

**F4. Hand-off.** Update `README.md`, `open-work.md` (remaining ideas only) and this plan
(every step marked).

## Order and dependencies

| Step | Needs |
| --- | --- |
| A1–A4, A6, A8 | nothing |
| A5 | A1–A4 |
| A7 | A6 |
| B1–B5 | A3 (for measurement) |
| C1 | nothing; C2 needs C1; C3 needs C2 and B3; C4 needs C3 and A7 |
| D1 | A6 |
| D2 | D1, A7 |
| D3 | D2; D4 needs nothing; D5 needs D2 and D4; D6 needs D2 |
| E1 | A8; E2 needs E1 and A7; E3 needs E1 (better after C) |
| F | all kept work |

Recommended path: A1 → A2 → A3 → A6 → A7, then D1 (which fixes the fast-machine world speed
on its own), then C1–C5 and D2–D5 in parallel, then B, E and F.

## Status

- [x] A1 [x] A2 [ ] A3 [ ] A4 [ ] A5 [ ] A6 [ ] A7 [ ] A8
- [ ] B1 [ ] B2 [ ] B3 [ ] B4 [ ] B5 [ ] B6
- [ ] C1 [ ] C2 [ ] C3 [ ] C4 [ ] C5 [ ] C6 [ ] C7
- [ ] D1 [ ] D2 [ ] D3 [ ] D4 [ ] D5 [ ] D6 [ ] D7 [ ] D8
- [ ] E1 [ ] E2 [ ] E3 [ ] E4 [ ] E5
- [ ] F1 [ ] F2 [ ] F3 [ ] F4

Done so far, before this plan: the byte-exact slave reconstruction, the route profile, the
game-time model, the write and bus audits, and `Custom1` bits 0–2 (measured on
`a1200-fast` and `a500-1.5m`).
