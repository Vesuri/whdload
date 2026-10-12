# Known internals

## Phase 1 gate: CD32 static identification complete

Evidence is static only: verified archive extraction, hunk/relocation parsing,
slave patch-list decoding and inspection of 68020 disassembly. No emulator,
reconstructed slave, game patch, timing measurement or gameplay validation exists.
The time-source and display descriptions below are **hypotheses to confirm at run
time**, supported by the stated instruction sites; presence is not execution.
Phase 2 requires a separate request. The OCS executable has not been analysed.

Notation: `E:` and `G:` mean English and German **game code hunk 0 offsets**;
`S:` means **slave code hunk 0 offset**; `D:` means **English data hunk 1 offset**.
Other hunks and file offsets are explicitly labelled. Hardware registers are
named, not presented as relocated program addresses. Signed library-vector
numbers are API displacements. ROM patch offsets below are ROM **file offsets**.

## Input identity and executable layout

The CD32 full install and installer are pinned in `manifest/inputs.tsv`.
A fresh extraction matched every file of the reference CD32 game directory;
the installer and full-install slaves are byte-identical. File fingerprints:

| File | Bytes | SHA-256 |
|---|---:|---|
| `data/wing.english` | 280288 | `093505483aed4c9dbd1b97484c3336e92fdb156be9c15a67ed0199bd4dade657` |
| `data/wing.german` | 280796 | `2047da69f2c83803675921afd86204747609a5c59dd3e7f67d954d785677dabe` |
| `WingCommanderCD32.Slave` | 7728 | `5fbbb774bba3c794a776acc25f33c3f47c579449e1ba1a21c31418716aa74986` |

Both executables are ordinary, unpacked `HUNK_HEADER` LoadSeg files. There is no
executable depacker stub: the first jump enters the C startup. Records are CODE,
DATA, BSS, ABSRELOC32 and END; no SYMBOL, DEBUG, EXT or overlay records. All hunk
allocation flags are unspecified (neither CHIP nor FAST). The larger allocation
of hunk 1 includes zero-initialised storage beyond its file-backed data.

| Hunk | Type | English file payload offset | English stored / allocated bytes (hex) | German file payload offset | German stored / allocated bytes (hex) |
|---|---|---|---|---|---|
| 0 | CODE | `002c` | `35ea4 / 35ea4` | `002c` | `36064 / 36064` |
| 1 | DATA | `3a048` | `8464 / fda0` | `3a208` | `8490 / fdd4` |
| 2 | BSS | none | `0 / 4` | none | `0 / 4` |
| 3 | CODE | `42dec` | `1590 / 1590` | `42fd4` | `15a4 / 15a4` |

The slave has one CODE hunk: file payload `0020`, length/allocation `1e0c`,
no relocations or symbols. Slave hunk offsets therefore map to file offset +`20`.
Game hunk 0 offsets map to file offset +`2c`; do not use this rule for other hunks.

**Compiler/runtime: Manx Aztec C**, with hand-written assembly subsystems.
`E:00000` jumps to `E:34a32`; `E:34aa4` establishes the data-hunk small-data base
at hunk 1 +`7ffe`, C functions use `link a5` and stack arguments, and startup
writes the `MANX` stack marker at `E:34b24`. Startup clears the data tail, saves
the launch stack and Exec base, opens DOS, handles CLI/Workbench launch and
initialises the C runtime. Compiler release and original build flags are not
encoded in identifiable metadata and remain unknown. German startup is
`G:34bf4`, with the corresponding marker at `G:34ce6`.

Library use is linked through saved bases and negative-vector calls, not an
import-symbol table: DOS (file/CLI services), graphics (Views, ViewPorts, copper,
palette, sprites, blitter ownership), intuition (auxiliary screen and pointer
handling), lowlevel (joypad), nonvolatile (saves), icon (Workbench runtime), and
freeanim (hunk 3 opens it at English hunk 3:`153c`). Input and console device
names are present; the two OpenDevice sites `E:341a6` and `E:344c6` resolve to
`input.device`. `ciaa.resource`/`ciab.resource` strings at `D:4b97/4ba5` are not
proof of CIA timer use; no corresponding OpenResource call was found.

English/German are distinct linked executables, not a language byte switch.
Game selection uses `Custom1=1` for German, otherwise English (`S:1426–1438`).
`S:143a–147a` loads/decrunches the file to check its CRC, then frees it and calls
DOS LoadSeg at `S:14c8`. The pinned files need no decrunching. WHDLoad CRC-16
(reflected polynomial `a001`, initial zero) is `88e7` for English and `ced7` for
German, matching the slave selectors. Unrecognised CRC aborts. Hunk 3 differs
in size too; never apply a global language offset to arbitrary code. The late
platform routines cited below were compared separately: their German sites
are English +`1c2`, but earlier patch sites use the explicit table.

**Hunk 3 is the program's top level**, kept apart from the main code hunk. Its
strings are the `Origin&tonic` version banner, the `Wing256/`/`WING256:` data
paths and `harddisk.dat`, the "no campaigns installed" abort, and animation-demo
diagnostics ("Memory free before/after animation", "Animation demo over.").
Thirteen 32-letter rows at English hunk 3:`0b80–0cc8` look like campaign series
tables, one per star system (the slave's `Custom3` also offers 13 systems); their
meaning is unverified. Relocations: hunk 3 to hunk 0 205, hunk 0 to hunk 3 5,
data hunk 1 to hunk 3 10.

Resources in `wing256/` were not unpacked. The music loader recognises both
ordinary tracker data and a `COMP` representation (`E:277a8`, `E:27af4`);
that is resource compression, not executable packing. The resource formats,
script content and any resource-supplied code are outside this static census.

## Original slave and KickEmu

Psygore v1.0, dated 11 January 2014; requires WHDLoad 17. Header:

| Slave field offset | Meaning |
|---|---|
| `S:000e` | Flags `3432`: NoError, Req68020, ReqAGA, EmulPriv, ClearMem, Examine |
| `S:0010` | Base/chip memory `a0000` (640 KiB) |
| `S:0018` | Entry `S:0034` |
| `S:001a` | Current directory string `data` at `S:127b` |
| `S:001e–001f` | Debug key 0; exit raw key `5d` (`*`/PrtSc) |
| `S:0020` | Expansion `160000` (1408 KiB): Kickstart `80000` plus game fast-memory region `e0000` (896 KiB) |
| `S:002a–0030` | Kick-name table `S:11c8`, image size `80000`, CRC initially `ffff` |
| `S:0032` | Configuration string `S:1280` |

This is the **KickEmu 3.1 (`kick31`) family**, booting an emulated OS and a
WHDLoad-backed filesystem, not a direct bare-metal loader. Its table accepts
40.068 A1200 (`9ff5`), 40.068 A4000 (`75d3`), and 40.063 A600 (`970c`), despite
the ReadMe mentioning only A1200/A4000. A600 acceptance does not remove the
slave's AGA/68020 requirement. Exact KickEmu source revision is not embedded;
it cannot be equated to the currently installed WHDLoad 20 source.

The decoded ROM lists and helper bodies correspond to HDINIT and BOOTDOS,
INITAGA, a 5000-longword (20000-byte) stack, FONTHEIGHT=8,
BLACKSCREEN and POINTERTICKS=1. `S:07f4` installs the filesystem;
`S:07e0` supplies the boot entry, which reaches `S:13f0`. No game-specific
DOS LoadSeg callback, DOSASSIGN, HRTMON or integrated INIT_LOWLEVEL replacement
was identified. Lowlevel/nonvolatile are instead bypassed at game call sites.
The public shared `kick31.s` helps name these mechanisms; macro names are an
interpretation of emitted code, not recovered original source settings.

**The original slave explicitly changes cache policy.** `S:1422` calls
`resload_SetCPU` with mask `7f3f`. Value `032a` is selected normally (base/exp/slave
write-through, instruction/data caches enabled); attention flag bit 3 selects
`3b3d` (68040-or-later indication: base non-cacheable, expansion/slave copyback,
IC/DC, store buffer, branch cache and superscalar bits enabled). These are
requests, not measured CACR values on a particular CPU. This original behavior
is distinct from the future policy in `open-work.md` that leaves cache choices
to WHDLoad/user options. KickEmu's CacheControl/MakeFunctions patches route to
cache flushing (`S:11bc`); the game also flushes its self-modified original c2p
at `E:32072`. No performance or cache-state measurement has been made.

The keyboard hook `S:063c` decodes the incoming raw key and compares the header
exit/debug keys. Exit goes through `resload_Abort` with normal termination.
`S:1524–15ac` forms the existing cheat/system/mission command line: `Custom2`
1 or 2 adds the cheat phrase, 2 adds invincibility, `Custom3` accepts 1–13,
`Custom4` accepts 0–2. Actual gameplay behavior is untested.

## Every game patch

All game patches below target **hunk 0** through `resload_PatchSeg` at `S:14da`.
English common list `S:15e6`, German common list `S:1cf4`: 22 operations each.
P replaces entry with a jump; PS calls a slave helper; S skips the stated byte
count; NOP replaces that many bytes; R returns; B/W/L write a scalar.
These are findings about the existing slave, not patches applied by this project.

| English offset | German offset | Operation / destination | Static purpose |
|---|---|---|---|
| `029b8` | `029fa` | PS `S:16fc` | Guard an indexed pointer before its byte comparison; expansion-relative bound `e0000` |
| `229b2` | `22ad6` | PS `S:1724` | Preserve failed-condition branch; guard nested pointer before dereference |
| `22aa6` | `22bca` | PS `S:1746` | Guard pointer loaded from object +12 before byte read |
| `32028` | `321ea` | P `S:178a` | Replace Akiko conversion entry with software c2p/limiter |
| `2823a` | `283fc` | P `S:1696` | Clear audio channel volume at channel base +8; original used custom base +8 |
| `286ca` | `2888c` | L: CIA-A PRA register pointer | Correct music filter-effect register from CIA-B port B |
| `3386c` | `33a2e` | PS `S:169c` | Set full 32-bit GetColorMap count to 256; reuse graphics base from a0 |
| `33bca` | `33d8c` | W: immediate-source move opcode | Correct palette count load: immediate 256 instead of reading low memory |
| `279c4` | `27b86` | **E: P; G: PS** `S:176a` | Music reset delay: five VHPOSR high-byte changes; English returns directly, German resumes following reset writes |
| `33da0` | `33f62` | S 4 | Skip lowlevel SetJoyPortAttrsA, port 0 |
| `33daa` | `33f6c` | S 4 | Skip lowlevel SetJoyPortAttrsA, port 1 |
| `33db0` | `33f72` | S 4 | Skip initial ReadJoyPort(0) |
| `33db6` | `33f78` | S 4 | Skip initial ReadJoyPort(1) |
| `33e3e` | `34000` | S 4 | Skip teardown SetJoyPortAttrsA |
| `33e48` | `3400a` | S 4 | Skip second teardown SetJoyPortAttrsA |
| `33e6c` | `3402e` | S 10 | Skip library-base check/load and port-0 ReadJoyPort; also changes the value subsequently pushed for port 0 |
| `33e78` | `3403a` | PS `S:1c2e` | Replace port-1 ReadJoyPort with direct CD32 pad/joystick sampling |
| `276b0` | `27872` | NOP 2 | Save-management return path falls through to success value |
| `3141e` | `315e0` | PS `S:16a8` | Replace DeleteNV with resload_DeleteFile |
| `3143c` | `315fe` | P `S:16cc` | Replace GetCopyNV/free with GetFileSize/LoadFile into caller buffer |
| `31498` | `3165a` | PS `S:16b6` | Replace StoreNV with SaveFile; bypass NV ten-byte-unit conversion |
| `314b0` | `31672` | R | Disable GetNVList enumeration routine |

The lowlevel replacement starts with port 1, samples JOY1DAT, CIA-A PRA/DDRA and
POTINP, clocks pad buttons using POTGO/PRA, and returns the bitmask expected by
the game. Timing of its repeated CIA bus reads is unmeasured. Save names are
formed by the game's existing name helper; files go through WHDLoad in the
current data directory. This project has not written any saves.

### Custom5 and conversion selection

| Custom5 | Static selection |
|---:|---|
| 0 | Software c2p with TOD delta threshold 2 |
| 1 | Same software c2p, bypass `S:17b8` wait |
| 2 | Software c2p, threshold 3 |
| 3 | Software c2p, threshold 5 |
| 4 | Clear graphics chunky-to-planar pointer; original **blitter** conversion path, with extra CHIP allocations |

`S:1490–14b4` changes the threshold at `S:17f2` (initially 2), selects optional
prefix lists, and writes `Custom5 - 4` to graphics base +`1fc`
(`gb_ChunkyToPlanarPtr`). For values 0–3 it is a nonzero sentinel: the patched
conversion entry does not dereference it. Value 4 makes it zero, so the branch
at `E:31fc6` uses the game's blitter routines rather than the patched Akiko
entry. **Custom5=4 is not an Akiko execution mode in this slave.**

Two additional operations precede the common list when Custom5=4:

| English offset | German offset | Purpose |
|---|---|---|
| `317cc` | `3198e` | W `ffff`: chunky allocation flag selects CHIP helper |
| `31ef7` | `320b9` | B `14`: original c2p workspace allocation branch selects CHIP helper |

Prefixes `S:15d0` and `S:1cde` then NEXT to their language's common list; they do
not replace that list. No additional game patch list was found.

The software entry `S:178a` saves all registers, optionally waits, and dispatches
on height: 200 to `S:1ac6`, 166 to `S:195e`, everything else to `S:17f6`
(the fixed 128-line implementation). These are full-buffer bit-shuffle routines,
with 320-byte chunky rows and eight planar outputs. Plane strides are 8000,
6640 and 5120 bytes respectively; there is no CPU-specific dispatch or dirty
region test in these bodies. Their results have not been executed or checked
against a pixel oracle. The default-height arm is not proof that arbitrary
heights are supported.

## Time-source inventory — runtime hypotheses

The search covered both executable CODE hunks and DATA, raw hardware constants
at every byte, negative-vector call candidates at every even byte, library-name
strings, and the resolved hardware-base users in code. The slave's helpers and
ROM patch lists were inspected separately. Code/data islands require instruction
boundary checks: a linear sweep alone is not a proof. Indirect calls, generated
copper, Kickstart internals and external library internals remain runtime scope.
There is no claim that an absent literal proves no possible indirect time source.

| Candidate | Static sites / evidence | Runtime question |
|---|---|---|
| VBL game clock | Exec AddIntServer(5) at `E:340e4`; handler `E:34162` increments `D:7f02`, decrements `D:7f06`; removal `E:34154`. Static users: see the VBL clock inventory below | Actual handler cadence, pause behavior, which users run in which scenes |
| VBL wait | `E:33fbe` → `E:34002` → supervisor wait `E:3406c`, STOP until the counter changes; countdown wait `E:340b8` | Which waits execute on each display path; any lost/extra waits? |
| Music VBL server | AddIntServer(5) `E:27720`, handler `E:27810` calls `E:27d52`; initial PAL/NTSC constants 125/104 at `E:27740–27770`, accumulator at `E:27d66–27d80` | Music cadence and cue alignment; tempo is not simply one rendered frame |
| Music short delay | CIA-B TOD low reads `E:27e64/27e70` and `E:27e8e/27e9a`, eight and two changes around audio DMA enable | How these line-clock waits behave under PAL/NTSC and interrupts |
| Slave frame limiter | `S:17c2/17ca/17d2` reads CIA-A TOD high/middle/low; compare against previous timestamp at `S:17ee` and threshold `S:17f2` | Actual TOD frequency, first call, wrap behavior, scenes/calls per game tick |
| Slave music delay | `S:1776/177a` polls VHPOSR high byte five times | Actual elapsed beam time, including rollover |
| Blitter completion | `E:3271e–3272e` polls DMACONR busy; `E:3407e–340a0` sleeps with STOP until busy clears; byte-flag wait `E:340a2` | Active on original blitter path and whether software path reaches any of these |
| Blitter/copper interrupt work | `E:325c6–3266a` sets up interrupt-driven conversion and publication; `E:34192` copper handler is a return stub | Actual installed vectors, completion and publication ordering |
| Joypad VBL | Exec AddIntServer(5) `E:33dc8`, handler `E:33e62` (patched lowlevel calls) | Input sampling rate and its coupling to game updates |
| KickEmu OS time | `S:06a0` seeds timer init from WHDLoad's date/time tag (`S:1212`), converting days/minutes/ticks (ticks divided by 50) | OS time behavior under KickEmu; not evidence of a game timer.device clock |
| KickEmu video selection | `S:0602` reads VPOSR and adjusts PAL/NTSC indication; ROM graphics hooks at the file offsets below | Selected video mode and actual VBL/TOD relationship |

For the corresponding late game routines, German offsets are +`1c2` (verified
separately), including music `G:279d2`, game VBL `G:34324`, and waits
`G:341c4/3422e`. Data offsets differ independently.

**CIA register coverage:** all sixteen CIA register indices were considered,
including Timer A low/high, Timer B low/high, TOD low/middle/high, ICR, CRA/CRB,
ports, direction and serial registers. The game literals resolve to CIA-A PRA
(filter enable), CIA-B PRB (filter bug, patched to PRA), and CIA-B TOD low
(audio delays). No game Timer A/B latch/control/ICR programming was identified,
including in the music code. Resource-name strings do not establish timers.
Slave-specific accesses add CIA-A TOD high/middle/low and pad PRA/DDRA reads and
writes. OS CIA use and keyboard handling inside KickEmu are separate from a
game-owned timer and need a live register-write audit.

**Other searched APIs:** no timer.device string or identified game open of it;
no graphics WaitTOF (-270), WaitBlit (-228), AllocBitMap (-918) or
ChangeVPBitMap (-942) call resolved to the graphics base. The -270 call at
`E:343fa` is intuition SetPointer, not WaitTOF. No lowlevel AddTimerInt,
RemTimerInt, StopTimerInt, StartTimerInt, ElapsedTime, AddVBlankInt or
RemVBlankInt call resolved to the lowlevel base; matching offsets elsewhere
belong to DOS, icon or Exec. No game direct level-3 vector installation or
beam read was identified; VBL uses Exec servers. The level-3 vector is `$6c`
in the architecture, not a game offset. No identified game DOS Delay/DateStamp
clock was found either.

The limiter supports a **two-TOD-increment minimum between conversion entries**
in normal mode, not a measured 15 Hz game tick. The first timestamp bypasses
the wait, and subtraction is not explicitly masked to a 24-bit wrap. Field rate,
render/update coupling and intended rate remain unmeasured. The 15 Hz estimate
in the plan is still only a prior; do not replace it with an FPS inference from
this static threshold.

**Expected limiter rates (hypothesis).** On standard Amiga hardware CIA-A TOD
counts vertical syncs. The loop (`S:17c0–17e4`) repeats until the TOD difference
from the previous exit reaches the threshold, then stores the current reading.
If TOD counts fields, conversions therefore start at most every 2, 3 or 5 fields:
at most 25, 16.7 or 10 per second on PAL (30, 20 or 12 on NTSC) for `Custom5`
0, 2 and 3. A frame that takes longer than the threshold is not delayed. This
caps the conversion rate the slave allows; it says nothing about the intended
game rate. Confirm the TOD clock and the rates at run time.

## VBL clock users — static inventory

`tools/clock_refs.py` lists every A4-relative and relocated-absolute reference
from hunk 0 to the VBL counter (`D:7f02` longword, `D:7f04` its low word) and the
countdown (`D:7f06`). English and German have the same **32 sites** in the same
order (German counter `D:7f2e`, countdown `D:7f32`). No hunk 1 or hunk 3 code
references them. A linear sweep can miss computed or pointer-passed accesses;
the counter's address is taken only by the wait at `E:3406c`.

The counter is real time in fields: it is read by **timed sequences, waits,
animation phases and a game clock**. Field-based durations run 20% faster on
NTSC unless something compensates; nothing in these sites checks the video mode.

| English | German | Classification | Static behaviour |
|---|---|---|---|
| `E:0e64` (`e6e`, `e84`) | `G:0e98`, `0eae` | Deadline wait with service | Deadline = counter + argument; calls `E:70ae`, then loops calling `E:02a8` and `E:0510` until the deadline passes. One caller, `E:1396` |
| `E:1a78` | `G:1aa2` | Animation phase | `(counter / 40) % 3` selects between two values (a 0.8 s phase on PAL); callers `E:1b3e`, `1bd0` |
| `E:1c952` (`1c9a8`, `1c9b6`) | `G:1ca52`, `1ca60` | Timed sequence player | Table of (event, duration) word pairs; advances when elapsed fields exceed the duration. A second table advances per loop pass (`-2(a5)`). Drawing runs every N passes (`-32624(a4)` reloaded from `-32622(a4)`); `E:1898a` can end the loop |
| `E:1d016` (`1d076`, `1d082`) | `G:1d120`, `1d12c` | Timed sequence player | Same pattern; the start is advanced by each duration (`E:1d09e`), so the schedule does not drift |
| `E:1dc2a` (`1ddf0/1ddf6`, `1df20/1df26`) | `G:1de9a/1dea0`, `1dfca/1dfd0` | Fixed-duration scene, per-pass animation | Two loops run until counter + argument; inside, animation advances per pass with the same N-pass drawing divisor. Scene length is real time, animation progress is per pass |
| `E:1fbba` (`1fdd6`, `1fde6`, `1fe2a`) | `G:1feda`, `1feea`, `1ff2e` | Timed pages | Up to 18 pages; each is shown for 320 fields, with a second element at 220 fields; `E:1898a` skips. A credits-like sequence; unverified which |
| `E:22c32` | `G:22d58` | Game clock (read) | `(counter − D:base) / 3300 % 60` gives minutes: one game minute is 3300 fields (66 s PAL). Base at `20432(a4)` |
| `E:254ac` | `G:2562c` | Game clock (set) | Base = counter − (hours × 60 + minutes) × 3300, from bytes `4390/4391(a4)` |
| `E:23154` | `G:232b0` | Snapshot | Stores the counter in `1538(a4)` at the end of an initialisation loop |
| `E:23164` | `G:232c0` | Rate limiter | Acts at most once per 7 fields (low word − snapshot ≥ 7). Mixes a sign-extended word with the stored longword: a wrap candidate after 32768 fields (about 11 min PAL); unverified. Callers `E:23316`, `233fc` |
| `E:23392` | `G:234ee` | Animation phase | `counter / 15` passed to `E:141b4` (a 3.3 Hz step on PAL) |
| `E:239f2` (`23a6c`, `23a74`) | `G:23be2`, `23bea` | Timed sequence player | Same (event, duration) pattern as `E:1c952` |
| `E:262a2` | `G:2644e` | Animation phase | `counter / 3` (16.7 Hz on PAL); in the routine at `E:26292`, called from `E:264c6` |
| `E:32658` | `G:3281a` | Publication timestamp | Original blitter-c2p completion path stores the counter in `-920(a4)` after publishing; no reader in hunk 0 |
| `E:33fca/33fcc` | `G:3418c/3418e` | Countdown set | Clears, then sets `D:7f06` to the argument; 10 callers |
| `E:33fd4/33fd6` | `G:34196/34198` | Countdown test | Returns 1 when the countdown is zero; callers `E:179ae`, `18a84`, `1dbfa`, `1ee0e`, `209c6`, `23c98`, `2538e` |
| `E:33fe0`, `33ff2` | `G:341a2`, `341b4` | Countdown busy wait, clear | Spins until zero; no direct caller found |
| `E:3406c` (via `E:33fbe`, `34002`) | `G:3422e` | One-field wait | Supervisor `STOP` until the counter changes; 10 callers of `E:33fbe`, including the c2p and display setup |
| `E:340be` (via `E:3402e`) | `G:34280` | Countdown wait | `STOP` while the countdown is non-negative. The handler never makes it negative, so this would not return unless something else writes it; its only caller, `E:33fec`, has no direct caller |
| `E:34166`, `3416c`, `34174` | `G:34328`, `3432e`, `34336` | VBL handler | Increment, then decrement the countdown towards zero |

**The per-pass drawing divisor** `-32622(a4)` is set at `E:0b4e` from a computed
value and copied into the working counter `-32624(a4)` at nine sites (`E:02ee`,
`1ca48`, `1db92`, `1de0c`, `1df3a`, `1e3ee`, `1ec6e`, `242f4`, `246a0`). `E:02e4`
is the generic form: it returns 0 until the counter expires, then reloads it,
increments `4434(a4)` and continues to the drawing path. Whether this divisor is a
user setting, a detail level or a speed compensation is unresolved; it is the
first candidate for frame coupling inside the real-time sequences.

Consequences to confirm at run time: sequence and scene lengths should be
independent of drawing speed, while animation inside `E:1dc2a`-style loops and
everything driven by `E:02e4` is per pass. None of these sites has been
identified as part of space flight's world update; flight may be entirely
per-frame apart from the game clock.

## Display path — runtime hypotheses

The main renderer uses **graphics.library View/ViewPort/BitMap structures and
OS-generated copper lists, with direct copper publication**. It is not simply
an Intuition screen flip. `E:3394c` does call intuition OpenScreen for an
auxiliary 320×15, depth-2 screen, whose structure is at `E:339b2`; do not mistake
that for the main eight-plane image.

Main layout evidence:

- `E:33818` rounds width to 64 pixels, derives bytes-per-row and plane stride,
  sets depth 8, and computes eight planes per buffer. For the software paths,
  width 320 and heights 128/166/200 imply stride 40 bytes/row, plane sizes
  5120/6640/8000 and buffer sizes 40960/53120/64000 bytes.
- `E:33650–33680` allocates **two** planar buffers plus 8 bytes through the CHIP
  helper; rounds the first base upwards to an 8-byte boundary and spaces them
  by the computed buffer size. `E:33d22` constructs two BitMaps with eight
  contiguous, non-interleaved planes. These strides preserve 8-byte alignment.
- The CHIP allocation helper `E:3460a` passes `MEMF_CLEAR | MEMF_CHIP | MEMF_PUBLIC`
  (`10003`) to AllocMem at `E:3463e`. The generic helper `E:34620` passes
  `MEMF_CLEAR | MEMF_PUBLIC` (`10001`), **not MEMF_FAST**. `E:317d8` builds chunky
  surfaces, rounds rows to four bytes, and selects either helper from its flag.
  Normal use at `E:317cc` selects generic memory; Custom5=4 changes it to CHIP.
  Actual fast/chip placement must be observed, not assumed from available RAM.
- `E:31ef2–31ef4` allocates original c2p workspace (16 plane-sized areas) through
  the generic helper, changed to CHIP by the Custom5=4 prefix. A separate
  `20000`-hex-byte (128 KiB) workspace request at `E:31f4c` also uses generic memory.
- `E:33a8a` initialises a View, `E:33ae8` a ViewPort, and `E:33c64` calls MakeVPort
  then MrgCop for each BitMap. `E:33caa` selects the generated copper list and
  `E:33ce2` writes COP2LC after updating graphics-library copper pointers.
  `E:33772` alternates indices modulo two; `E:3378e` publishes the completed
  index through `E:33a12`. This is a candidate frame-publication marker, not
  yet a validated frame counter.
- The normal software branch at `E:31fee` converts, advances the buffer index,
  then publishes. The original blitter branch at `E:31fcc` starts asynchronous
  conversion; its interrupt/completion path can publish at `E:3264e`.

**FMODE/BPLCON remain unresolved runtime values.** No direct game FMODE write
or explicit main-renderer BPLCON register write was identified in the resolved
hardware-base code. Graphics.library emits the lists from the mode/depth
structures (`E:33ab2`, `E:33b16`); eight planes require the AGA depth encoding.
The slave's generic graphics hook `S:0554` writes BPLCON0 during ROM setup,
while `S:05dc` restores COP2LC/BEAMCON0/DIWHIGH on WHDLoad switches. These are
not a measurement of the main display's BPLCON0/1/2/3/4, FMODE, DDF or modulos.
Read both generated lists and the actual writes before changing fetch mode;
eight-byte allocation alignment alone does not prove FMODE=3.

## Complete KickEmu ROM patch inventory

These are **ROM file offsets**, never game-hunk offsets. They are decoded from
slave lists `S:007a` (A600), `S:01f2` (A1200) and `S:035e` (A4000), selected at
`S:004e–006a`. No ROM bytes were extracted or analysed. Names are interpretations
from the public KickEmu source and the slave helper bodies. C clears a byte
range, CB clears one byte; other operations use the game-table legend above.

| A600 file offset | A1200 file offset | A4000 file offset | Operation | Interpretation |
|---|---|---|---|---|
| `0000d6` | `0000d6` | `0000d6` | S skip 144 bytes; A4000 52 | Boot/probe skip |
| `000166` | `000166` | `00010a` | PS S:0516 | Overlay/LED handling |
| `0001a6` | `0001a6` | `000180` | S skip 42 bytes | Boot/probe skip |
| `000240` | `000240` | `00021a` | PS S:0520 | Chip-memory size |
| `000246` | `000246` | `000220` | S skip 36 bytes | Chip detection skip |
| `000334` | `000334` | `00030e` | S skip 6 bytes | Fast detection skip |
| `000376` | `000376` | `000350` | L -1 | Disable high-ROM resident search |
| `00038e` | `00038e` | `000368` | P S:0528 | Fast-memory bounds |
| `000460` | `000460` | `00043a` | R  | Skip board-specific probe |
| `0005e8` | `0005e8` | `0005c0` | S skip 22 bytes | Preserve vectors |
| `000634` | `000634` | `00060c` | PS S:0500 | Install vectors |
| `00066a` | `00066a` | `000642` | S skip 12 bytes; A4000 20 | Preserve vectors |
| `000a4c` | `000a4c` | `000a54` | C clear 12 bytes | Clear vector-init code |
| `000a5a` | `000a5a` | `000a62` | C clear 32 bytes | Clear vector-init code |
| `000c1c` | `000c1c` | `000c24` | P S:053c | CPU detection |
| `000d36` | `000d36` | `000d3e` | P S:11bc | CacheControl → flush |
| `000db8` | `000db8` | `000dc0` | P S:0072 | ColdReboot entry |
| `001380` | `001380` | `001388` | PS S:0546 | ExitIntr handling |
| `001c6c` | `001c6c` | `001c74` | PS S:11bc | MakeFunctions → flush |
| `03cefc` | `0038f8` | `049f44` | S skip 162 bytes; A1200 264; A4000 292 | Skip autoconfiguration |
| `041ac4` | `0042f4` | `04006c` | PS S:07f4 | Filesystem initialisation |
| `00bd70` | `00b484` | `02a9dc` | PS S:0602 | PAL/NTSC VPOSR |
| `00bd8c` | `00b4a0` | `02a9f8` | S skip 16 bytes | Skip byte bitplane writes |
| `00c028` | `00b73c` | `02ac94` | S skip 6 bytes | Skip init blitter wait |
| `00c044` | `00b758` | `02acb0` | S skip 6 bytes | Skip init blitter wait |
| `00c2e4` | `00b9f8` | `02af50` | PS S:062c | AGA initialisation |
| `00c35e` | `00ba72` | `02afca` | PS S:0554 | Initial BPLCON0 |
| `00c46a` | `00bb7e` | `02b0d6` | P S:0628 | Genlock result |
| `00ffc4` | `00f6d8` | `02ec30` | PS S:055e | BEAMCON0 state |
| `01001a` | `00f72e` | `02ec86` | PS S:0574 | Copper/DIWHIGH state |
| `010034` | `00f748` | `02eca0` | PS S:0596 | Copper/DIWHIGH state |
| `010082` | `00f796` | `02ecee` | PS S:0596 | Copper/DIWHIGH state |
| `0100aa` | `00f7be` | `02ed16` | PS S:05b8 | BEAMCON0 state |
| `0100cc` | `00f7e0` | `02ed38` | PS S:05d2 | Graphics byte-access correction |
| `01543a` | `014b4e` | `0340a6` | PS S:0602 | PAL/NTSC VPOSR |
| `02305c` | `022772` | `018b9a` | L 5000 longwords | DOS stack = 5000 longwords |
| `023100` | `022814` | `018c3c` | PS S:07e0 | DOS boot entry |
| `035936` | `03504a` | `007e3e` | CB  | Disable SCSI resident |
| `004ed2` | `03a7ea` | `00d3ee` | PS S:063c | Keyboard/quit hook |
| `03e332` | `03ddf2` | `044fc6` | CB  | Disable battery-clock resident |
| `04013c` | `040414` | `041a10` | S skip 34 bytes | Skip disk-unit detection |
| `04028e` | `040566` | `041b62` | P S:0698 | Disk unit ID |
| `040296` | `04056e` | `041b6a` | P S:0698 | Disk unit ID |
| `03c246` | `040d3a` | `00c01a` | P S:06a0 | Timer initial date/time |
| `0446aa` | `044a5a` | `04b84e` | P S:07b8 | Trackdisk task |
| `044ea8` | `045258` | `04c04c` | P S:06cc | Trackdisk format |
| `0452ec` | `04569c` | `04c490` | P S:0768 | Trackdisk motor |
| `0455dc` | `04598c` | `04c780` | P S:06cc | Trackdisk read/write |
| `0459aa` | `045d5a` | `04cb4e` | PS S:0774 | Trackdisk protection status |
| `045e80` | `046230` | `04d024` | PS S:07a6 | Trackdisk initialisation |
| `068900` | `068cb0` | `06799c` | B 8 | Font height 8 |
| `068966` | `068d16` | `067a02` | C clear 6 bytes | Clear colors 17–19 |
| `06896e` | `068d1e` | `067a0a` | C clear 8 bytes | Clear colors 0–3 |
| `06896c` | `068d1c` | `067a08` | W 1 | PointerTicks = 1 |

The A4000 list has four additional operations (58 total, versus 54 each for
A600/A1200): file `000146` skips 38 bytes; `000174` skips 8 bytes (early machine
initialisation); `04a024` skips 8 bytes; `01e67a` replaces an entry with a zero
return. The final two are A4000-specific ROM workarounds; their subsystem names
are not established here. All lists terminate explicitly. There is no ROM
patch at an invented runtime base in this inventory.

## Gate hand-off

Written executable/slave identification, both language patch maps, all three
KickEmu ROM patch maps, and the static time/display hypotheses are present.
Reproduction commands and limitations are in `development.md`. The gate is
satisfied **as a static description**, not as runtime correctness or timing proof.

When runtime work is separately authorised, confirm: selected CRC/language and
Kickstart; CACR after the original SetCPU call; actual interrupt/vector and CIA
register traffic (including library code); TOD cadence and wrap; c2p branch for
each Custom5; chunky/planar placement and geometry; generated copper/FMODE/BPLCON
values; buffer publication versus completed frames; the VBL clock users and the per-pass drawing divisor in each scene; music cadence and game-time
coupling. Exact compiler and KickEmu source release remain unknown metadata.
Do not start reconstruction, boots, patches or phase 2 from this hand-off alone.
