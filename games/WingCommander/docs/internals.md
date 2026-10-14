# Known internals

## Phase 1 gate: CD32 static identification complete

The identification sections record static evidence from verified extraction,
hunk/relocation parsing, slave patch lists and 68020 disassembly. Their time-source
and display-path descriptions remain hypotheses except for the explicitly scoped
runtime confirmations in the phase 2 and phase 3 sections below. The OCS executable
has a separate static investigation below; its runtime behaviour is not yet validated.

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
  index through `E:33a12`. This is the static frame-publication candidate; the scoped phase 3
  runtime validation appears below.
- The normal software branch at `E:31fee` converts, advances the buffer index,
  then publishes. The original blitter branch at `E:31fcc` starts asynchronous
  conversion; its interrupt/completion path can publish at `E:3264e`.

**Runtime update (phase 6):** the captured credits and menu copper lists use
FMODE 3, DDF `0038/00d8` and modulos `fff8`, with aligned CHIP planes. The phase-6
section records the evidence and scope. Other display states remain unverified.
No direct game FMODE write was identified statically: graphics.library generates
the lists from the mode/depth structures at `E:33ab2` and `E:33b16`. The slave's
generic graphics hook `S:0554` writes BPLCON0 during ROM setup; `S:05dc` restores
COP2LC/BEAMCON0/DIWHIGH on WHDLoad switches. These hooks alone do not establish
the active display registers.

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

## Phase 1 gate

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
These remain outside the phase 2 equivalence checks below.

## Phase 2 reconstruction (gate complete)

`tools/reconstruct.py` reconstructs 1,758 instructions (5,008 bytes) from the
original slave's code islands; the remaining payload is data. The whole assembled
file is byte-identical: 7,728 bytes, SHA-256
`5fbbb774bba3c794a776acc25f33c3f47c579449e1ba1a21c31418716aa74986`.
This includes the original KickEmu, patch tables and cache policy. All generated
source and binaries stay under `tmp/`.

Two disassembler details require explicit correction: the PC-relative 020
memory-indirect jump at `S:0072` has a signed base displacement, and MOVEM at
`S:14e4` bases its displacement after the register-mask word. The generator
corrects their textual targets and the full-file comparison checks the result.

### Runtime route and coverage

English boots use PAL A1200-fast, 68EC020, 2 MiB chip and 8 MiB fast RAM,
windowed at real speed. Native debugger keyboard input skips the logo and credits
with two separate Escape presses, selects the Vega campaign with Return, then
provides no input through the simulator's automatic destruction. The endpoint is
the first name-input loop, showing the name/callsign request; no name is entered.

| Checkpoint | English hunk 0 | Executable file |
|---|---|---|
| Intro/credits input poll | `1898a` | `189b6` |
| Credits entry | `1fbba` | `1fbe6` |
| Menu entry | `20164` | `20190` |
| Menu ready | `20214` | `20240` |
| Selection accepted | `20226` | `20252` |
| Name prompt call | `1744c` | `17478` |
| First name-input iteration | `16fc6` | `16ff2` |

The live patched LoadSeg chain is calibrated separately from PRELOAD/file copies.
Each endpoint retains all four allocated game hunks (291,288 bytes total), fast
RAM, input/checkpoint logs and a one-field screenshot. Comparisons require equal
placements and input routes, and apply no masks or pixel tolerance.

| Custom5 | Menu: game bytes / RGB pixels | Name prompt: game bytes / RGB pixels |
|---|---|---|
| 0 | identical / identical | identical / identical |
| 1 | identical / identical | identical / identical |
| 2 | identical / identical | identical / identical |
| 3 | identical / identical | identical / identical |

Evidence is retained in `tmp/phase2-ab/`, including all eight fresh boots and
`menu-0..3.json` / `name-0..3.json` comparison reports. Deliberately changing one
data byte or one screenshot pixel makes the gate fail. A damaged input digest
and a missing live slave patch are also rejected by their respective checks.

### Diagnostic control

The VERIFY build changes only the call at `S:14da` (slave file `14fa`) to enter
an appended seam at `S:1e0c` (file `1e2c`). It calls the original PatchSeg and
preserves its register/CCR outputs. `CUSTOM1=2` selects English and sets a marker
at `S:1e34` (file `1e54`); default English and German selection retain their
original values, 0 and 1. No new game patches are installed.

An equal-size control retains every original payload byte and appends the unused
seam, avoiding different slave placements in the comparison. At both endpoints,
its marker and VERIFY-off's marker are zero; VERIFY-on's marker is one. Both
VERIFY modes match every game-hunk byte and screenshot pixel of the control.
Evidence: `tmp/verify-reference/`, `tmp/verify-off/`, `tmp/verify-on/`.
The ordinary reconstruction remains the byte-identical original-size build.

This gate covers the English install and this emulator preset only. It does not
validate German runtime behaviour, other CPUs, OCS, intended game speed, or the
phase 1 time-source/display-path hypotheses. The phase 2 checks establish no frame counter or instruction-cost profile.
Phase 3 evidence follows separately.

## Phase 3: unskipped intro and publication counter

The runtime window uses the original English slave, `CUSTOM5=0`, PAL,
cycle-exact 68EC020 at the A1200-fast preset with stock CPU multiplier 4,
2 MiB chip and 8 MiB fast RAM.
It includes reset/startup, the full Origin animation, the title animation,
all 18 flight/credits pages, and the main menu. The credits loop indefinitely;
a single Escape press is therefore sent **after** `E:1fe48` completes page 17,
at the next input poll. Release occurs at menu entry. Nothing is skipped on the
first cycle and no earlier input is sent.

### Milestones and the counted event

| State or event | Hunk offset | English executable file offset |
|---|---|---|
| Game startup | hunk 3:`0000` | `42dec` |
| Origin load | hunk 3:`0d12` | `43afe` |
| Origin reveal | hunk 3:`0eb0` | `43c9c` |
| Origin animation | hunk 3:`0ee0` | `43ccc` |
| Origin expression | hunk 3:`0fb4` | `43da0` |
| Origin separation | hunk 3:`10cc` | `43eb8` |
| Origin flight/hold | hunk 3:`11a8` | `43f94` |
| Origin particles/logo | hunk 3:`12c0` | `440ac` |
| Origin fade/cleanup | hunk 3:`0de0` | `43bcc` |
| Title load | `E:1fbba` | `1fbe6` |
| Title preamble | `E:1fcfc` | `1fd28` |
| Title arrival | `E:1fd3a` | `1fd66` |
| Title departure | `E:1fd46` | `1fd72` |
| Flight/credits load | `E:1fd96` | `1fdc2` |
| Credits page entry, D5 = 0…17 | `E:1fdd6` | `1fe02` |
| Complete credits cycle | `E:1fe48` | `1fe74` |
| Menu ready | `E:20214` | `20240` |
| Publication entry | `E:3378e` | `337ba` |
| Publication return from display helper | `E:3379a` | `337c6` |
| COP2LC longword store | `E:33ce2` | `33d0e` |
| Game VBL handler entry | `E:34162` | `3418e` |

Scene cuts use the routine/state transitions above; the title screenshot uses
animation index D2=185 within the arrival state. Credits screenshots follow the
first completed publication for each page. Other scene pictures follow their
first publication; load/fade pictures can consequently be black. These are exact
state checkpoints, not screenshots selected by elapsed field number.

For this software-c2p route, every observed publication entry has exactly one
COP2LC store before `E:3379a`. The engine has finished conversion and selected
its completed buffer before this helper. Counting all COP2LC stores would be
wrong: the run also contains 68 writes outside publication calls (display setup
and palette-related paths). A buffer index/pointer can repeat across display
reinitialisation, so pointer inequality is not the counter either.

The counter measures **completed buffer publications**, including cleared/setup
frames. It does not count palette-only changes or require visually unique images.
It is not a proof that a mid-field publication is tear-free. The blitter path
`CUSTOM5=4`, other CPUs and German/OCS remain outside this validation.

### Instrument agreement and clock calibration

A local native debugger explicitly sets its profiler PC window; an unconfigured
native trace can have instruction records without usable RAM PCs. The read-only
host ledger records selected instructions, full register snapshots, physical
field numbers, monotonic emulator cycle stamps and music variables. It adds no
guest code and remains active across screenshot captures.

The 20-field Origin window contains **4 publications**; the 20-field
flight/credits window contains **6**. Full instruction traces and the ledger agree
on every watched PC/register tuple and its physical field, including window
edges. Both windows contain one game VBL entry per physical field, and each
publication agrees with its helper return and COP2LC store. An independent GDB
**SWAP_ONLY** run, with the host ledger disabled, gives the identical Origin
pattern and game-clock interval: publications at relative fields 3, 8, 12, 17.

Across the whole captured run, all 8,322 consecutive game-VBL intervals advance
both the physical-field number and `D:7f02` by one. This confirms that counter's
cadence in this run only. VBL entry has small interrupt latency: adjacent observed
entry scanline differences can be 312/314 around the normal 313, so entry position
is not treated as a perfect beam boundary. UAE uses 512 units per chip clock and
`baseclock = 8 × CHIPSET_CLOCK`; the observed PAL baseclock is 28,375,160.

The stock 020 multiplier is important: in the pinned emulator's `newcpu.cpp`,
`CYCLE_UNIT * baseclock / cpu_frequency` uses 32-bit arithmetic. For the shared
preset's numeric frequency, the product 14,528,081,920 overflows; this binary
reports a CPU cycle unit of **115**. The core's stock 020 configuration in
`cfgfile.cpp` uses multiplier 4, yielding **128** without that calculation.
The phase 3 launcher applies this locally and checks the actual emulator log;
all accepted ledger records also require 128. The shared installation is unchanged.
Phase 2 remains an equivalence test under its recorded preset, not a calibrated
CPU-speed baseline. Numeric-frequency matrix presets need separate validation
before phase 4 measurements.

Elapsed seconds below use cycle-stamp differences divided by 512 and 3,546,895,
not host duration or an assumed exact 50 fields/s.

### Per-scene observations

Music position is `(cue16, order, row, tick)`, with active/stopped recorded in the
machine-readable report. `D:4bbc` (file `3ec04`) is the cue counter incremented
when the tracker row reaches a multiple of 16 (`E:28156–2815e`). Order is the byte
at `D:519f` (file `3f1e7`), row the word at `D:51ac` (file `3f1f4`), tick the byte
at `D:519e` (file `3f1e6`), and active the byte at `D:51a5` (file `3f1ed`).
`E:27f36–27f48` advances the tick/row path; `E:281a8–281c6` advances/selects the
order. These identify tracker state, not elapsed audio samples or an intended-rate
estimate. Loading a new track resets its position.

Fields are the physical-field difference between state entries. Seconds include
loading/holds. F/P is the mean gap between consecutive publications **within** the
scene, absent if fewer than two occur; it deliberately does not divide a long
hold by an unrelated frame count. Full gap histograms and both music endpoints
are retained by `intro_report.py`. The last row ends at menu ready.

| Scene | Fields | Emulated s | Publications | F/P | Music at entry |
|---|---:|---:|---:|---:|---|
| reset | 601 | 12.038 | 0 | — | stopped |
| game-startup | 72 | 1.455 | 4 | 5.333 | stopped |
| origin-load | 39 | 0.776 | 5 | 5.000 | stopped |
| origin-reveal | 60 | 1.197 | 1 | — | 0/0/0/0 |
| origin-animation | 133 | 2.672 | 30 | 4.448 | 0/0/10/0 |
| origin-expression | 265 | 5.300 | 21 | 4.450 | 2/0/32/1 |
| origin-separation | 71 | 1.431 | 17 | 4.188 | 4/1/0/0 |
| origin-flight | 506 | 10.127 | 42 | 3.878 | 4/1/0/71 |
| origin-particles | 321 | 6.449 | 100 | 3.222 | 9/2/16/0 |
| origin-fade | 226 | 4.513 | 6 | 5.200 | stopped |
| title-load | 99 | 1.985 | 5 | 5.250 | stopped |
| title-animation | 307 | 6.147 | 67 | 4.576 | 0/0/0/3 |
| title-arrival | 225 | 4.505 | 50 | 4.531 | 3/0/51/4 |
| title-departure | 150 | 3.019 | 31 | 4.733 | 5/1/25/1 |
| credits-load | 11 | 0.223 | 0 | — | 7/2/26/3 |
| credits-00 | 322 | 6.448 | 81 | 3.987 | 7/2/29/2 |
| credits-01 | 322 | 6.442 | 74 | 4.342 | 12/4/14/0 |
| credits-02 | 320 | 6.414 | 75 | 4.270 | 17/5/46/2 |
| credits-03 | 323 | 6.469 | 74 | 4.356 | 22/7/20/4 |
| credits-04 | 320 | 6.417 | 73 | 4.375 | 26/9/15/1 |
| credits-05 | 322 | 6.436 | 73 | 4.403 | 31/10/47/1 |
| credits-06 | 324 | 6.490 | 72 | 4.507 | 36/12/31/3 |
| credits-07 | 323 | 6.485 | 72 | 4.493 | 41/14/15/3 |
| credits-08 | 322 | 6.443 | 71 | 4.529 | 46/15/36/0 |
| credits-09 | 320 | 6.415 | 71 | 4.500 | 49/17/1/1 |
| credits-10 | 322 | 6.446 | 69 | 4.662 | 51/17/41/1 |
| credits-11 | 322 | 6.457 | 73 | 4.417 | 54/18/17/3 |
| credits-12 | 323 | 6.456 | 69 | 4.676 | 56/18/57/5 |
| credits-13 | 320 | 6.424 | 71 | 4.500 | 59/19/34/0 |
| credits-14 | 320 | 6.401 | 72 | 4.437 | 61/20/10/0 |
| credits-15 | 320 | 6.403 | 72 | 4.437 | 64/20/50/0 |
| credits-16 | 322 | 6.458 | 72 | 4.479 | 66/21/26/0 |
| credits-17 | 321 | 6.431 | 75 | 4.284 | 70/23/6/1 |
| cycle-complete | 50 | 0.999 | 8 | 4.714 | 74/24/22/2 |

The complete reset-to-menu interval contains **1,696 publications in 178.771
emulated seconds**. This is a description of this unmodified route, not a
performance improvement, intended game rate, or machine-matrix baseline. Music
coupling, presentation geometry, cache policy and all other phase 1 timing/display
hypotheses remain open except for the scoped publication/VBL observations above.


### Phase 3 gate

Two independent fresh boots (`tmp/intro-pal-a/` and `tmp/intro-pal-b/`) give the
same 31 screenshot milestones, every RGB pixel, and every allocated game-hunk
byte at each checkpoint. All **13,594** observer records from reset through the
first menu-ready instruction are identical, including clocks, registers and
music positions. Per-scene reports match exactly. Emulator shutdown after the
endpoint is outside this comparison; the menu screenshot is checked separately.

Both boots' Origin and flight/credits traces agree with their ledgers. The
independent `tmp/intro-pal-counter/` SWAP_ONLY run agrees with the Origin trace
at game-clock entries 175…195. `tmp/phase3-gate.json` records the combined pass.
Negative controls reject a missing publication, wrong field, changed pixel and
changed game-hunk byte (`tmp/intro-negative.json`). The original slave digest is
unchanged. No reconstructed slave change was needed.

The phase 3 gate is complete. These are measurements of this observed original
intro route, not a CPU performance profile or proof of intended timing. Phase 4 is separately authorised below. Performance patches, the blitter route,
German runtime and OCS remain deferred.


## Phase 4: practical baseline (gate complete)

The user approved closing phase 4 with the practical baseline and documented
gaps on 2026-10-12. All eleven configurations have cache-audited scene and
source-change measurements plus validated DMA and STOP idle controls. Eight
have consolidated callback validation. Representative leaf costs and the three
scoped ceiling experiments provide the optimisation evidence below. General
routine and complete interrupt/wait attribution remain deferred. No phase 5
work or rendering release patch has started.

### Hardware cache audit

The separate terminating VERIFY build detours the original `SetCPU` call at
`S:1422` (slave file `1442`). It executes that call unchanged, queries `SetCPU`
and `SetCACR` with zero change masks, reads hardware CACR through Exec Supervisor,
and writes one `resload_Log` record before normal termination. Only this build
raises the slave API version from 17 to 18 for the logging API. It does not supply
performance timings. Ordinary reconstruction still matches the pinned original
byte for byte.

All 15 fresh audit boots completed with `CUSTOM5=0`:

| CPU/configuration | Default CACR | With `DCache` | With `NoCache` |
|---|---:|---:|---:|
| A1200 fast, 020 | `00000001` | `00000001` | `00000000` |
| 030, no WHDLoad MMU option | `00002111` | `00002111` | `00002000` |
| 030, WHDLoad `MMU` | `00002111` | `00002111` | `00002000` |
| 040, WHDLoad `NoMMU` | `00000000` | `80008000` | `00000000` |
| 060, WHDLoad `NoMMU` | `20800000` | `a0808000` | `00000000` |

`DCache` therefore makes no observed cache-state change on this original 020/030
slave, but enables instruction/data caching on the 040/060 audits. `NoCache`
disables those caches on 020/030. Other CACR bits must not be conflated with the
instruction/data enable bits. These are observations immediately after the
original slave's cache request; a later timing run must also check its live state.

The audit slave is 7,860 bytes, SHA-256
`99512207a79b3b4558787b156f53f85566fb0afacdfa656b3880ef6c36985cd6`.
Retained records are `tmp/phase4-audit-{020,030,030-mmu,040,060}-{default,dcache,nocache}/`.
The original performance-run slave remains SHA-256
`5fbbb774bba3c794a776acc25f33c3f47c579449e1ba1a21c31418716aa74986`.

### Instrument coverage is a prerequisite

Five original-slave preflight boots reach the flight/credits checkpoint
`E:1fdd6` (file `1fe02`). They explicitly enable the whole-RAM trace PC window,
then request a five-field instruction trace and aggregate profile. Emulator
configuration is read back at reset and at the checkpoint.

| Requested cell | Observed backend | Preflight result |
|---|---|---|
| A1200 fast, 020 | cycle-exact, no hardware MMU model, cycle unit 128 | 427,130 instruction records; aggregate profile available |
| 030/50 | cycle-exact, hardware MMU model 030, cycle unit 32 | zero instruction records; aggregate profiler rejects backend |
| 030/50, WHDLoad `MMU` | same hardware backend | zero instruction records; aggregate profiler rejects backend |
| 040/25, WHDLoad `NoMMU` | non-cycle-exact, hardware MMU model 040, cycle unit 32 | zero instruction records; aggregate profiler rejects backend |
| 060/50, WHDLoad `NoMMU` | non-cycle-exact, hardware MMU model 060, cycle unit 32 | zero instruction records; aggregate profiler rejects backend |

Zero coverage is **unavailable data**, not zero CPU cost, publications or interrupts.
A WHDLoad `NoMMU` option does not remove the emulator's configured MMU model;
configured hardware capability alone also does not prove guest translation is on.
The shared source dispatches an MMU-model 030 through `m68k_run_mmu030`; the
aggregate profiler instruments `m68k_run_2ce` and explicitly rejects MMU models.
Its instruction-trace hooks likewise do not cover the accelerated backends used
here. The 040/060 probes report memory and blitter cycle-exact modes disabled and
multiplier 2048. Their nominal MHz labels are not calibrated timing evidence.
The numeric-frequency arithmetic issue recorded in phase 3 also remains relevant.
Adding counters alone would not establish a valid accelerated timing model.

Retained preflights are `tmp/phase4-probe-{020,030,030-mmu,040,060}/`.
The local audit/probe debugger SHA-256 is
`c3292762b619d735182d68ee60326dc9950284a90ce575b84873aa5887b38352`;
shared tools were not modified. The source revision and modified source inputs
are checked by `manifest/debugger.tsv` before each local build.

### Corrected NOMMU-core coverage

The `68EC030` preflight in `tmp/phase4-nommu-probe-030/` reaches the same
`E:1fdd6` checkpoint with the original slave. Effective settings report model
68030, MMU zero, CPU/memory/blitter exact enabled, requested frequency 50 MHz,
multiplier zero, cycle unit 32 and live CACR `$00002111`. Its five-field sample
contains 802,766 instruction records, including 201,773 in the executable's first
hunk, three publication entries and five VBL entries. Aggregate profiling is
available. The emulator digest is
`95329265de9f948787a6494fd8029d3e3516113b315f14dd586c00b37764494f`.
This establishes instruction coverage on the corrected 030 core, not validated
50 MHz costs, calling-context attribution or a completed matrix baseline. The
WHDLoad-MMU cell remains separate.

The corrected 040 and 060 probes also reach the checkpoint. Both report MMU
zero and CPU/memory/blitter exact enabled. At requested 25/50 MHz they report
cycle units 65/32 respectively, live CACR `$00000000`/`$20800000`, and zero
instruction records; aggregate profiling rejects both. This establishes that the
core-selection correction alone does not add instruction-cost coverage on these
CPUs. Data are in `tmp/phase4-nommu-probe-{040,060}/`.

A local debugger with `--matrix-nommu-counters` adds scene/census observations at
the 040/060 NOMMU interpreter's pre-fetch PC, separately from the unavailable
instruction profiler. The build succeeds; full-run reproducibility and observer
neutrality are not yet validated. Its digest is
`b624c41c58053e7012de18f9e48c1c0e9cb366b34c3fcb57c037cb9c5499885f`.
A matching terminating 040 `NoMMU` audit reports CACR zero in
`tmp/phase4-nommu-audit-040/`. This does not replace audits for other cores/options.

### 040/060 NOMMU scene-counter validation

The first complete counter-only capture, `tmp/phase4-nommu-scenes-040/`, reaches
all 35 boundaries in order and passes the independent ledger checks. Raw-source
recomputation matches all 3,342 c2p entries (3,310 comparisons in 31 scenes),
covering 136,957,440 recorded bytes. The scene validator checks exact cut offsets,
chronological records, cache audit agreement and census bounds; it also accepts
the established 020 capture. Negative fixtures reject a missing boundary, a wrong
CACR, a backwards timestamp and a c2p event assigned to the wrong scene.

The fresh recording-off control `tmp/phase4-nommu-control-040/` matches all
6,739 ledger records, every final allocated game-hunk byte and every menu RGB
pixel. The two runs use the same effective core settings and emulator/slave
hashes; raw-source recording is the sole changed feature. The comparison passes
in `tmp/phase4-nommu-recording-check-040.json`.

The isolated warp control `tmp/phase4-nommu-warp-040/` likewise matches all
6,739 records, final game hunks and menu pixels against the recording-off control.
Only host warp changes. `tmp/phase4-nommu-warp-check-040.json` records the pass;
warp may now be used for this capture path without converting host elapsed time
into an emulated timing claim.

These checks establish record integrity, census arithmetic, scoped repeatability
and source-recording neutrality. They do not independently validate the observer's
PC acquisition or calibrate the requested CPU MHz. No accelerated timing baseline
or instruction-cost claim follows from them. The negative results are in
`tmp/phase4-scene-negative/negative-results.json`.

The first 060 counter capture `tmp/phase4-nommu-scenes-060/` also completes the
35 boundaries. Its separate audit reports CACR `$20800000`; full raw recomputation
passes all 3,342 calls, covering 136,957,440 source bytes. Repetition and independent observer checks of this superseded capture are
not pursued; accepted corrected-clock evidence is recorded below. The digest is the same NOMMU-counter
build listed above. These are diagnostics under the original numeric-clock
scaling, not a corrected-clock baseline.

### Numeric CPU-clock scaling

The optional local `--frequency-clock` build corrects the numeric-frequency path
without changing the shared installation. `get_cycles()` uses 512 units per PAL
colour clock (3,546,895 Hz), whereas the source's `baseclock` is eight times that
clock. The replacement widens the multiplication and computes
`floor(512 * (baseclock / 8) / requested_frequency)`. The existing multiplier
path is unchanged. Merely widening the original multiplication would preserve an
eightfold scale disagreement with the verified stock 020 multiplier.

The candidate digest is
`44b8e4f44798af096e6c72da94999c6a726dba192fb985cc746f7195c2126ac0`.
At numeric 14,187,580 Hz its five-field original-slave trace matches the stock
multiplier reference exactly: all 427,130 PC/cost/register records, trace memory,
pixels, DMA bytes and custom-register bytes. The aggregate profile independently
covers all trace PCs and costs. Evidence is in `tmp/phase4-frequency-probe-020/`
and `tmp/phase4-frequency-stock-check.json`, against
`tmp/phase4-stablepc-probe/`. This validates the numeric scaling at the stock
reference, not the physical accuracy of every CPU's instruction/memory model.

| Requested frequency | Internal unit | Implied internal-cycle frequency |
|---|---:|---:|
| 14.187580 MHz | 128 | 14.187580 MHz |
| 25 MHz | 72 | 25.222364 MHz |
| 50 MHz | 36 | 50.444729 MHz |

The integer unit quantises the accelerated settings. The corrected 030 probe
reads back unit 36, reaches the checkpoint, and records 684,458 instructions in
five fields, including 207,121 game-hunk instructions, three publications and five
VBL entries. Both trace and aggregate instrumentation are available. The 040/060
unit values in the table follow the formula; corrected-core readbacks still need
to be collected. Their per-instruction costs remain unsupported.

The corrected 030 full capture `tmp/phase4-frequency-scenes-030/` passes scene,
profile accounting, live leaf-byte/entry checks and raw-source recomputation
(3,342 calls, 3,310 comparisons, 136,957,440 source bytes). The report now supports
covered NOMMU 030 profiles; the established 020 leaf report remains byte-identical.
General caller attribution is still unresolved. The first profiler-off control
lost the emulator connection in the credits and has no success record; its partial
output is retained in `tmp/phase4-frequency-control-030/`. The fresh retry in
`tmp/phase4-frequency-control-030-retry/` completes and matches all 6,739 ledger
records, every raw source byte, final allocated game hunks and menu RGB pixels.
Only aggregate profiling changes; `tmp/phase4-frequency-profiler-check-030.json`
records the isolated neutrality pass. No failed run is included as a baseline.

The verified 030 instruction-body shares illustrate the current cost split:
Origin animation spends 39.571% in the 128-line converter and 23.490% in its TOD
limiter; the particle scene spends 39.429% and 40.663%, respectively. These use
whole-scene duration as denominator, include instruction memory stalls, and
exclude interrupt service and between-instruction gaps. They do not price general
calling contexts or establish an intended game rate.

### 020 whole-scene diagnostics

A read-only host observer starts/stops the aggregate profiler at the phase 3
state cuts without debugger stops inside a scene. At the existing c2p entry
`E:32028` (file `32054`) it compares all 320 × height chunky bytes against the
previous same-size call within that scene, recording changed bytes and 32-byte
blocks. Heights are restricted to 128, 166 or 200; a scene's first call is not a
comparison. This is a proposed change-rate instrument awaiting independent
validation, not a choice of full-frame or delta conversion.

Fresh default and `NoCache` runs both complete the entire credits cycle and reach
the menu, with live CACR matching their separate audits. All 34 scene profiles
reconcile their PC/context unit sums and boundary clocks, with zero residual and
zero high-address cost. Nevertheless, the default run reports 43,154 unmatched
RTS/RTR/RTD returns and 10,455 unmatched RTE returns; `NoCache` reports 44,510 and
10,561 respectively. Until their cause and attribution are validated, neither
inclusive nor context-based self routine costs are accepted. Between-instruction
cost is not automatically idle or interrupt cost.

The default diagnostic has 1,697 publications over 178.891181 emulated seconds,
versus phase 3's 1,696 over 178.771040. The capture protocols differ; this has not
passed a matched observer-off comparison or a repeat check. It must not be treated
as an improvement or a trusted baseline. NoCache diagnostics are likewise
unaccepted. Raw data and reports are retained in
`tmp/phase4-profile-020-{default,nocache}/`, with `validated_baseline=false` in the
report. Local profiler SHA-256:
`9123cf986fe75e2a8f45beacf1f8b67d4b554a00a7076aeec1185f8ea32b3f94`.

The independent five-field 020 slice provides nonempty instruction and DMA
records. `matrix_trace.py` rejects the uncovered accelerated traces. Its DMA
fractions describe that slice only, not whole-scene idle time or CPU utilisation.
Parser negative controls reject a missing scene, wrong CACR, invalid change count
and wrong CPU clock (`tmp/phase4-negative-checked/`). These structural checks do not resolve
the instrument-accuracy issues above.

### Profiler address-accounting correction

The shared aggregate profiler calls `aprof_after(r->instruction_pc, r->opcode)`
after executing an instruction. The emulator's `m68k_setpc` changes
`instruction_pc` during control transfers, so a return can be charged to its
**destination** instead of its executing address. This makes the original
per-PC profile unsuitable for exact source-range costs even when total units
reconcile. The local builder now snapshots PC/opcode before execution with
`--aprof-stable-pc`; `--matrix-observer` includes this correction automatically.
It does not change the emulated instruction or the Barto trace hook.

Two separate original-slave 020 boots, with the unmatched-return diagnostic
logger enabled in both, provide a five-field before/after check. All 427,130
instruction PC/cost/register records, field cycle/idle totals, screenshots, AGA
colours and the trace's ROM/chip snapshots match. The corrected aggregate covers
all 3,829 instruction PCs and their cycle costs in the enclosed trace; the old
aggregate undercovers 145 count PCs and 146 cost PCs. Its additional edge
instructions are outside the five-field trace, so this is a lower-bound coverage
check, not exact equality of the two differently bounded windows. Total aggregate
accounting remains exact, with zero residual.

Full raw trace identity **does not** pass: the five fields have 18 differing DMA
bytes and 10 differing custom-register snapshot bytes, all observed differences
in the pending INTREQ bit `0800`. Instruction execution and slot ownership in
this slice are unchanged; the cause of that pending-bit difference has not been
established. It is retained rather than masked by the checker.

The corrected aggregate still has 21 unmatched RTS/RTR/RTD and two unmatched RTE
returns. The log identifies nonstandard system transfers and a concrete slave
case: `S:05b4` (file `05d4`) advances the stacked return address by four before
`S:05b6` returns. Exact saved-return-address matching cannot recognise that call's
return. A PC correction alone does not repair calling contexts, and all earlier
whole-scene diagnostics remain unaccepted.

Evidence: `tmp/phase4-return-probe/`, `tmp/phase4-stablepc-probe/`,
`tmp/phase4-stablepc-check.json` and `tmp/phase4-stablepc-negative.json`.
The corrected diagnostic emulator SHA-256 is
`e5434cfd84f60d5497687102226e6ee01477ae676e22730ee4093101f525a044`.
The old profile is a negative control and must fail the coverage check.

### Saved-slot return diagnostic

`--aprof-stack-returns` additionally records the stack slot where each JSR/BSR
saved its return address. An ordinary RTS/RTD/RTR consuming that same slot can
return from the call even if the saved address was modified. Hardware exception
frames are excluded from this additional rule. The stable executing-PC correction
is required and included by this option.

In the same five-field 020 window, an independent trace check observes five calls
to `S:0596`, each returning at `S:05b6` through the original saved stack slot to
four bytes beyond the JSR's normal successor. The diagnostic recognises exactly
five adjusted returns; unmatched ordinary returns fall from 21 to 16. Both
unmatched RTEs remain. All 427,130 instruction PC/cost/register records, field
cycles, screenshots and captured ROM/chip memory still match the control. The
previously observed INTREQ snapshot differences remain visible. Total units,
gap, chip costs and zero residual are unchanged.

This validates the observed modified-return case only. The remaining trace also
shows interrupt forwarding via a manually stacked RTS destination, software-created
RTE frames, and an RTE switching to a different stack. Those transfers need
separate context handling; the five recovered returns do not certify general
inclusive/self routine attribution. The option remains experimental and is not
automatically enabled in scene captures.

Evidence: `tmp/phase4-stack-probe/` and `tmp/phase4-stack-check.json`.
The diagnostic emulator SHA-256 is
`4dae329f0844f4a00f882f77232a39f1573d27e323c28a067646cd085321c2b6`.

### Independent chunky-census sample

A separate original-slave boot stops at each of the first six c2p entries in
Origin animation (`E:32028`, file `32054`). GDB independently reads D0/D3/A0 and
dumps the full 40,960-byte source before the host observer sees that call. The
observer then runs normally. Python compares the saved buffers byte for byte and
by 32-byte block, without using the observer's change counts as inputs.

| Source sample | Changed bytes | Changed 32-byte blocks |
|---|---:|---:|
| First (unpaired) | not compared | not compared |
| 1 | 614 | 202 |
| 2 | 588 | 205 |
| 3 | 9 | 8 |
| 4 | 655 | 176 |
| 5 | 770 | 212 |

All six observer records agree with the independent snapshots, including the
unpaired first sample. A deliberately changed byte in sample 1 is rejected.
This verifies the sampled 320×128 census only; it does not yet validate 166/200-line
inputs, every scene, or a full-frame-versus-delta design choice. The oracle run
contains debugger stops and is not an accepted timing baseline.

Evidence: `tmp/phase4-census-oracle/`, `tmp/phase4-census-check.json` and
`tmp/phase4-census-negative/`. All raw source buffers remain in `tmp/`.

### Whole-route chunky census and recording neutrality

The corrected-PC 020 observer now optionally retains every source buffer after
reading it. A separate Python implementation recomputes byte and 32-byte-block
changes from that stream, resetting comparisons at scene and geometry changes.
All **1,677 calls**, **1,645 comparable pairs** and **68,759,040 source bytes** agree
with the native census. Calls occur in 31 scenes; the recorded geometries are
320×128 and 320×200. No 166-line input occurs in this route. The first six Origin
source buffers also match the independently acquired GDB snapshots byte for byte.
A changed raw byte is rejected at its first affected comparison.

A fresh matched control uses the same local emulator, original slave, stock 020
clock, `CUSTOM5=0`, PAL and CACR `00000001`, with raw recording disabled. All
**3,409 B/P/C ledger records**, **34 complete aggregate profile files**, final
allocated game-hunk bytes and menu RGB pixels match exactly. A deliberately
changed profile instruction count fails the comparison. This establishes repeat
agreement and the neutrality of the **additional raw recording** on this route;
it is not an aggregate-profiler-off test and does not validate the remaining
calling-context errors. The two runs each observe 1,697 publications over
178.891181 emulated seconds, including loading and holds. Their agreement does
not remove the separately recorded difference from the phase 3 capture protocol.

Percentages below use only same-size, consecutive source pairs within a scene.
Unpaired first calls and geometry changes are excluded, not counted as zero
change. Block percentage is the fraction of compared 32-byte source blocks with
at least one changed byte. These measurements do not include palette changes,
conversion cost, or a recommendation for delta c2p.

| Scene | c2p calls | Pairs | Changed bytes % | Changed blocks % |
|---|---:|---:|---:|---:|
| origin-load | 1 | 0 | — | — |
| origin-reveal | 1 | 0 | — | — |
| origin-animation | 30 | 29 | 0.771 | 9.246 |
| origin-expression | 21 | 20 | 0.445 | 3.543 |
| origin-separation | 17 | 16 | 9.267 | 30.098 |
| origin-flight | 42 | 41 | 13.160 | 26.265 |
| origin-particles | 100 | 99 | 2.783 | 13.404 |
| origin-fade | 2 | 1 | 0.000 | 0.000 |
| title-load | 1 | 0 | — | — |
| title-animation | 67 | 66 | 6.041 | 13.640 |
| title-arrival | 50 | 49 | 2.546 | 4.904 |
| title-departure | 31 | 30 | 7.640 | 15.365 |
| credits-00 | 81 | 80 | 1.659 | 5.798 |
| credits-01 | 74 | 73 | 2.893 | 7.276 |
| credits-02 | 75 | 74 | 1.039 | 4.298 |
| credits-03 | 74 | 73 | 1.051 | 3.924 |
| credits-04 | 73 | 72 | 1.062 | 4.332 |
| credits-05 | 73 | 72 | 1.683 | 6.367 |
| credits-06 | 72 | 71 | 1.916 | 6.306 |
| credits-07 | 72 | 71 | 1.916 | 6.773 |
| credits-08 | 71 | 70 | 3.567 | 8.790 |
| credits-09 | 71 | 70 | 1.033 | 4.075 |
| credits-10 | 69 | 68 | 1.823 | 5.958 |
| credits-11 | 73 | 72 | 2.081 | 6.377 |
| credits-12 | 69 | 68 | 1.538 | 6.018 |
| credits-13 | 71 | 70 | 1.570 | 5.631 |
| credits-14 | 72 | 71 | 1.588 | 6.005 |
| credits-15 | 73 | 72 | 1.802 | 6.870 |
| credits-16 | 72 | 71 | 1.766 | 6.199 |
| credits-17 | 75 | 74 | 0.896 | 3.806 |
| cycle-complete | 4 | 2 | 6.763 | 7.600 |

The cycle-complete row contains one 128-line and three 200-line calls; its two
comparisons are between the 200-line sources. Other rows contain 128-line calls.
Evidence: `tmp/phase4-raw-census/`, `tmp/phase4-raw-control/`,
`tmp/phase4-raw-comparison.json`, `tmp/phase4-raw-negative/` and
`tmp/phase4-raw-profile-negative/`. Local emulator SHA-256:
`bfef8b4d91f0a68eabff32e8a16e21d80f21b67fa75bfa4a2da94d4014c34237`.
The full CPU/cache matrix, caller attribution and ceiling experiments still have
not passed the phase 4 gate.

### Aggregate-profiler on/off controls

Two isolated comparisons now pass on the original 020 route. The default-cache
pair disables raw recording in both arms; the NoCache pair enables it in both.
Only aggregate profiling changes within each pair, using the same local emulator.

| Cache state | CACR | Identical B/P/C records | Final game hunks / menu pixels | Raw sources |
|---|---|---:|---|---|
| Default | `00000001` | 3,409 | exact / exact | disabled in both arms |
| `NoCache` | `00000000` | 2,885 | exact / exact | every byte identical |

The disabled controls contain no aggregate profile files. This establishes the
aggregate profiler's neutrality for scene progression, clocks and the compared
state/picture under both effective 020 cache states. It does **not** repair the
calling-context attribution. The earlier comparison that disabled both profiling
and raw recording is retained as a combined control, not mislabelled as an isolated
profiler test. The comparison tool records exactly which features changed.

Default evidence: `tmp/phase4-profile-on-no-raw/`, `tmp/phase4-profile-off/` and
`tmp/phase4-profiler-isolated-check.json`. NoCache evidence:
`tmp/phase4-nocache-on/`, `tmp/phase4-nocache-off/` and
`tmp/phase4-nocache-profiler-check.json`. Both use local emulator SHA-256
`95329265de9f948787a6494fd8029d3e3516113b315f14dd586c00b37764494f`.
The NoCache source census independently recomputes every recorded change, just as
the default census does. Its buffers are compared with its own matching control;
no equality between different cache-state trajectories is assumed.

### Verified 020 converter and limiter instruction costs

The four routines below contain no subroutine calls or jumps out of their own
ranges; every decoded branch stays inside its range and the final instruction is
RTS. The original slave digest is checked, and all four live ranges still match
the original bytes in the menu snapshot. This permits direct instruction-PC
accounting without the unresolved calling-context tree.

| Routine | Slave code range (end exclusive) | Slave file range (end exclusive) |
|---|---|---|
| TOD limiter | `17b8–17ee` | `17d8–180e` |
| 128-line converter | `17f6–195e` | `1816–197e` |
| 166-line converter | `195e–1ac6` | `197e–1ae6` |
| 200-line converter | `1ac6–1c2e` | `1ae6–1c4e` |

For every scene after game entry, each converter's entry count equals the
independent census count for its height, and limiter entries equal all converter
calls. The 166-line entry is never observed in this intro route. An uncorrected-PC
profile is rejected. Default-cache leaf reports reproduce exactly in independent
fresh boots, and isolated aggregate-profiler-off controls pass for both cache states.

**Definition:** costs below sum instruction-body cycle units at the verified PCs,
including memory stalls charged to those instructions. They exclude interrupt
service and between-instruction gaps. The routines have no synchronous callees,
so these are their own instruction costs without a separate callee contribution;
they are not full entry-to-return elapsed times. No general inclusive-call-tree
accuracy is claimed. Percentages use the complete scene duration as denominator.

D/N means default CACR `00000001` / NoCache CACR `00000000` on the calibrated stock
020 emulator. Publication rate includes scene holds and loading; it is not an
instantaneous animation rate. Converter share sums the three height-specific
bodies. Reset/boot is excluded because the future slave address range is not yet
established throughout that interval.

| Scene | Publications/s D / N | Converter instruction % D / N | Limiter instruction % D / N |
|---|---:|---:|---:|
| game-startup | 2.750 / 1.878 | 0.000 / 0.000 | 0.000 / 0.000 |
| origin-load | 6.447 / 4.474 | 5.098 / 3.561 | 0.002 / 0.001 |
| origin-reveal | 0.835 / 0.688 | 3.312 / 2.743 | 0.001 / 0.001 |
| origin-animation | 11.228 / 7.807 | 44.480 / 31.103 | 0.017 / 0.012 |
| origin-expression | 3.962 / 3.978 | 15.691 / 15.845 | 0.006 / 0.006 |
| origin-separation | 11.884 / 8.384 | 47.080 / 33.404 | 0.018 / 0.013 |
| origin-flight | 4.147 / 4.407 | 16.420 / 17.558 | 0.006 / 0.006 |
| origin-particles | 15.506 / 12.973 | 61.409 / 51.680 | 0.023 / 0.020 |
| origin-fade | 1.324 / 1.323 | 1.746 / 1.756 | 0.001 / 0.001 |
| title-load | 2.519 / 1.486 | 1.996 / 1.183 | 0.001 / 0.000 |
| title-animation | 10.900 / 9.306 | 43.159 / 37.056 | 0.015 / 0.013 |
| title-arrival | 11.099 / 8.384 | 43.959 / 33.401 | 0.015 / 0.012 |
| title-departure | 10.266 / 8.696 | 40.675 / 34.651 | 0.014 / 0.012 |
| credits-load | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| credits-00 | 12.563 / 10.661 | 49.741 / 42.468 | 0.017 / 0.015 |
| credits-01 | 11.487 / 9.365 | 45.490 / 37.303 | 0.015 / 0.013 |
| credits-02 | 11.693 / 9.110 | 46.302 / 36.291 | 0.016 / 0.013 |
| credits-03 | 11.438 / 9.073 | 45.311 / 36.147 | 0.015 / 0.013 |
| credits-04 | 11.375 / 9.220 | 45.050 / 36.724 | 0.015 / 0.013 |
| credits-05 | 11.342 / 8.953 | 44.911 / 35.672 | 0.015 / 0.012 |
| credits-06 | 11.094 / 9.118 | 43.931 / 36.327 | 0.015 / 0.013 |
| credits-07 | 11.103 / 9.406 | 43.979 / 37.474 | 0.015 / 0.013 |
| credits-08 | 11.020 / 9.135 | 43.643 / 36.393 | 0.015 / 0.013 |
| credits-09 | 11.068 / 8.682 | 43.818 / 34.582 | 0.015 / 0.012 |
| credits-10 | 10.702 / 8.809 | 42.386 / 35.083 | 0.014 / 0.012 |
| credits-11 | 11.303 / 9.634 | 44.755 / 38.365 | 0.015 / 0.013 |
| credits-12 | 10.689 / 9.041 | 42.331 / 36.006 | 0.014 / 0.012 |
| credits-13 | 11.044 / 8.550 | 43.741 / 34.051 | 0.015 / 0.012 |
| credits-14 | 11.234 / 9.135 | 44.481 / 36.396 | 0.015 / 0.013 |
| credits-15 | 11.250 / 9.631 | 44.564 / 38.369 | 0.015 / 0.013 |
| credits-16 | 11.150 / 9.105 | 44.154 / 36.272 | 0.015 / 0.013 |
| credits-17 | 11.666 / 9.507 | 46.210 / 37.875 | 0.016 / 0.013 |
| cycle-complete | 7.995 / 6.400 | 22.776 / 18.296 | 0.006 / 0.005 |

On these two 020 runs the limiter's instruction cost stays below 0.024% of each
scene. This is a measured cost in these configurations, not a statement of the
intended game rate or a prediction for faster CPUs. The default converter occupies
44.480% of Origin animation and 61.409% of the particle scene. No rendering patch
or performance improvement is claimed.

Evidence: `tmp/phase4-leaf-costs.json`,
`tmp/phase4-profile-on-no-raw/leaf-costs.json`,
`tmp/phase4-nocache-on/leaf-costs.json` and `tmp/phase4-leaf-negative.json`.
The unresolved remainder includes other instructions, exception/idle gaps and
unvalidated general caller attribution. These leaf measurements do not fill the
other CPU matrix cells or substitute for the ceiling experiments.

### Idle-field interpretation

The pinned Barto `Field.idle` comes from explicit `barto_cmd_set_idle` application
markers in `debug.cpp`; it is not an automatic measurement of CPU STOP or scheduler
idle. The unmodified-game slice has zero such marker units, which must not be
reported as zero CPU idle. A missing instruction PC is likewise labelled
`no-recorded-PC`, not automatically STOP. `matrix_trace.py` explicitly reports
`cpu_idle_measured: false`. Between-instruction cycles remain unclassified until
an appropriate idle/interrupt instrument accounts for them.

The debug record layout and idle-marker implementation, plus the custom-chip
recording source, are now pinned in `manifest/debugger.tsv` alongside the existing
CPU/debugger source inputs. They remain shared read-only build inputs.

### Deferred gaps after practical-baseline closeout

- General routine self/inclusive attribution remains invalid around system
  returns and task/interrupt stack transitions. Verified leaf instruction costs
  do not depend on that call tree.
- Complete interrupt entry/dispatch, other handlers and blitter-wait attribution
  are unavailable. Three VBL callback scopes and STOP idle have narrower meanings.
- 030 NoMMU default's beam diagnostic differs from its uninterrupted control.
  060 default/NoCache fail exact callback-recorder neutrality; their scene-level
  rates and final state agree, with the local differences quantified below.
  Those callback results are not silently promoted to accepted measurements.
- The drawing ceiling covers TM6 bitmap drawing only. Blanket clear bypass is
  invalid because later work reads its pixels. A broader ceiling needs preserved
  data dependencies.
- Accelerated timings are emulator-model measurements, not physical accelerator
  validation. Intended game speed, timing coupling and cockpit evidence belong
  to later phases; no rendering improvement has yet been delivered.

These gaps are accepted deferrals under the user-approved practical scope.
Revisit them only when needed for a subsequently authorised engineering decision.

### Practical-baseline gate audit

The initial accelerated preflights tested the shared presets' MMU cores, not the
NOMMU timing configurations required by the plan. WHDLoad `NoMMU` does not select
an emulator core. Hard Drivin' and Red Baron explicitly use `68040-NOMMU` and
`68060-NOMMU` with cycle-exact settings for timing, and separate MMU functional
runs. Hard Drivin' retains accelerated frame counts and ceiling experiments while
marking unsupported instruction costs unavailable. Thus the initial missing
instruction records do not justify blocking all accelerated measurement work.

`WC_NOMMU_CORE=1` now replaces the project launcher's preset CPU/MMU/exact settings
in place: `68EC030`, `68040-NOMMU` or `68060-NOMMU`, MMU model zero and CPU/memory/
blitter exact requested. It leaves shared presets untouched. This selects an
instrumentation path; it does not validate the requested MHz, guarantee that all
exact settings survive emulator fixups, or replace the WHDLoad-MMU matrix cell.
Corrected probes must read back the effective settings. The numeric-frequency
issue and each instrument's coverage still require explicit checks.

| Approved requirement | Evidence and disposition |
|---|---|
| CPU/cache matrix and VERIFY audits | All eleven corrected cells have complete captures, matching CACR/configuration/debugger audits and effective-state readback. Numeric scaling is calibrated to the stock 020 reference. Pass for the emulator model. |
| Per-scene baseline and source-change census | All eleven bare captures parse into 34 intervals; each cell's bare/idle/DMA raw-source recomputation passes. Scene figures and commands are recorded below. Pass. |
| Validated representative costs, DMA and idle | Verified 020/030 leaf costs identify software c2p; all eleven cells pass DMA accounting, independent menu histograms and exact recording controls, plus STOP accounting and exact idle controls. Eight pass consolidated callback checks. Pass with the deferred coverage limits above. |
| Controlled ceilings on the nominal fastest cell | 030 MMU/default has matched c2p, instant-blitter and scoped bitmap-drawing comparisons, fixture/readback checks and repeated controls. Blanket clear bypass is rejected. Pass for the approved scoped experiments. |
| Findings and reproducibility | Findings, code-hunk/file offsets and limitations are in this document; commands are in `development.md`. Derived material remains in ignored `tmp/`; changes are committed in coherent steps. Pass. |
| Phase boundary | All acquisition jobs are terminal. No phase 5 or release rendering work has started. Stop at this gate. |

Closeout verification inspected the eleven corrected cells' capture/audit
metadata, reparsed their scene ledgers and checked their retained raw-census,
DMA and idle results. It also inspected the c2p/instant/bitmap comparison reports
and consolidated callback reports. No new emulator run was needed. Completion
is for this approved practical baseline, not the superseded exhaustive accounting
gate. Detailed evidence and failure reports remain available below.

### Prepared c2p ceiling fixtures

The VERIFY-only equal-size `reconstruct.py --variant cd32 --ceiling` fixtures are built and
byte-checked; the matched c2p runtime result is recorded below. The control is
byte-identical to the original 7,728-byte slave. The c2p arm changes only the first
word of the three leaf converter entries to `RTS`: `S:17f6/195e/1ac6` (file
`1816/197e/1ae6`). The wrapper at `S:178a` still saves/restores registers, runs
the existing TOD limiter and returns to the normal publication path. The arm
intentionally omits planar conversion; visual equivalence is not expected.

Both size and all bytes outside those three words are checked during the build.
The c2p-arm digest is
`ec089eabbc6b869d3ec96fcc54a110d94e2fb3c362fe980ee1965b4f2f52ec53`.
Fixtures and generated assembly are under `tmp/phase4-ceiling-{control,c2p}-slave/`.
The selected comparison cell and accepted c2p result are recorded below. The instant-blitter and scoped bitmap-drawing pairs also pass. Blanket clear bypass fails and is excluded.

### Corrected-clock NOMMU scene figures

These are original-slave, `Custom5=0` counter measurements on the corrected
numeric-clock model. Frequencies are requested values with the quantisation
listed above; they are not predictions for physical accelerators. Each cell has
a separate cache audit and a completed ledger check. The 030 default also has
an isolated profiler-neutrality check. Repetition of the other corrected cells
and the MMU pair remain separate checks.

Values are publications per emulated second. Reset/loading has no published game
frames and is omitted. Reports retain counts, elapsed units and change census.

| Scene | 030 default | 030 NoCache | 040 default | 040 DCache | 060 default | 060 DCache | 060 NoCache |
|---|---:|---:|---:|---:|---:|---:|---:|
| game-startup | 4.345 | 3.745 | 4.016 | 4.015 | 4.048 | 4.048 | 4.048 |
| origin-load | 9.595 | 8.325 | 9.027 | 9.028 | 9.229 | 9.229 | 9.229 |
| origin-reveal | 1.158 | 1.157 | 1.136 | 1.136 | 1.136 | 1.136 | 1.136 |
| origin-animation | 25.159 | 25.004 | 25.133 | 25.133 | 25.133 | 25.133 | 25.133 |
| origin-expression | 3.953 | 3.967 | 3.955 | 3.955 | 3.955 | 3.955 | 3.955 |
| origin-separation | 25.886 | 25.165 | 25.770 | 25.770 | 25.770 | 25.770 | 25.770 |
| origin-flight | 3.853 | 3.860 | 3.854 | 3.854 | 3.854 | 3.854 | 3.854 |
| origin-particles | 25.060 | 25.065 | 25.049 | 25.049 | 25.049 | 25.049 | 25.049 |
| origin-fade | 1.736 | 1.734 | 1.737 | 1.737 | 1.738 | 1.738 | 1.738 |
| title-load | 5.398 | 4.002 | 4.515 | 4.515 | 4.519 | 4.519 | 4.519 |
| title-animation | 25.053 | 25.108 | 25.034 | 25.034 | 25.028 | 25.028 | 25.028 |
| title-arrival | 24.969 | 24.426 | 24.103 | 24.103 | 24.202 | 24.202 | 24.202 |
| title-departure | 24.281 | 24.010 | 24.497 | 24.496 | 24.327 | 24.327 | 24.327 |
| credits-load | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| credits-00 | 25.065 | 25.073 | 25.077 | 25.077 | 25.077 | 25.077 | 25.077 |
| credits-01 | 24.960 | 24.959 | 24.958 | 24.958 | 24.958 | 24.958 | 24.958 |
| credits-02 | 24.962 | 24.961 | 24.963 | 24.963 | 24.962 | 24.962 | 24.962 |
| credits-03 | 24.959 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 |
| credits-04 | 24.960 | 24.959 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 |
| credits-05 | 24.962 | 24.961 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 |
| credits-06 | 24.959 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 |
| credits-07 | 24.960 | 24.959 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 |
| credits-08 | 24.962 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 |
| credits-09 | 24.959 | 24.962 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 |
| credits-10 | 24.961 | 24.959 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 |
| credits-11 | 24.960 | 24.961 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 |
| credits-12 | 24.959 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 |
| credits-13 | 24.961 | 24.959 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 |
| credits-14 | 24.960 | 24.961 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 |
| credits-15 | 24.959 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 |
| credits-16 | 24.961 | 24.959 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 |
| credits-17 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 | 24.960 |
| cycle-complete | 13.096 | 12.310 | 12.253 | 12.253 | 12.254 | 12.254 | 12.254 |

Evidence: `tmp/phase4-frequency-scenes-CELL/scene-report.json`, where CELL is
`030`, `030-nocache`, `040`, `040-dcache`, `060`, `060-dcache` or `060-nocache`.
All seven runs publish 3,362 frames over the reset-to-menu window. This does not
establish equal per-instruction performance. Corrected readbacks are unit 36 for
030/060 and unit 72 for 040. Live CACR is respectively `$00002111`, `$00002000`,
`$00000000`, `$80008000`, `$20800000`, `$a0808000` and `$00000000`.
Additional corrected-core audits confirm 030 `DCache` has the default `$00002111`
and 040 `NoCache` has the default `$00000000`; no separate timing improvement is
inferred from those option names.

### DMA instrumentation check

`--matrix-dma` records completed DMA fields and assigns slots to the current
scene at the slot's left boundary. It keeps only counts in `dma-events.txt`;
full derived records stay in the separate Barto validation capture. The first
030 run in `tmp/phase4-dma-on-030/` records 8,221 complete fields. Its final
field histogram agrees exactly with the independently parsed full `menu.bin`
trace. Scene coverage after reset differs from the PC-clock interval by at most
432 units, below one 512-unit DMA slot. Negative fixtures reject an incorrect
field total, missing scene coverage and an altered histogram.

The local recorder binary is
`7e4388b891d7d9973e4c8f7a7b7958c6a49811d8bab7e8fc53ca999ddf59715b`.
A same-binary recording-off control in `tmp/phase4-dma-off-030/` shows that enabling
DMA recording is **not exactly timing-neutral**. All 6,739 records agree after
removing cycle timestamps, including field numbers, publications and source-change
counts. Final game hunks and menu pixels are identical. The largest absolute
scene-duration change is 82.568 microseconds. The exact comparator correctly
rejects the pair; the quantified effect is retained in
`tmp/phase4-dma-effect-030.json`.

DMA shares therefore describe the explicitly instrumented run, while CPU timing
continues to use recording-off captures. They are bus-slot shares, not CPU-time
shares. Unclaimed slots do not measure CPU idle. The hardware blitter appears in
reset/loading (142,597 recorded slots) and has no recorded slots after game startup
in this `Custom5=0` run; this does not cover the original blitter converter option.
DMA results for other matrix cells are still outstanding.

### 030 MMU counter path and paired scene captures

`--matrix-mmu030-counters` adds the same read-only scene observer to the 030 MMU
interpreter before its internal instruction-retry label. Internal MMU retries do
not create duplicate observer entries. The debugger audit now reports `tc030`,
so configured MMU capability can be distinguished from enabled translation.
The local build succeeds with digest
`c2fb09ab6f3d5dbb2102ff6f3df5ce1b458792f22f55a05172f057defdfba4a6`.
Counter capture requires explicit `--mmu-core --no-profiles`; it does not claim
instruction-profiler support. The `MMU` capture in `tmp/phase4-mmu-scenes-030/` completes and passes the scene
ledger check. Its actual translation control is `$80c07760` (enabled), with CACR
`$00002111` and unit 36. The checker now requires the TC enable bit to agree with
an explicit `MMU`/`NoMMU` option. The same-interpreter `NoMMU` control also completes with TC zero. Both NoCache
variants complete with CACR `$00002000`; the MMU option still controls TC as
requested. Their scene ledgers pass. These rows remain separate from the
NOMMU-interpreter figures to avoid attributing a core implementation difference
to the WHDLoad option.

| Scene | MMU default | NoMMU default | MMU NoCache | NoMMU NoCache |
|---|---:|---:|---:|---:|
| game-startup | 4.835 | 4.848 | 3.878 | 3.871 |
| origin-load | 10.465 | 10.462 | 8.969 | 8.965 |
| origin-reveal | 1.176 | 1.176 | 1.153 | 1.153 |
| origin-animation | 25.217 | 25.217 | 25.193 | 25.193 |
| origin-expression | 3.963 | 3.963 | 3.950 | 3.950 |
| origin-separation | 26.147 | 26.148 | 26.050 | 26.049 |
| origin-flight | 3.850 | 3.850 | 3.851 | 3.851 |
| origin-particles | 25.091 | 25.091 | 25.078 | 25.078 |
| origin-fade | 1.733 | 1.733 | 1.732 | 1.732 |
| title-load | 6.699 | 6.700 | 4.325 | 4.326 |
| title-animation | 25.326 | 25.322 | 25.213 | 25.209 |
| title-arrival | 24.965 | 24.965 | 24.967 | 24.967 |
| title-departure | 25.014 | 25.014 | 24.655 | 24.655 |
| credits-load | 0.000 | 0.000 | 0.000 | 0.000 |
| credits-00 | 25.111 | 25.110 | 25.097 | 25.096 |
| credits-01 | 24.960 | 24.960 | 24.959 | 24.959 |
| credits-02 | 24.960 | 24.960 | 24.962 | 24.962 |
| credits-03 | 24.960 | 24.960 | 24.960 | 24.960 |
| credits-04 | 24.960 | 24.960 | 24.958 | 24.958 |
| credits-05 | 24.960 | 24.960 | 24.962 | 24.962 |
| credits-06 | 24.960 | 24.960 | 24.960 | 24.960 |
| credits-07 | 24.960 | 24.960 | 24.958 | 24.958 |
| credits-08 | 24.960 | 24.960 | 24.962 | 24.962 |
| credits-09 | 24.960 | 24.960 | 24.960 | 24.960 |
| credits-10 | 24.958 | 24.958 | 24.960 | 24.960 |
| credits-11 | 24.963 | 24.963 | 24.960 | 24.960 |
| credits-12 | 24.958 | 24.958 | 24.960 | 24.960 |
| credits-13 | 24.960 | 24.960 | 24.960 | 24.960 |
| credits-14 | 24.960 | 24.960 | 24.960 | 24.960 |
| credits-15 | 24.963 | 24.963 | 24.960 | 24.960 |
| credits-16 | 24.958 | 24.958 | 24.960 | 24.960 |
| credits-17 | 24.960 | 24.960 | 24.960 | 24.960 |
| cycle-complete | 14.122 | 14.122 | 12.748 | 12.748 |

Values are publications per emulated second. Evidence is in
`tmp/phase4-{mmu,mmu-off,mmu-nocache,mmu-off-nocache}-scenes-030/`.
The byte-identical ceiling control on the same-core NoMMU/default cell repeats
all 6,741 ledger records, final game hunks and menu pixels exactly;
`tmp/phase4-ceiling-repeat-check-030.json` records the pass.

### Ceiling comparison cell

The declared ranking window is `origin-load` entry through `cycle-complete`
entry: one complete intro, excluding reset and the second-cycle/menu exit.
`tmp/phase4-ceiling-cell-ranking.json` covers all measured CPU/cache cells.
The 030 MMU/default cell records 3,351 publications over 152.658730 emulated
seconds (21.950923/s). Same-core NoMMU/default records the same count over
152.658910 seconds (21.950897/s). This 180-microsecond difference over the entire
intro is not evidence of a meaningful physical accelerator advantage; the two
are effectively tied. The nominally fastest MMU/default cell is selected for the
matched ceiling experiments. The equal-size control repeats all 6,741 ledger records, final game hunks and
menu pixels of the matrix capture exactly. The matched c2p-bypass run completes
with the same 3,351 publications over 152.649027 seconds (21.952318/s), saving
0.009703 seconds across the declared window: a rate ratio of 1.00006356.

The retained boot fixtures differ only at the three declared converter entry
words, and all six control/bypass entry words agree with the final live memory
captures. The bypass replaces code-hunk offsets `$17f6`, `$195e`, `$1ac6`
(file offsets `$1816`, `$197e`, `$1ae6`) with `RTS`. The original limiter and
publication path remain active; this small measured gain is not the converter's
CPU cost. Planar output is intentionally invalid in this ceiling arm. This is
one matched pair, not a variability estimate or a physical accelerator claim.

`tmp/phase4-ceiling-c2p-comparison.json` records every scene and the complete
window; `tmp/phase4-ceiling-repeat-check-030-mmu.json` records the control repeat.
The checker rejects reversed arms and mismatched emulator builds. The instant-blitter and scoped bitmap-drawing results follow.


### Instant-blitter ceiling result

The selected 030 MMU/default cell uses the same original-byte control slave for
both arms. The local debugger digest is
`0984e6365a6bebe9c9d0909e2c8d10216516cf0404896959a75bd88515bf2951`.
Its fresh VERIFY audit records CACR `$00002111`. At both boot and menu,
`wc-audit` confirms `immediate_blits=0` in the control and `1` in the intervention;
CPU/memory/blitter exact settings, unit 36 and MMU configuration otherwise match.
Live translation control is `$80c07760` in both arms.

| Complete intro window | Publications | Emulated seconds | Publications/s |
|---|---:|---:|---:|
| Matched control | 3,351 | 152.658729642 | 21.950922871 |
| Instant blitter | 3,351 | 152.658722312 | 21.950923925 |

The full-window difference is 7.330 microseconds; the largest absolute individual
scene difference is 47.083 microseconds. This is no meaningful measured
whole-intro benefit for `Custom5=0`; it is not a claim about the unmeasured
`Custom5=4` blitter converter. The existing limiter remains active. Final allocated
game hunks and menu pixels match in both arms. The new control also repeats the
prior control's complete ledger, final game hunks and menu pixels exactly.

Evidence is in `tmp/phase4-instant-{control,on}-030-mmu/`,
`tmp/phase4-instant-comparison.json` and `tmp/phase4-instant-state-check.json`.
The ceiling checker validates retained binary identity, placement, scene ledgers
and effective settings; a negative fixture with the instant flag claimed but
readback disabled is rejected. These two completed ceiling comparisons do not
close the broader drawing or full-matrix accounting gaps.


### Bitmap-drawing ceiling and unsafe clear bypass

The TM6 bitmap drawing entry is English code-hunk 0 offset `$2efe8` (file
`$2f014`). It validates TM6 image data, clips the requested rectangle and writes
pixels into the destination surface. It is used by the Origin sequence and the
credits text renderer (the latter calls it from `E:13ff0`). The surface-clear
entry is `E:31cd6` (file `$31d02`). These are distinct drawing operations.

The accepted drawing comparison bypasses **TM6 bitmap drawing only**, retaining
surface clearing, other drawing/projection, c2p, the limiter and publication.
Both 7,836-byte VERIFY fixtures use the same PatchSeg detour at `S:14da`
(file `$14fa`), preserve registers/CCR, install their entry words, and flush the
CPU cache before returning. They differ only in the bitmap patch word at slave
code-hunk offset `$1e74` (file `$1e94`). The control retains both MOVEM entries;
the bitmap arm uses RTS at `E:2efe8`. An installation counter at `S:1e70`
(file `$1e90`) reads one in both completed captures, and all live entry words
match their intended arms. No release slave is produced.

| Selected 030 MMU/default cell | Publications | Complete intro seconds | Publications/s |
|---|---:|---:|---:|
| Equal-size drawing control | 3,351 | 152.658729642 | 21.950922871 |
| Bitmap drawing bypass | 3,351 | 152.658729642 | 21.950922871 |

All per-scene publication counts match. The largest absolute scene-duration
change is 103.083 microseconds; the complete-window difference is zero.
Origin animation and particle source-change counts drop to zero in the bypass,
and menu pixels differ, confirming an effective rendering intervention. This
is a measured zero whole-window gain with the original limiter active, not a
zero bitmap-drawing CPU cost. The new control's complete-intro scene rows,
including census counts, match the prior original-byte control exactly.

Evidence: `tmp/phase4-drawing-v2-control-030-mmu/`,
`tmp/phase4-drawing-bitmap-030-mmu/` and
`tmp/phase4-drawing-bitmap-comparison.json`. Fixture digests are
`0825f64aa762ad77aff01682c20a2eeb73e816d73cfa0c6f46c1b4e5e3631138`
(control) and
`c182473a52bccafc275547163ffe063466076eab3713ec3e25559e39b200321a`
(bitmap). Emulator and cache audit are the same as the instant-blitter pair.
The checker rejects a negative memory fixture in which the claimed bitmap
bypass was not installed. Rebuilding the ordinary slave still produces the
pinned original bytes exactly.

A blanket RTS replacement of surface clear is **not a valid ceiling arm**.
The combined and clear-only diagnostics fail during title loading; the bitmap-only
diagnostic reaches credits. A write watchpoint on the clear-only run identifies
`E:2cd00` (file `$2cd2c`) clearing beyond its stack buffer into the game hunk.
The preceding pixel scan stores rectangle bounds at `E:2ccc0`; the failed run's
bounds are `(319,199,0,0)`. Subtracting the vertical bounds produces `$ff39`, so
the DBF loop clears 65,338 bytes instead of a valid small rectangle. The capture
has no completed result and supplies no performance figure. Registers, memory
and the first corrupting write are retained in `tmp/phase4-drawing-watch-clear/`.
This is evidence that drawing data is consumed by later work; broader drawing
bypass requires preserving that dependency, rather than silently accepting a
crashed or shortened window. Full-matrix accounting also remains incomplete.


### STOP-state idle accounting

`--matrix-idle` observes each assignment to the emulator's stopped-CPU state,
including reset and CPU-tracer restore paths. `idle-events.txt` records state
transitions and the exact scene clocks. A separate counter measures elapsed
units inside `do_cycles_stop` only when the CPU was already stopped at entry;
the first invocation belongs to the STOP instruction before the stopped flag
is set. The report integrates transitions independently and retains the gap
between stopped-state duration and that narrower wait-loop counter.

The completed 020 default pair uses local debugger digest
`6b6678b68b153f704f06e798b061189b5cd13b70e3fbd9ac9401da451c0eda21`
and a fresh VERIFY audit with CACR `$00000001`. Recording on/off matches every
one of 3,409 scene/publication/census records, all final allocated game hunks and
menu pixels exactly. Evidence: `tmp/phase4-idle-{on,off}-020/` and
`tmp/phase4-idle-neutrality-020.json`.

| Scene | Stopped seconds | Stopped share | STOP entries |
|---|---:|---:|---:|
| reset/loading | 7.673017 | 63.741% | 1,378 |
| game-startup | 0.372302 | 25.592% | 27 |
| origin-load | 0.304465 | 39.255% | 22 |
| origin-reveal | 0.661638 | 55.277% | 51 |
| origin-fade | 2.750912 | 60.683% | 197 |
| title-load | 0.302045 | 15.214% | 23 |
| second-cycle/menu exit | 0.316669 | 31.648% | 23 |

All other measured scenes have zero stopped-CPU duration. This measures the
emulator's STOP state, not unclaimed DMA slots or busy-wait time. The original
TOD limiter remains executing CPU work. Stopped time outside the narrow wait
call is retained explicitly (for example, 0.009430 seconds in origin-load);
it is not silently discarded or assigned to an interrupt/routine cost.

The prior stable-PC 020 instruction capture has the identical complete ledger.
For every post-startup scene, its game STOP execution count equals the new
state-entry count plus repeated wait-loop calls. The active game instruction is
`E:34074` (file `$340a0`); the second checked STOP is `E:3408e` (file `$340ba`).
The report checks both live opcodes. The independent comparison is in
`tmp/phase4-idle-profile-check-020.json`. Negative fixtures reject duplicate
transitions, missing scene boundaries and impossible wait totals.

The matrix build additionally counts those STOP PCs directly, independently of
the state assignments and wait function, for cores without aggregate instruction
profiles. Its digest is
`9816cb9879d4521a54521ac8de2dd6171b5e4a8870b6c829e2e1e8cc2a86ee6a`.
Its completed 020 default `bare`/`idle` pair passes exact neutrality including
all raw source bytes, and repeats every STOP duration/counter in the table above.
Direct STOP-PC counts agree both with entries plus waits and with the prior
independent instruction profile. The added negative fixture rejects a changed
STOP-PC count. Evidence: `tmp/phase4-idle-v3-neutrality-020.json`,
`tmp/phase4-idle-v3-profile-check-020.json` and
`tmp/phase4-idle-v3-negative-020/`.

The original 11-cell acquisition in `tmp/phase4-accounting-matrix/` is complete.
The corrected batches in `tmp/phase4-dma-cia-matrix/` and
`tmp/phase4-dma-cia-accelerated/` also complete all eleven cells. Each has a fresh
cache audit and separate bare, idle and idle-plus-DMA captures. Every corrected
cell's `idle-neutrality.json` passes exact on/off comparison; `idle-idle.json`
passes STOP-state accounting and STOP instruction-count checks. The idle
measurement requirement is covered for this route, with busy waits explicitly
excluded. General routine and complete interrupt attribution remain open.

### DMA recording neutrality: matrix controls

The completed `020-default`, `020-nocache` and `030-mmu-default` cells in
`tmp/phase4-accounting-matrix/` pass exact bare/idle neutrality, including raw
source bytes. Their DMA arms pass slot-ledger accounting, but this does not
establish neutrality:

| Cell | Largest absolute scene-time change | Publication change | Final game hunks / raw source |
|---|---:|---|---|
| 020 default | 85.272400 ms | credits-15 loses one | differ |
| 020 NoCache | 112.459630 ms | credits-03 gains one; credits-04 loses one | differ |
| 030 MMU default | 0.098114 ms | none | identical |

All three menu images match. The 030 MMU ledger matches after removing only
cycle timestamps; the 020 ledgers do not. The 020 DMA arms are diagnostic
captures, not accepted neutral baseline measurements. Each cell retains
`dma-effect.json`, `dma-report.json` and `idle-neutrality.json`.

The pinned emulator's `cia_cycles` changes its CPU delay calls when `debug_dma`
is enabled: it advances in `CYCLE_UNIT` chunks, while `cia_wait_pre` also splits
synchronisation from access delay. Preserving the DMA-off stepping removes the
recording effect on both tested 020 states. `--dma-cia-unsplit` keeps those calls
identical to DMA-off, omitting intermediate CIA wait-phase annotations while
retaining actual CIA-access annotations and DMA ownership records. The latter
use separate fields in the recorder. This diagnostic does not change game code.

The matched two-cell experiment in `tmp/phase4-dma-cia-matrix/` is complete, using
new cache audits and fresh bare/idle/DMA arms. Its debugger digest is
`5fc6bc292433e60b788b8f14af09613ea2734c2cbc5476c0ac4024dfa474482d`.
Both effective cache states pass exact idle/DMA ledger neutrality, including all
cycle timestamps, raw source bytes, final allocated game hunks and menu pixels.
Every scene has zero duration/publication/field difference. The independent menu
DMA histogram and complete-field accounting pass. Evidence is each cell's
`dma-neutrality.json`, `dma-report.json`, `dma-effect.json` and raw/idle checks.
This accepts the corrected recorder for these 020 cells; it does not validate
routine attribution or prove equivalent behaviour on other CPU cores. The nine
accelerated cells are being checked in `tmp/phase4-dma-cia-accelerated/`.
The completed 030 default pair also passes exact neutrality, raw-source and
independent DMA checks with both WHDLoad MMU enabled and disabled on the same
MMU interpreter. Both fresh audits read CACR `$00002111`; live TC is `$80c07760`
and `$00000000` respectively. Every scene's duration/publication/field difference
is zero, all game hunks and pixels match, and the separate `dma-neutrality.json`
checks pass. Corrected controls also complete for both 030 NoCache states,
both 040 states and all three 060 states: all have exact ledgers, raw sources,
final hunks and menu pixels. All eleven corrected DMA cells are complete, with
complete-field slot accounting and independent menu histograms passing in each.
The final 060 NoCache exact comparison is retained in its `dma-neutrality.json`;
`tmp/phase4-dma-completed-summary.json` collects the eleven completed results.
No missing or failed original-matrix cell is substituted into this summary. The completed original
matrix remains diagnostic evidence of the earlier recorder behaviour.

### Game VBL callback interval validation

The read-only `--matrix-irq` observer brackets the three known game VBL
callbacks by entry PC, saved return address and stack slot. A return closes only
when both the return PC and the restored stack pointer match. Scene boundaries
split elapsed intervals without closing a callback; an unfinished callback at
the menu endpoint is an error. This applies the complete-call approach used in
Stellar 7, with stack-slot checks rather than a reconstructed general call tree.

| Callback | Hunk 0 offset | English file offset | 020 default entries, reset to menu |
|---|---|---|---:|
| Game clock VBL | `$34162` | `$3418e` | 8,329 |
| Music VBL | `$27810` | `$2783c` | 8,289 |
| Joypad VBL | `$33e62` | `$33e8e` | 8,327 |

The completed `tmp/phase4-irq-pair-020/{off,on}/` pair uses debugger digest
`bdadc9da8d89d4d6d6f21c8c155f0ca315e8eb38324467353d6b8810b5fd98ba`
and a fresh CACR `$00000001` audit. Every one of 3,409 ledger records, all raw
source buffers, final allocated game hunks and menu pixels match exactly.
All entries have matched returns. Entry instruction counts independently match
`tmp/phase4-profile-on-no-raw/` in every post-startup scene, whose complete event
ledger is also identical. Evidence: `neutrality.log`, `irq-check.log` and
`profile-crosscheck.json` within the pair directory.

Synthetic checks cover nested callbacks and a call spanning a scene boundary;
malformed ordering, wrong return stack, wrong entry PC, changed scene clock,
backward time and incomplete coverage are rejected. A separate five-field 020
instruction trace now validates 15 complete callbacks (five of each kind), with
exactly zero elapsed-unit residual for every call. Entry PC/SP order is matched
within independently timestamped trace fields; each return is an observed RTS
restoring the saved slot. The checker requires exact agreement for this fixture,
not merely agreement within the trace format's per-record rounding bound.

`tmp/phase4-irq-v2-trace-020/` uses debugger digest
`c30ad609dc1141b47d3b9cfbf7d5a86666445fee7985907beef60b095679d940` and
fresh cache audit `tmp/phase4-irq-v2-audit-020/`. Its complete callback intervals,
publication/census ledger, raw source bytes, final game hunks and menu pixels
match the uninterrupted 020 control exactly. The diagnostic retains its explicit
breakpoint flag; it is not substituted for the uninterrupted baseline. Evidence:
`tmp/phase4-irq-v2-trace-check.json`. Negative fixtures in
`tmp/phase4-irq-v2-negative-clock/` reject a one-unit decrease or increase in
callback duration and a changed trace-field clock.

Representative accumulated callback elapsed time from the uninterrupted 020
default run (all 34 scene rows are reproduced by `matrix_irq_check.py`):

| Scene | Game VBL ms | Music VBL ms | Joypad VBL ms | Callback union / scene |
|---|---:|---:|---:|---:|
| origin-animation | 1.509207 | 24.147811 | 40.607630 | 2.480156% |
| title-arrival | 2.552444 | 26.746704 | 68.720247 | 2.175811% |
| credits-00 | 3.652631 | 51.711215 | 98.312045 | 2.383403% |
| credits-15 | 3.673001 | 33.082880 | 98.933010 | 2.091169% |

Scope elapsed time includes callees and preemption;
innermost selected callback time is not routine self time. Exception entry,
dispatcher work and other handlers remain outside these three callback scopes.

The callback controls use `tmp/phase4-irq-matrix/` and its retry root, with
fresh cache audits and separate bare/IRQ arms. All 020, 030 and 040 cells pass
exact callback recording neutrality. The 060 default and NoCache pairs have
the bounded differences documented below; 060 DCache passes exact neutrality.
A completed acquisition validates callback event accounting and exact recorder
neutrality only; it does not by itself extend the 020 instruction-duration
calibration to the accelerated interpreters. General routine self/inclusive
attribution and the interrupt work outside these callback scopes remain open.

Five initial callback-control cells failed before emulator launch because their
selected debugger port was held by Red Baron: 020 NoCache, 030 MMU NoCache,
040 default, 060 default and 060 NoCache. The strict ownership check refused the
launch without stopping that process. Their failed records remain in
`tmp/phase4-irq-matrix/`; completed audited retries are in
`tmp/phase4-irq-retry/`. The original lane and all retries are terminal. No failed or
pending cell counts as a completed callback measurement.

### Independent beam calibration of callback intervals

`--irq-beam` applies Stellar 7's read-only VPOSR/VHPOSR method to three complete
calls of each known VBL callback at credits entry. GDB records entry PC, stack,
saved return address and beam position, then stops at the actual return address
and checks stack restoration. Samples align to the first matching callback after
the preceding observed return, starting at scene 15; duration similarity is not
used to select calls. The PAL decoder handles UAE's HP=0/1 convention and field
wrap explicitly. Each interval must be shorter than one field.

The completed `tmp/phase4-irq-beam-020/` uses the already audited v2 callback
debugger. All nine independently sampled intervals agree within one colour clock
(512 emulator units, about 0.282 microseconds). Maximum absolute disagreement is
384 units, about 0.211 microseconds. Every complete-run callback interval,
publication/census record, raw source buffer, allocated game hunk and menu pixel
matches the uninterrupted 020 control exactly. Evidence:
`tmp/phase4-irq-beam-check-020.json`. Negative fixtures in
`tmp/phase4-irq-beam-negative/` reject changed beam time, return stack and callback
order; PAL line/field rollover cases are also checked.

This calibrates beam observations against the 020 instrument whose durations
already match an instruction trace. All ten additional machine/cache beam
captures are complete under `tmp/phase4-irq-beam-matrix/`, with fresh cache audits.
Their completed beam reports must still be compared with matching uninterrupted
callback controls before acceptance. The diagnostic breakpoint flag remains set;
these runs do not replace uninterrupted FPS baselines. Measured intervals include
callees and preemption, and still exclude interrupt entry/dispatch outside the
selected callbacks.

### Consolidated instrument evidence and limits

Completed rechecks use existing captures without emulator runs:

| Report | Cells accepted for the stated scope |
|---|---|
| `tmp/phase4-instrument-accept-01/` | 020 default, 020 NoCache, 030 MMU default, 030 MMU NoCache |
| `tmp/phase4-instrument-accept-02/` | 030 NoMMU NoCache, 040 default |
| `tmp/phase4-instrument-040-dcache.json` | 040 DCache |
| `tmp/phase4-instrument-060-dcache.json` | 060 DCache |

For each accepted cell the checker matches the effective cache/core audit and
debugger hash, recomputes raw-source changes, checks isolated idle/DMA/callback
controls, and compares the beam diagnostic with its uninterrupted callback
control. The DMA and callback bare runs also have identical complete event
ledgers. The second report rejects 030 NoMMU default because the diagnostic
publication/census ledger differs from its uninterrupted control. Its other
individual instrument checks do not override that failed comparison.

Acceptance covers DMA slot ownership, stopped-CPU idle and the three selected
VBL callbacks only. Missing runs remain pending. The summary is a snapshot;
a pending row is not evidence that a subsequently completed capture passes.
Negative fixtures reject stale debugger hashes, CACR and options and preserve
missing captures as pending (`tmp/phase4-instrument-negative/result.json`).

The 040 default beam duration check needs the explicit endpoint model below.
The 060 default callback on/off
ledgers differ at record 2327 despite both containing 6739 records. Evidence is
retained in `tmp/phase4-irq-beam-matrix/040-default/` and
`tmp/phase4-irq-retry/060-default/`. The 060 discrepancy remains unaccepted and unexplained. It does not invalidate the independently
accepted cells, and must not be hidden by aggregate matrix completion flags.

The outstanding general routine attribution problem concerns interrupt/task
stack transitions and synthetic returns. Callback elapsed times include callees
and preemption and cannot stand in for routine self times or complete interrupt
cost. Further diagnosis should use a short representative window before any
additional matrix acquisition.

### Representative profile: what already informs the next change

The validated 020 leaf profile identifies software c2p as a substantial cost:
44.480% of total Origin-animation time, 61.409% of Origin-particles time and
49.741% of credits-00 time with default caches. These are direct instruction
costs in the verified converter ranges above, independent of the broken general
calling-context tree. The corresponding TOD-limiter instruction costs are only
0.017%, 0.023% and 0.017%. The three measured VBL callbacks occupy 2.480% of
Origin-animation time and 2.383% of credits-00 time, including their callees and
preemption. These differently defined measurements must not be summed as a
complete partition of time.

This evidence supports prioritising c2p in the later rendering phase. It does
not predict a speedup: the fastest-cell bypass saves only 9.703 ms across the
whole intro with the original limiter active. Timing coupling and pacing still
need the separately authorised later phases. Complete attribution of system
returns is not needed to establish the observed converter cost; it remains
necessary for the exhaustive accounting gate as currently written.

Inspection of the existing 040 default beam samples narrows its failed check:
all three music and all three joypad samples have zero residual. Only the three
short game-VBL samples differ, by -512, +512 and -512 emulator units (one colour
clock). Their observer durations are respectively 1024, 1536 and 1024 units;
the independent beam intervals are 3, 2 and 3 colour clocks. The pinned emulator source explains a possible endpoint skew: `m68k_run_3ce`
calls `do_specialties` (which services debugger stops) before the cached-access
workaround may advance one `CYCLE_UNIT`. The next callback observation occurs
after that adjustment. Each debugger endpoint can therefore precede its ledger
endpoint by zero or 512 units. The difference of the two endpoint adjustments
is between -512 and +512, in addition to beam quantisation below 512 units.

The checker applies a strict residual bound below 1024 units only to 040/060
captures from the reviewed debugger digest `c30ad609…`. It reports the extra
512-unit endpoint uncertainty separately; the 020/030 bound stays below 512.
This is bounded agreement, not exact endpoint equality. The existing 040 default
capture passes, and its complete callback intervals, event ledger, raw sources,
final hunks and pixels match the uninterrupted control. Evidence:
`tmp/phase4-040-beam-boundary-check.json`. Corrupted beam (+4 clocks), stack and
callback-order fixtures still fail (`tmp/phase4-040-beam-boundary-negative/`).
No new emulator capture was needed.

### Bounded 060 callback-recording differences

The existing bare/IRQ pairs in `tmp/phase4-irq-retry/` have identical scene
boundary times, scene publication counts and scene field counts on both 060
default and 060 NoCache. Every event payload apart from its clock/field matches;
all raw source bytes, four final allocated game hunks and menu pixels match.

| Cache option | Changed event clocks | Largest absolute clock difference | Changed event fields |
|---|---:|---:|---:|
| default | 29 of 6,739 | 0.729370 ms | one event, one field |
| NoCache | 8 of 6,739 | 0.235981 ms | none |

Evidence: `tmp/phase4-060-default-irq-effect.json` and
`tmp/phase4-060-nocache-irq-effect.json`. These comparisons bound differences in
this recorded route; they do not identify their cause, prove callback-duration
accuracy or establish a universal error bound. Exact neutrality still fails.
The already measured scene-level rates and durations agree across these pairs;
the local discrepancies must not be hidden by that aggregate agreement.

The effect reporter now supports isolated callback recording as well as DMA.
It compares event payloads before pairing timing differences, so frame/census
changes cannot be mistaken for clock-only changes. Its original DMA path still
reports exact equality on the corrected 020 default pair
(`tmp/phase4-dma-effect-regression.json`).

### Representative idle, callback and chip-bus measurements

These rows come from the four accepted cells in
`tmp/phase4-instrument-accept-01/`, using exact recorder controls. STOP and
callback percentages use scene elapsed time; CPU/bitplane/blitter percentages
use available chip-bus slots. They have different denominators and must not be
added. CPU bus share is not CPU utilisation, and unclaimed slots are not idle.
Callback share covers the three named VBL callbacks, not complete IRQ dispatch.

| Cell | Scene | STOP % time | Callback % time | CPU % slots | Bitplanes % slots | Blitter % slots |
|---|---|---:|---:|---:|---:|---:|
| 020-default | origin-animation | 0.000 | 2.480 | 3.329 | 8.579 | 0.000 |
| 020-default | origin-particles | 0.000 | 2.458 | 4.565 | 8.581 | 0.000 |
| 020-default | credits-00 | 0.000 | 2.383 | 4.245 | 8.583 | 0.000 |
| 020-nocache | origin-animation | 0.000 | 2.661 | 2.341 | 8.585 | 0.000 |
| 020-nocache | origin-particles | 0.000 | 2.477 | 3.833 | 8.585 | 0.000 |
| 020-nocache | credits-00 | 0.000 | 2.569 | 3.405 | 8.579 | 0.000 |
| 030-mmu-default | origin-animation | 0.000 | 1.909 | 7.369 | 8.572 | 0.000 |
| 030-mmu-default | origin-particles | 0.000 | 2.084 | 7.335 | 8.576 | 0.000 |
| 030-mmu-default | credits-00 | 0.000 | 1.633 | 7.936 | 8.582 | 0.000 |
| 030-mmu-nocache | origin-animation | 0.000 | 1.949 | 7.362 | 8.588 | 0.000 |
| 030-mmu-nocache | origin-particles | 0.000 | 2.123 | 7.332 | 8.582 | 0.000 |
| 030-mmu-nocache | credits-00 | 0.000 | 1.687 | 7.932 | 8.589 | 0.000 |

The selected scenes have no STOP idle and no blitter slot use. This excludes
those two mechanisms as direct consumers in these windows, while leaving busy
waits and system work unclassified. The limited callback share and large measured
020 converter cost support investigating software rendering first. Bus averages
alone do not establish whether individual CPU accesses suffer contention.

The completed beam-only rechecks for 040 DCache and all three 060 cache states
pass the source-derived endpoint bound (maximum residual 512 units). Their
`endpoint-check.json` reports remain under `tmp/phase4-irq-beam-matrix/`.
040 DCache, 060 DCache and 060 NoCache also match their uninterrupted callback
controls in full. The 060 default diagnostic ledger differs. The first two also
have consolidated passes listed above; the NoCache comparison alone is not one;
in particular, 060 NoCache still fails bare/IRQ exact recorder neutrality.

## Phase 5: intro motion model and PC reference

Phase 5 analysis is complete. **The user selected 10 native updates/s for the
intro, matching flight**, superseding the PC-derived candidate below. The video
is a secondary visual reference, not an intended-rate authority. The user's clarified
reference is the movement of ships, explosions and asteroids: visible advances
per second **and distance/size change**, not total intro length or credit duration.
Keep the existing music and text deadlines. Their cadence is not a motion-rate
calibration.

### Optical motion reference

The supplied `wcpc.mov` is 96.611667 seconds, SHA-256
`53942f67631e30868a214a92fae45776193306bcc805ecf27c54e5279c7be8f3`.
The user identifies the configuration as eXoDOS's 86Box 4.2, 486SX/16 MHz.
That configuration and sustained emulator speed are user-reported, not independently
verified by the clip. The last frames do show the opening caption starting again;
the recording is not cut off partway through the credits.

`intro_motion_reference.py` samples three one-second passages at 60 samples/s.
This is the analysis sampling rate, **not game FPS**. The handheld recording can
contain mixed screen refreshes, so adjacent changed camera frames are not each
counted as a game advance. Ship/explosion foreground changes tolerate two pixels
of translation and are grouped across adjacent mixed samples. Four thresholds
are retained; contacts and the selected asteroid poses allow visual review.
All decoded media, colour masks/measurements and contacts remain in `tmp/`.

| Moving subject | Video window | Approximate visible cadence | Projected movement in the sampled passage |
|---|---|---|---|
| Approaching ships | 28.0–29.0 s | **14–15 advances/s**; 14 change groups at every tested threshold | Upper ship's box centre moves about **7% of viewport width left in 0.20 s**; its left edge moves 41 analysis pixels, about 23 pixels on a 320-wide view |
| Explosion | 29.0–30.0 s | **about 14 advances/s**; 12–14 automatic groups, 14 at the two stricter thresholds | Bright burst width grows from about **21% to 42% of viewport width in 0.40 s** (29.133–29.533 s) |
| Asteroid approaching below the caption | 36.2–37.2 s | **roughly 20–25 advances/s**, less certain than the ships | From 36.200 to 36.333 s, its bright component moves down about **8% of viewport height** and grows from 30 to 39 analysis pixels high |

The asteroid estimate uses six visibly distinct poses at 36.233, 36.300, 36.333,
36.383, 36.417 and 36.467 s: five advances in 0.233 s, about 21/s. The automatic
whole-image change groups are deliberately **not** used as an asteroid frame
counter: mixed refresh images join consecutive advances. This short optical
sample supports an approximate range, not a precise constant for the whole game.

Coordinates refer to a 640×360 analysis image, with approximately 560×224 pixels
covering the game viewport. Camera motion, threshold edges, perspective and sprite
rotation limit precision; these are screen-space examples at those depths, not
constant world velocities. The asteroid component is isolated from the adjacent
smaller rock. Explosion growth is reported as width, not translational speed.
No audio waveform/synchronisation claim is made from the phone recording.

The existing original 020 raw-source capture supplies the Amiga comparison,
without another emulator run. In title-animation source frames 21–26, five
intervals take 0.623497 s: **8.02 drawn frames/s**. Explosion frames 29–36 give
**8.32 drawn frames/s**. The first asteroid page averages **12.52 source frames/s**
over its consecutive-frame intervals. These source timestamps precede conversion;
they are not monitor refresh measurements. The retained raw stream was independently
validated in phase 4.

Low drawn FPS does not by itself mean slow movement. The Amiga upper ship's left
edge moves from native x=95 to x=67 between source frames 21 and 23, in 0.243820 s:
about **115 native pixels/s**. The PC sample's 41 analysis pixels in 0.20 s,
normalised to 320-wide coordinates, is about **117 pixels/s**. These are similar
short portions of the approaching ship's path, not pixel-identical cross-port
states. The agreement is approximate, but shows why doubling drawn FPS while
keeping every old movement increment would be wrong.

### Update, draw, wait and publish

Offsets below are hunk-relative (`E` = executable hunk 0, `H3` = hunk 3,
`S` = slave code hunk). Add `0x2c`, `0x42dec` and `0x20`, respectively, for file
offsets. Data `D` is hunk 1, with file base `0x3a048` where stored.

| Path | Native work and timing |
|---|---|
| Ships/title, `E:1fd00–1fd8e` (file `1fd2c–1fdba`) | Calls update `E:02a8` on every pass; `E:1fd06` draws only on odd D2. Exactly **296 update calls and 148 publications**. D2 and title geometry advance per pass, with no elapsed-time factor. |
| Asteroids/credits, `E:1fdd6–1fe48` (file `1fe02–1fe74`) | Saves the VBL clock, then update `E:1fdda`, draw `E:1fde0`, publish through `E:1fe14`, input `E:1fe1a`, deadline `E:1fe2a`. **One update per draw** on this captured path. The page ends at 320 VBL counts; its text stops being drawn at 220. These are VBL deadlines, not direct tracker-row comparisons. |
| Shared update, `E:02a8–02da` (file `02d4–0306`) | Services `E:0260`, dispatches `E:76e4`, `E:7b4e`, `E:680e`, conditionally `E:1568`, and increments the update counter. No elapsed-time argument at this boundary. This is not a complete flight-system audit. |
| Draw, `E:02e4–0342`; finish `E:0c40–0c66` | Drawing divisor/clear/world drawing, overlay handling, then `E:02dc` → `E:31fc2`. |
| Software conversion/publish, `E:31fee–31ff6` | Sets source/destination, calls patched `E:32028` → `S:178a`, waits in the original limiter, converts, selects the buffer and calls `E:3378e`. Exactly one COP2LC store per observed publication. |
| Input | Ship/title poll `E:1fd76`, asteroid poll `E:1fe1a`, both call `E:1898a`. No input is injected before the completed credits cycle. |

Origin also mixes clocks: `H3:0f2a/0f98` exits the opening animation at music cue 2;
`H3:1066` holds the expression at cue 4; `H3:0db2` holds after flight until cue 9.
Separation `H3:1194–11a2` and flight `H3:129a–12a4` advance by loop iterations.
Particles change behaviour at cue 10 (`H3:12dc`), stop spawning at cue 12
(`H3:13d4`), then drain per-frame work. Consequently a music-anchored cut can stay
correct while motion inside it speeds up, or its final drain takes longer.

### Targeted coupling and time-source checks

Only three full timing captures were added: an equal-size 020 control/slow pair
and an original-slave 030/50 MMU comparison. No new debugger build, DMA matrix or
profiling campaign. A separate short boot located the diagnostic slave. The
read-only instruction observer records scene cuts, publications, VBL entries,
tracker positions, limiter samples and delay endpoints without stopping the
measured intro. All three complete the full cycle and reach the menu.

The VERIFY-only slowdown adds 100,000 decrement-loop iterations inside the c2p
wrapper at `S:178e` (file `17ae`). The original instruction is replayed by a
20-byte tail at `S:1e0c`; interrupts remain enabled and registers are preserved by
the existing wrapper. The equal-size control uses zero iterations. Original
bytes differ only at the declared four-byte detour; the two fixtures differ only
in the delay immediate. They are not release slaves or new CUSTOM behaviour.
The measured added-call span is approximately **31.94 ms median** on the 020
(control 2.75 microseconds), rather than an assumed delay from instruction counts.
The control and slow slaves are 7,748 bytes, SHA-256 respectively
`345e82b1fa5c14ab1a9b74c8776fd170b9318b04d5a904bb85048e3aae122eca`
and `730deb71df55e2b29b12dc721964b8ad03dab5125c91d79381a9c409bbd4e24d`.
All three ledgers pass the timing reporter. Wrong CPU clock units, a corrupted
VBL counter and a missing publication are rejected by deliberate negative checks.
The fixture pair's only differing file bytes are `1e2f–1e31`, within the delay
immediate, and the slowdown retains the same 296/148 title update/draw counts.

| Window | 020 control seconds / publications | 020 slowed seconds / publications | 030 MMU seconds / publications |
|---|---:|---:|---:|
| Origin separation | 1.431 / 17 | 1.971 / 17 | 0.650 / 17 |
| Origin flight plus music hold | 10.127 / 42 | 9.587 / 42 | 10.908 / 42 |
| Ship preamble/action before title arrival | 6.148 / 67 | 8.249 / 67 | 2.646 / 67 |
| Title arrival | 4.505 / 50 | 6.116 / 50 | 2.003 / 50 |
| Title departure | 3.020 / 31 | 4.012 / 31 | 1.239 / 31 |
| First asteroid/credit page | 6.446 / 81 | 6.464 / 60 | 6.412 / 161 |

The two-update ship loop is frame-coupled. Credits deadlines stay clocked while
asteroid updates/publications change. The complete expression interval remains
5.300/5.278/5.300 s and reaches music `(cue,order,row,tick)=(4,1,0,0)` in all
three runs. Flight-plus-hold ends at `(9,2,16,0)` in all three. In contrast, ship
preamble/action ends at `(3,0,51,4)`, `(4,1,5,0)` and `(1,0,22,1)`: motion is not
kept in musical step. Full per-scene music endpoints remain in the JSON reports.

Runtime confirmations, limited to this English PAL software-c2p intro:

- Game VBL `E:34162` and counter `D:7f02` agree one-for-one over 8,328 / 8,616 /
  7,689 consecutive intervals. Music callback `E:27810` likewise runs once per
  field over 8,288 / 8,576 / 7,662 intervals. The music clock does not depend on
  render speed. The cadence and existing tracker cue checks do not uniquely fix
  a motion rate inside a scene.
- `S:17b8–17e6` samples CIA-A TOD. Consecutive D1 samples agree exactly with elapsed
  fields at every limiter exit, in all three runs. Deltas never fall below two.
  On the fast 030, 3,333 of 3,342 intervals are exactly two: the normal limiter
  caps conversion at approximately 25/s on PAL. This is a cap, not proof of the
  intended ship-motion rate.
- The active patched music delay `S:1774–1784` executes four times per capture;
  observed spans are 0.264–0.319 ms across the runs, consistent with its five
  changing VHPOSR-line waits. The original CIA-B TOD short-delay routines are
  replaced on this path. Previously validated STOP/VBL and blitter waits remain
  display/idle synchronisation, not an independent motion tick.
- No inference about flight's mission clock, unvisited modal paths, NTSC, German
  or OCS follows from these observations.

### Rate decision

The selected intro target is **10 native world updates/s**, matching the measured
flight-unit anchor. This is a practical design decision, not independent proof
of the original intro's historical intended rate. Native displacement is not
scaled toward the earlier 15–17/s PC-derived candidate. The recorded PC ship,
explosion and asteroid advances remain reference observations only.

The enhanced ship/title and asteroid-credit loops now separate updates from
rendering. Ships, asteroids and the scripted camera use bounded display-time
extrapolation. Discrete explosion images remain tick-owned; no intermediate
artwork is fabricated. Music playback and native credit deadlines are retained.
See the intro-clock implementation gate below for exact scope and validation.

## Phase 6 rendering implementation

Rendering work is complete; intended-speed calibration and exact duration
neutrality remain deferred under the user's instruction to investigate timing
in-game later. No new motion rate is installed. `Custom5=0–3` retains the existing
limiter. Music and credit-text deadlines are not patched. This is an experimental
English intro build, not a release or a gameplay timing fix.

### Gating, converter selection and cache policy

`Custom1=2` enables the renderer; `Custom1=0/1` retains the original
English/German paths. The only original slave seams are four-byte instructions
at `S:1422` (SetCPU) and `S:178a` (converter wrapper). Normal reconstruction is
still byte-identical. An equal-size control redirects only the cache-policy
seam and retains the original converter. Both builds restore the original
SetCPU request when disabled. Enabled mode rejects `Custom5>=4`; that option
selects the old blitter converter, not Akiko. No Akiko implementation was found.

The embedded converter's authorship has not been established: “existing slave
converter” identifies its location, not its author. Mikael Kalms' public-domain
030 and 040/060 routines are vendored unmodified and pinned in
`manifest/kalms-c2p.tsv`. The build generates immutable specialisations for
320×128, 320×166 and 320×200, with plane strides 5120, 6640 and 8000 bytes.
Full-frame conversion follows the intro change census. No new converter performs
SMC, copies code, or allocates workspace.

**Selection follows measurements, not the routine's CPU suffix:**

- 020/030 with instruction caching enabled: Kalms 030 family.
- Instruction caching disabled, or 040/060: retain the existing slave converter.
- `--render-family 030/040` is an explicit diagnostic override, not the default.

At startup a zero-mask `resload_SetCPU` query reads WHDLoad's effective policy
(`WCPUF_IC`, bit 8). It changes no settings; the API performs its normal one-time
cache flush. The selected family is stored as data at `S:1f3e` in the final
non-VERIFY build. No cache setting is forced and no flush occurs per frame.
Unmeasured cache/CPU combinations conservatively retain the existing converter;
no speed improvement is claimed for those cells.

The final wrapper is at `S:1e0c`, the display wait at `S:1ebe`, and the cache-policy
adapter at `S:1ed4`. After conversion, graphics.library WaitBOVP waits for the
existing ViewPort (established at `E:33afe`) before the original index change and
single publication at `E:3378e`. This protects reuse of the old front buffer.
Double buffering remains; no measurement justifies a third buffer.

### Correctness

`tmp/phase6-native-final-policy.json` records **688 native comparisons**, all
three heights, zero/one/ramp/random sources, and real sources from 31 intro
scenes. The checker runs the existing converter, both applicable converter
bodies and enabled/disabled wrappers against an independent pixel model. Every
destination store is hooked: exact once-only coverage, bounds, source integrity
and wrapper register preservation pass. **60 cache/option-gate cases** pass,
including rejection of the unsupported blitter option. Missing-converter,
wrong-mask and wrong-geometry negative fixtures are rejected.

Unicorn's 060 model rejects MOVEM. Its dispatch is therefore tested on the 040
ISA model, with actual 060 execution checked separately in FS-UAE. These native
checks establish semantics, not speed. The live twin build allocates a separate
64000-byte FAST reference destination, executes the existing converter on the
same source, and compares every output longword before publication:

| Live intro through menu | Verified frames | Output differences |
|---|---:|---:|
| 020, cached Kalms candidate | 1106 | 0 |
| 060, Kalms 040 diagnostic candidate | 2291 | 0 |
| Final 060 NoCache selection (existing converter) | 2314 | 0 |

The captures are `tmp/phase6-twin-020/`, `tmp/phase6-twin-060/`, and
`tmp/phase6-final-twin-060/`. The final selector reports 30 in the cached 020 run
and 0 in the 060 NoCache run, as intended. Twin overhead is excluded from all
performance comparisons. The final enabled 020 and both 030 core runs preserve
296 ship updates / 148 title publications, the scene/page sequence, game/music
interrupt cadence and one copper publication per completed frame. Their matched
menu screenshots are pixel-identical (`tmp/phase6-menu-pixels.json`); the comparison
report also enforces this check.

### Measured converter choice

Matched controls use the same slave allocation size, CPU backend and live CACR.
Figures below are median elapsed service time for the 320×128 converter over
an uninterrupted intro. They include interrupts inside the interval, exclude
the limiter and display wait, and describe the calibrated **emulator model**,
not physical accelerators. There is no claim of a corresponding FPS increase.

| Configuration | Existing, ms | Candidate, ms | Decision |
|---|---:|---:|---|
| Final 020, instruction cache | 41.777 | 38.726 (Kalms 030) | Select; 7.3% less time |
| 030 NoMMU interpreter, caches | 16.150 | 11.375 (Kalms 030) | Select; 29.6% less time |
| 030 MMU interpreter + WHDLoad MMU, caches | 9.027 | 6.142 (Kalms 030) | Select; 32.0% less time |
| 020 NoCache | 42.022 | 48.774 (Kalms 030) | Reject; retain existing |
| 040, caches | 18.919 | 21.884 (Kalms 040), 22.509 (Kalms 030) | Reject both |
| 060, caches | 18.918 | 21.908 (Kalms 040), 22.506 (Kalms 030) | Reject both |

Evidence: `tmp/phase6-final-render-020/report.json`,
`tmp/phase6-render-030/report.json`, `tmp/phase6-render-030-mmu/report.json`,
`tmp/phase6-render-020-nocache/report.json`, `tmp/phase6-render-040/report.json`,
`tmp/phase6-render-060/report.json`, and `tmp/phase6-030-on-040/report.json` /
`tmp/phase6-030-on-060/report.json`. Earlier candidate measurements determine the
selection; the final 020 pair rechecks the completed selector. The converter
bodies remain unchanged. Full fresh timing matrices for every retained-original
cache cell, optional 060 BranchCache/StoreBuffer/SuperScalar combinations and
physical hardware are **not** claimed complete. 320×166 has native correctness
coverage but does not occur in this intro window; its live use belongs to gameplay.

### Existing FAST placement and FMODE 3

The observed chunky sources and loaded game hunks are already in FAST memory in
the 8 MiB FAST setup. The 128 KiB workspace pointer (hunk 1 offset `7b9e`, written
at `E:31f58`) also points into FAST at the credits probe. The unused old c2p
workspace pointer is zero on this software path. No broad AllocMem flag patch
is introduced; smaller-memory configurations remain untested.

Both captured generated copper lists have FMODE `0003`, DDFSTRT `0038`, DDFSTOP
`00d8`, and BPL1MOD/BPL2MOD `fff8`. The original phase-4 menu trace has the same
values in both lists. Planar buffers are CHIP, eight-byte aligned, with the
expected plane spacing. Graphics.library already configures FMODE 3 in these
states: no new fetch patch is needed and **no freed chip-bus slots are claimed**.
Sprites and OS-generated lists stay untouched. Evidence is the credits memory
in `tmp/phase6-probe-v1/` and original menu trace in
`tmp/phase4-dma-cia-matrix/020-default/bare/`. These observations resolve the
previous FMODE hypothesis for the captured states only.

### Timing limitation and phase gate

The existing limiter is not an intended-speed calibration. Converter savings
and the display-end wait still interact with per-frame motion. In the final
020 comparison the title animation is **0.638 s longer**, and reset-to-menu is
**0.631 s longer**. Individual credit-page differences are at most 0.075 s in
that pair. The cached 030 candidate title differs by +0.010 s (NoMMU interpreter)
and +0.006 s (MMU); their whole-window differences are -0.008 s and +0.002 s.
The title update count, music driver, 320-tick credit deadlines and 220-tick text
threshold remain unchanged. Thus **exact scene-duration neutrality is not
claimed**, despite the retained limiter.

Four TOD/field-sample discrepancies in the final 020 ledger are recorded rather
than hidden: adjacent samples straddling an interrupt/field boundary can differ
because the TOD read precedes observation at `S:17e6`. The minimum two-tick
limiter threshold still holds. No new timing-backend calibration is claimed.

Phase 6 stops here with measured converter selection, bit-exact output evidence,
cache-preserving gating and safe publication. The original gate's exact-duration
requirement remains deferred with the user's timing investigation. No universal
motion rate, phase-7 gameplay analysis, release archive or OCS work is included.

## Phase 7: flight time model and reproducible gameplay windows

The English CD32 flight gate is complete. Normal flight advances the world once
per rendered picture in the captured default configuration. The native speed and
range units imply **10 world updates/s**, replacing the unmeasured 15/s flight
prior. This is a flight-unit calibration, not an intro rate or an implemented
limiter. The timing fix and exhaustive framerate audit remain later work.

### Route, counters and evidence

`Custom3=1 Custom4=0` selects Enyo, mission 0; those options alone do not bypass
the front end. The existing argument parser accepts bare `l` for direct flight
(`H3:056a`, file `43356`, sets `D:004e`), and `as1` for starting navpoint 1
(`H3:0594–05b0`). The diagnostic fixture replaces the redundant standalone `-`
emitted before `s1` with `l` at `S:156d` (slave file `158d`). Optional `as1` is
placed in the unused argument buffer tail. It uses the original game's parser;
no game instructions or release defaults change. `Custom2=2` supplies invulnerability.
The no-input departure window is reproducible; Nav 1 supplies nearby combat.

Offsets below use `E` = English hunk 0, `D` = hunk 1, `H3` = hunk 3, and `S` =
slave code hunk. Code file offsets are `E+002c`, `H3+042dec`, `S+0020`.
Most flight state is in hunk 1's zero-filled allocation beyond stored offset
`8464`, so those `D` offsets have no corresponding stored file bytes.

The normal loop at `E:0698–06c6` polls input, calls world update `E:02a8`, then
`E:0510` and the cockpit path. `D:914c.w` increments at `E:02d6` (file `0302`);
the observer samples its completed value at the next `E:0698`. The draw gate
`E:02e4` uses `D:008e/0090.w`; `D:9150.w` increments at `E:02f4` (file `0320`).
The observed divisor is one. Publication remains `E:3378e` (file `337ba`).
Do not equate these counters in a modal loop or after changing the draw divisor.

Each coast capture has three uninterrupted 100-field windows, with debugger
stops only between windows. Window 0 includes asset setup and acceleration and
is excluded from settled figures. The corrected combat tape then holds Space
(fire), Right (turn) and Tab (afterburner) for 100 fields each, enters pause via
P, samples ten fields, resumes with Space and samples twenty fields. Inputs use
the native shared debugger key route; recordings, traces and screenshots stay
in `tmp/`. This is a short invulnerable flight, not a campaign-completion test.

The phase-7 observer snapshots the allocated hunk 1 at `E:0698` without stopping
or modifying the guest. A no-snapshot control, also including the census flush
fix, has identical events, emulated cycle timestamps and screenshot pixels in
all three coast windows. Short single-scene captures required explicit census
flushes: the older delayed capture has no usable source census, not zero change.
Frame-counter checks compare successive state counters, publication counts and
an independent full instruction trace; see the retained validation report: 100 complete fields contain 20 flight entries,
20 completed updates, 20 publications and 100 VBLs, with matching registers and
field placement in the independent trace.

### Native speed/range anchor and coupling test

Positions (`D:919a+12*i`) and velocities (`D:9d6c+12*i`) are three signed longs
with eight fractional bits. `E:80b6–80e0` adds velocity to position once per
world update, without an elapsed-time factor. The set-speed HUD path multiplies
its native value by ten (`E:22c2–22ca`); actual speed takes the velocity magnitude
and applies the same scale (`E:22ee–230a`). Nav range is the length of the
navpoint/player difference, shifted right eight (`E:3066–30d0`, `D:ab80.l`);
`E:2848–2896` formats it with the ` km` suffix at `E:28aa`.

At settled displayed speed 200 kps, velocity magnitude is 5120 fixed-point
units: **20 km per update**. Therefore **200 / 20 = 10 updates/s** is the rate
at which the game's own units agree. The nav HUD caches a value one update
behind the entry snapshot; compare equivalent update stages. The departure course is not directly toward the navpoint: its cached range
rises 34719→34893 km across the first settled 19 intervals. The anchor uses full
3D displacement and the verified range-unit conversion, not radial range loss. This does not establish an intended cadence for every animation or AI
subsystem.

| Configuration, settled coast windows 1 / 2 | Updates and pictures/s | Travel km/s at displayed 200 kps | Mean update ms |
|---|---:|---:|---:|
| 020, original converter and normal limiter | 10.230 / 10.104 | 204.60 / 202.07 | 97.75 / 98.97 |
| Same 020, matched 100,000-iteration c2p delay | 7.735 / 7.685 | 154.69 / 153.70 | 129.29 / 130.12 |
| Calibrated 030 NoMMU interpreter | 24.956 / 24.966 | 499.12 / 499.33 | 40.07 / 40.05 |

These are short-window emulator measurements, not real accelerator benchmarks.
The stock 020 uses exact unit 128; 030 uses the previously calibrated NoMMU
interpreter, unit 36. Seconds use emulated cycles / `(512 * 3546895)`.
Both use the original software converter, `Custom5=0`, and equal-sized diagnostic
slaves. No phase-6 renderer or new gameplay timing patch is enabled.
The 020 windows contain 19 / 20 complete intervals; their p95 is
100.31 / 100.38 ms and maxima 100.31 / 100.49 ms.

The repeated boot matches 65 consecutive entry states. The delay matches 49,
and the 030 matches the first 65, by update index: all 61 position, velocity,
forward-vector and object-type slots; ten ship action, set-speed, fuel, energy,
shield, armour and target slots; RNG and update/draw counters. Identical native
steps take different wall-clock times. This directly demonstrates render-coupled
flight motion; the existing limiter does not maintain the native 10 Hz model.

### Representative flight costs and source changes

In the 020 no-input windows 1 / 2, changed source bytes are only
**0.03059% / 0.04156%** of the complete 320×200 source compared with its previous
conversion. This includes the whole cockpit image, not an isolated cockpit crop.
The Nav-1 fire / turn / afterburner windows change **1.000% / 1.382% / 0.711%**.
These observations motivate later work; they do not prove that skipping writes
or conversions would preserve animation.

Native profiler PC buckets attribute **65.90% / 64.09%** to existing slave
converter addresses `S:17f6–1e04`, **12.15% / 13.38%** to math
`E:2a9d4–2cbd8`, **7.93% / 8.27%** to drawing `E:2d000–31fc2`, and
**2.35% / 2.51%** to world dispatch/motion `E:65b4–10c7a`.
These are address-range costs, not full self/inclusive call-tree attribution.
The profiler residual is zero and its recorded gap about 0.9% in these windows.
The approved phase-4 interrupt/DMA/attribution gaps remain; no new matrix is
needed to establish the flight coupling result.

### State map and cadence

`i=0` is the player. World arrays serve up to 61 entity slots; several detailed
ship arrays serve ten ships. Bounds differ: do not extend a ten-ship structure
to all projectile/effect slots. **Update** below means a call to the world
update, **draw** means a permitted presentation pass, **clocked** means VBL-based,
and **modal** means a separate control flow. Static writers classify paths not
exercised by the tape; that is not a claim of runtime coverage for every branch.

| State (hunk-1 offset) | Writer / consumer evidence (hunk-0 offsets) | Cadence and coverage |
|---|---|---|
| Position `919a+12*i`, velocity `9d6c+12*i` | Acceleration `7f78–80b4`, integration `80b6–80e0` | Update; straight trajectories and changed-rate coupling measured |
| Forward `a148+12*i`; other orientation bases `b450`, `b750`; angular steps `9578/95f8/9678+2*i` | Input `18daa–19070`, scale `0742–07ce`, rotations `7c86–7d18` | Update; Right-key turn exercised; orientation is fixed-point vectors, not a single heading |
| Set speed `99be+4*i`; actual speed derived from velocity | Acceleration `7f78–80b4`; HUD `22c2–230a` | Update; 200-kps straight-flight anchor measured |
| Ship action `9564+2*i`, afterburner timer `bb14+2*i`; fuel `a7cc+4*i` | Action setter `11688`, activation `cad8/cb42`, countdown/drain `7e10–7ed4`, fuel subtract `1591a`; normal drain `cb78` | Update; Tab exercised. Timer is a step count, not seconds. Fuel falls 199540→196055 in the retained afterburner window while actual HUD speed rises about 200→1237 kps |
| Gun energy `9546+2*i` | Fire spend `c52e` and subsequent store; recharge `cc36–ccd2` | Update/action; Space firing gives energy 88–100, then recovers. Recharge depends on shields/system damage; fuel is separate |
| Shields `a7f4+4*i` (two words), maxima `c03a+4*i`; armour `9876+8*i` (four words) | Shield regeneration `cba4–cc34`, eligible by update modulus; damage path `a49c–a598` selects and subtracts armour; HUD `1f86` | Update/event, not elapsed seconds. Static classification; invulnerability means this tape does not validate ordinary player damage balance |
| Ship hull/system damage `98c6+2*i`, `9946+i` | Damage writers `abf8`, `aa1c` | Hit-event changes within update; static, not a separate damage clock |
| Entity type `96fe+2*i`, model `97f6+2*i`, AI action `9564+2*i` | Dispatch `76e4`, `7b4e`; AI `8940–8ac4`, eligibility `89c6–89e4` | Movement each update; ordinary combat decision eligibility every fourth update, with exceptions for selected missiles and mode. Other-ship trajectories compared; not every AI branch exercised |
| Projectile/missile position and velocity in entity arrays; lifetime `baa8+i`, guidance stage `ba52+2*i` | Spawn `c458`, `ca38–cad6`; lifetime seed `ca9e`, decrement `77ea/7820` | Update/event; gun firing exercised. Missile lifetime/guidance classification is static; no claim of a live missile-lock test |
| Target `955a+i`, lock flag `38b0.w`, selection globals including `3898.w` | Target invalidation `3bba`, lock/selection `3bc4–3d1a`, selected missile `19832` | Input/event plus draw-based targeting checks (including draw-counter modulo eight); not an independent real-time lock clock. Static branch coverage |
| Message countdown `a956.w`, text pointer `00f2.l` | Set `2298/39c4`, decrement `22a6`, clear `5a86`, called after draw gate at `051a` | Draw-count duration; comms/menu actions replace or clear messages |
| Comms mode `0232.w`, speaker `027e.w`, portrait selection `0282.w`; portrait table `b270` | Mode setter `53be`, selection flow `545e–584e`, portrait drawing `4338–4460`, reset `5a20` | Modal selection plus draw-coupled portrait animation: `435c` tests odd draw count, `43ee` chooses a random frame. This is not a free-running video clock; static, conversation not entered by tape |
| Cockpit cached animation `a7bc/a7c4/a7c8`; hand state `af9e`; blink phase from `7f02` | `1de4` uses draw-counter modulo four; hands `3d66`; blink `1a78` divides clock by 40 | Mixed draw/input/clocked presentation. Do not scale the entire cockpit with world motion |
| Explosion/effect countdown `c076+2*i`, script index `c0f6+2*i` | `28fd0` decrement, `28fea` reload, `2901e` advance; object dispatch `65b4` | Update-count animation with asset-dependent periods; static classification, no calibrated explosion lifetime or asteroid rate from this flight tape |
| RNG `6f18.l`, saved seed `6f1c.l` | Generator `2cb56–2cb6e`, write `2cb66` | Call-driven; frame/action and modal consumers. Coast seeds match by update, not by elapsed time |
| VBL clock `7f02.l`; calendar origin `cfce.l` | Interrupt `34166`, origin `254ac`, display arithmetic `22c32` | Clocked. Calendar code divides elapsed ticks by 3300; this is not a simulation delta. No independent universal mission-seconds accumulator is established |
| Mission/nav progress including `949a`, system/mission `910e/910f` | `0260` checks every 32 updates, calls `061c→2124c` | Update/event-driven mission logic; full mission completion not exercised |
| Pause / active mode `0088.w` | Pause entry `0a76`, wait `0878` | Modal; measured: update/draw counters stay 110, all mapped world ranges and RNG freeze, no publication, VBL clock 744→754 |
| Autopilot mode `0088.w`, destinations/ship motion arrays | `101c–1472` sets mode 4; `1396→0e64` has a VBL deadline; `13e0` directly advances position | Mixed modal deadline and per-pass motion, not ordinary flight ticks. Static classification; actual fast-travel sequence needs a later live check |
| Return/landing animation, shared update/draw counters and cinematic motion | Return branch `1549c→1b8a8`; `1b948→1b2e6`; `1b394` increments draw on odd passes, `1b498` increments update each pass | Modal, per-pass animation; up to 100 iterations, skippable. Separate from normal integration. Static return/landing-path identification; not a measured landing duration |
| Menus and briefing | Front-end dispatcher `15348`, separate scripted sequence paths around `1c952` | Modal; no assumption that normal flight cadence applies; outside the flight tape |

The map identifies representative writers and cadence for each requested state
family. The phase-7b inventory and native reproductions below extend it. Runtime gaps
are live comms, missile locking, normal damage, autopilot, landing and full mission
progression; their classifications above are static evidence/hypotheses to check
when those paths are changed. Pausing demonstrably separates the interrupt clock
from the world counters, so replacing every counter with VBL time would be wrong.

Evidence: `tmp/phase7-coast-{020,repeat,delay,030}/`,
`tmp/phase7-observer-control/`, `tmp/phase7-combat-controls/`, their
`flight-report.json` files and `tmp/phase7-validation.json`. The corrected combat
capture supersedes exploratory control-key attempts. Derived binaries, complete
traces, snapshots and pictures remain ignored. Phase 7 stops at this documented
time-model/coupling gate. The phase-7b audit below is complete; timing design,
release and OCS work have not begun.


## Phase 7b: world-update dependency audit

The complete findings are [FR-01–FR-23](framerate-audit.md), with hunk/file-offset
notation, native fixture scope, clock-policy alternatives and implementation costs
under B/C/D. The gate covers the English CD32 world root `E:02a8`, its direct
calls and every dispatch entry, up to explicitly classified platform/resource
boundaries. It is not a claim of full live mission coverage.

The static closure has 30,384 instructions, 6,118 direct/selected-helper edges,
54 tables and 625 entries. Native 68000 and 68040 checks reach all 625 targets and
reject 104 out-of-bounds switch indices. The 47-entry ship-action table is
`D:0372` (executable file offset `3a3ba`), selected at `E:13d60`; its shared
elapsed/countdown word and phase byte are `D:c272/c288`, reset at `E:11620`.
There are no unidentified simulation callbacks. Copy/fill, formatting, runtime and
OS leaves are listed individually in the generated inventory; the external direct
edges are slave adapters `S:16fc/176a`.

Key refinements to the phase-7 map:

- Motion includes acceleration and angular feedback, not only final position.
  `E:807a–80e0` and complete angular update `7c86` reproduce call-count dependence.
  Existing position/velocity arithmetic retains eight fractional bits.
- Missile launch/guidance delay `D:baa8` is a signed byte (`E:77da/7808`), default
  20 at `ca9c`. Values 128–255 do not decrement through the positive-only gate.
  The native default expires at 0.8 seconds for a half-second 10→50 calls/s change,
  versus 0.4 seconds for 50→10. This is a timer fixture, not live missile duration.
- The original point-overlap routine `E:1597e` detects a controlled midpoint hit
  while missing both endpoints of a crossing step. The complete range/angle
  predicate `1187c` likewise admits or misses an equal-time approach according to
  sampling cadence. Both are synthetic native reproductions, not observed live
  collision or landing failures.
- Effect scripts `E:28f96` have their own update-count period, jump/removal opcodes
  and integer size growth. Damaged-ship emission at `65f4` instead reads the draw
  counter `D:9150`; keeping the world at 10 Hz alone does not remove that coupling.
- Communications animation `E:43e8` consumes the shared gameplay RNG `D:6f18`.
  Extra rendered portrait frames can therefore alter subsequent gameplay random
  values. Messages use draw counts; the six directional hit-indicator bytes
  `D:c4f4–c4f9`, set to four at `15ffc–1607a`, use world counts.
- The hardpoint byte at `E:ca12` is selected/disabled weapon state, with setters
  `1a5a2/1a5aa`; it is not a newly discovered gun reload timer. Gun energy recovery,
  firing opportunities and per-shot cost must be treated separately.
- The current/previous input latch `E:19334` is an explicit world/render hand-off.
  Reusing the native edge predicate's unchanged inputs produces five deliveries
  across five ticks; advancing the latch produces one. The camera command runner
  `18910` has a frame-count wait, but no general gameplay replay contract is proven.
- Landing writes the world counter directly at `E:1b498`, outside the ordinary
  root. Autopilot also has a VBL-deadline loop `0e64`; pause and modal transitions
  need explicit scheduling rather than accumulated catch-up work.

Steady 10/20/50/60 calls/s and both mid-run rate changes pass the current-defect
oracles on both models. Reset, byte/word bounds, lifetime sentinel, all effect
opcode families and rejecting mutation controls are included. VBL production and
per-event amounts are unaffected only in the scoped controls; they are not to be
wholesale rescaled. The installed Unicorn library mishandles an exploratory
high-bit memory logical-shift fixture at `E:790e`; the report records observed
`ffe0` versus expected `0020` after ten shifts. Positive-size timing results are
separate. No physical-CPU or performance claim follows from native execution.

Evidence: `tmp/phase7b-inventory-gate/` and `tmp/phase7b-native-verified/`, using the
retained `tmp/phase7-combat-controls/start-fast.bin`. Reproducible commands and
input/instrument fingerprints are documented in `development.md`. All derived
material remains ignored. Comms, player missile locking, ordinary damage,
autopilot, landing, full mission progression and gameplay-replay compatibility
retain explicit live/contract gaps. Phase 7b is complete at this audit gate;
phase 8, fixes, release and OCS work remain deferred.

## Phase 8: native-world price for the design decision

The [design comparison](timing-design.md) prices all eleven established cells in
Nav-1 held-fire combat. The root is `E:02a8` (file `02d4`), returning from the
call at `E:06b8` (file `06e4`) to `E:06bc` (file `06e8`). Draw returns at
`E:06c0` (file `06ec`); loop entry is `E:0698` (file `06c4`). Observer stack
checks verify the exact root return; cost includes every callee and any interrupt
preemption. Residual loop time includes input, HUD, drawing and waits, not drawing
alone. This closes the missing inclusive-world bracket without claiming complete
exclusive CPU/IRQ attribution.

Updates 10–39 exclude initial loading; frames crossing field-window stops are
excluded. All cells retain five ships and 17–23 active objects. Fourteen mapped
state ranges match by update number across the matrix; a fresh 020 repeat gives
identical selected state and costs. Root cost is 15.82 ms mean / 18.29 ms p95 on
cached 020, 20.78 / 23.75 ms uncached; the accelerated emulator cells range from
2.23 to 4.11 ms mean. At the native 10 Hz world rate the 020 reservation is
15.8–20.8%; at 25 Hz it is 39.6–51.9%. These are elapsed reservations including
preemption, not exclusive CPU utilisation or physical-hardware measurements.

The user selected D on 2026-10-13 because it retains most native world clocks while making the
player control/camera path responsive. Costs of its new per-render path and of
B/C conversion are not measured yet. Full IRQ subtraction, worst-case combat,
phase-6 renderer budgets and previously documented live gameplay paths remain
explicit gaps. The 10 Hz rate is inferred from native speed/displacement units;
the original world is frame-coupled. Bounded extrapolation is the initial
world-object presentation approach to validate, separate from authoritative
collision and lifecycle state. Phase 8 is complete; the selected policy is implemented below.

## Phase 9: decoupled simulation gate

The experimental `CUSTOM1=3` adapter replaces the ordinary loop entry `E:0698`
(file `06c4`) and returns to its original exit at `E:06c8` (file `06f4`).
It installs through `S:14da` (slave file `14fa`); option values 0/1/2 install no
new game patches. Pinned-input guards include relocated call targets and every
other displaced instruction operand before the first code write. Native installer
checks preserve the whole code hunk and registers/CCR with the option off and
reject a deliberately changed operand with no partial installation.

Phase 9 is complete for the separate English timing build. The final report is
`tmp/phase9-complete-verified-report.json`; the source fixture is
`tmp/phase9-flight-final-normal/`, with equal-size slow/one-field siblings.
The non-VERIFY candidate is `tmp/phase9-final-candidate/` (slave SHA-256
`0cc3c731c7a0b6de3e19e3281423ad1adee45a1ff6dd227c6491ae737f6ec5f7`).
It is not combined with the phase-6 renderer or packaged as a release.

Each capture has 20 windows of 100 fields; the first two are warm-up. Elapsed
seconds come from the observer's emulated cycle count and recorded base clock,
not host time or assumed exact PAL/NTSC rates. Complete world returns are counted
within the same measured VBL interval. Debugger detach events after the final
window are excluded. No exclusive instruction/DMA or physical-CPU claim follows.

| Final capture | Measured fields/s | World updates/s | Error from 10 Hz | Published pictures/s |
|---|---:|---:|---:|---:|
| `phase9-final-normal`, PAL 020, held fire | 49.92041 | 9.98963 | −0.104% | 6.60 |
| `phase9-final-slow`, PAL 020, ten-field draw floor | 49.92041 | 10.01738 | +0.174% | 3.39 |
| `phase9-final-one-field`, PAL 020, VERIFY wait replacing drawing | 49.92041 | 9.96188 | −0.381% | no drawing |
| `phase9-final-ntsc-020-turn`, NTSC 020, held turn | 59.82609 | 9.97656 | −0.234% | 7.48 |
| `phase9-final-pal-030-baseline`, PAL 030, held turn | 49.92041 | 9.96188 | −0.381% | 24.97 |

All five captures have zero input-history overflow. The beam classifier selects
50 or 60 as appropriate. These are scoped runtime measurements, not a new CPU
matrix or a claim of one-field rendering throughput. The diagnostic one-field
fixture replaces drawing with a field wait; its native world and input path run.

The 360 normal/slow and 359 normal/one-field matched world snapshots agree in
ship/projectile positions and velocities, forward vectors, classes, actions,
set speed, fuel, energy, shields, armour, targets and gameplay RNG. Whole-array
position/velocity residuals are limited to cosmetic debris slots 34–41; draw
counts differ as intended. Native regeneration `E:28c86–28f94` (file
`28cb2–28fc0`) scans slots 34–48 and creates replacement debris when presented.
Its private visual RNG and regeneration pictures remain render-dependent;
The phase-10 ownership policy below accounts for this presentation residual. No blanket state identity
is claimed.

The 030 publication snapshots contain **540 pairs within an unchanged world
counter with a changed player forward basis**. The forward camera matches that
basis, while collidable positions remain fixed. This is responsive input/camera
motion, not interpolation of old pictures. The slower 020 runs do not publish
extra pictures inside a tick; elapsed-field integration still feeds every world
boundary. Both PAL and NTSC native pauses freeze the mapped world state and
resume without accumulated paused time. Unread pre-pause active history is
explicitly discarded/counted; no such drop occurs in the uninterrupted schedules.

The shared accelerated emulator preset changed since phase 8. Its new data-cache
and indirect-UAE-board combination did not boot with the retained observer build.
The 030 capture explicitly selects the established phase-8 emulation setting
(`WC_BASELINE_CACHE_MODEL=1`, emulated data cache off). The effective configuration
and native CPU audit are checked; WHDLoad's original requested cache policy is
unchanged. This compatibility choice is confined to the measurement harness.

Input is not a pure device poll. `E:19330` copies input latches, polls devices,
runs `18daa` (steering ramps, throttle and held fire), maps rates at `0742`, and
processes pad/keyboard commands. The isolated player helper previews `18daa/0742`
with throttle calls at `18eee/18f00` and fire at `18f3a` suppressed, then restores
all changed native ramp/rate state. Tests cover all 64 combined-input masks at
five initial ramp values on both CPU models. The world data allocation is
unchanged by preview. The helper retains signed sub-angle remainders and applies
native pitch/yaw/roll routines `2acb2/2acf2/2ad32` in their original order; each
rebuilds the basis through `2bb30`. Signed unit-rate results at 50/60 Hz match ten
native rotations over a second. These are local native correctness checks only.

The helpers are connected through a VBL input history. `E:34188` (file `341b4`)
records native RAM after the existing clock/music callback, preserving its register
and CCR contract and replaying the displaced custom-register base load. The
producer uses the saved data-hunk pointer, not interrupted A4. A 64-record ring
publishes complete field-stamped pad/key samples; a full ring preserves unread
records, counts loss and forces a rebase. Native pad event latches transfer into
history. The consumer preserves pad transitions until a world tick and ORs event
pulses; native edge dispatch runs for each transition, then held controls/actions
run once. `E:1934c/18c6a/19380` (files `19378/18c96/193ac`) supply frozen pad/keys
and clip the native command FIFO at the captured producer cursor. Command bytes
remain in the native FIFO, including its original translation and 64-byte limit.

Each elapsed field previews the native steering controller and advances player
rotation with signed carried fractions. Only the world tick commits ramps,
throttle, firing and other commands. The world rotation hook at `E:7bc2` (file
`7bee`) excludes the already-integrated ordinary player. Other objects, scripted
player actions, death and external camera mode 8 retain native world ownership.
Ordinary forward/side/rear camera modes 0–3 refresh from the player basis via
`E:680e` (file `683a`); the script runner is excluded from these extra refreshes.
No collision, target lock, damage or lifecycle is extrapolated. At each world
boundary `E:2a086` (file `2a0b2`) refreshes native object/view geometry before
`E:3b8e` (file `3bba`) commits target selection. The latter's modulo-eight gate
uses the world counter; its draw invocation is suppressed. Input edges use the
last committed target, then automatic selection and held actions run at the new
boundary. Render-time aiming geometry cannot commit an extra lock or launch.

Pause uses the common entry `E:0878` (file `08a4`), covering relative as well as
absolute callers. Autopilot uses `E:101c` (file `1048`). Both disable sampling and
replay, discard/count unread active time, preserve native modal execution, and
rebase on return. The loop exit `E:06c8` precedes outer menu/landing transitions.
The retained pause run `tmp/phase9-history-pause-fixed-live-v2/` freezes all mapped
world state for 20 fields and resumes with 20 completions in the next 100-field
window, without the prior catch-up burst. CPU-only modal checks separately prove
ownership, elapsed-time exclusion and D0/CCR/stack preservation for both wrappers;
they do not claim a complete live autopilot or landing sequence.

Draw dependencies now have explicit owners:

- `E:65f4` (file `6620`) uses world-counter modulo four for damaged-ship emission
  inside the scheduled world; native/modal callers retain the draw counter.
- The draw call at `E:051a` (file `0546`) defers message duration to each world
  tick. The simulator transition tail at `E:0530/0536` (files `055c/0562`) likewise
  advances once per world tick, including its exit/position event. Score/time
  bookkeeping at `E:0438` (file `0464`) is also world-owned.
- `E:4b16` (file `4b42`) consumes elapsed world ticks for the cockpit indicator.
  Missed pictures are coalesced at the next draw; an expired visual selection
  transitions once and reloads natively, rather than replaying old pictures.
- `E:46ea` (file `4716`) defers subsystem fault/repair polling `af84` (file
  `afb0`) to the world tick. Its random trials and damaged-system writes are
  gameplay work even though the original caller is HUD drawing.
- `E:435c/43ee` (files `4388/441a`) use world parity and a private visual random
  value advanced on each tick. The original range routine advances a private seed
  and restores the gameplay seed. Repeated or skipped portraits cannot change AI
  randomness. The entire ordinary scene/HUD call additionally saves the gameplay
  seed, uses a separate rendering seed and restores gameplay state on return.
  This covers cosmetic star/debris regeneration as well as portrait draws;
  their pictures can differ across render schedules. Outside the ordinary loop
  original random consumers and targeting retain native behaviour.

Native component checks cover FIFO wrap, overflow, inactive producer, register/CCR
preservation, captured command boundaries, two pad edges between world ticks,
negative copy controls, and timer/RNG invariance across four draw schedules.
The final native checks are retained under `tmp/phase9-final-*check/`,
`tmp/phase9-flight-final-{install,input,modal}/` and the candidate check directories.
The unmodified reconstruction still matches the original slave SHA-256 exactly.

Remaining limits: native free/external camera mode 8 and scripted/death cameras
retain their original world cadence. World-object presentation is covered by the
phase-10 gate below.
Complete comms, missile-lock, ordinary-damage, autopilot/landing/campaign and
physical mouse/pad play-throughs remain release coverage. Native modal wrappers
prove the clock boundary, not every mission outcome. Original point-sampled
collision and integer world-effect quantisation remain unchanged. These are
explicit limits, not claims of completed release validation.

## Phase 10: renderer-only prediction gate

Phase 10 is complete in the separate English `--timing`, `CUSTOM1=3` build.
The non-VERIFY candidate in `tmp/phase10-isolated-candidate/` is 32,472 bytes,
SHA-256 `9f750132625a9a4d17622b80a8c89c6fcdfa23c3827fbebb0177242b7222c0eb`.
Original reconstruction remains byte-identical, and option values 0/1/2 install
none of the timing/presentation patches. This is not the combined phase-6 renderer
or a release package. Phase 11 flight conversion is recorded below.

### Ownership and correction policy

The common world exit snapshots all 64 native position/velocity slots, types,
models, lifetimes, angular steps and the ten ship actions. Rendering uses
`position + trunc(velocity * fraction / field_rate)`, with fraction taken from
the scheduler's residual debt and clamped to one world interval in the experimental
timing build. The buffered release uses the C1 display-time horizon below. Signed quotient
and remainder splitting avoids intermediate overflow and 64-bit division on 040.
A new picture starts from the authoritative pose, never from a previous prediction.
At a world boundary the latest authoritative state replaces the prediction;
there is no correction blend or persistent forecast debt.

Other objects' pitch/yaw/roll use the scaled native angular steps, in their native
order, through `E:2acb2/2acf2/2ad32` (files `2acde/2ad1e/2ad5e`). Their basis
rebuild `E:2bb30` (file `2bb5c`) retains native fixed-point orthogonality rather
than linearly blending matrix components. Player orientation remains phase 9's
elapsed-field result. Ordinary camera modes 0–3 are rebuilt from the staged
player pose; script/death/external-camera paths are not extrapolated.

First snapshots, modal rebases, view changes, changed class/model/action and
lifetime reloads snap. A per-axis change differing from the prior velocity by
more than four prior displacements plus 100 km is treated as a jump; arithmetic
overflow also snaps. A player jump suppresses prediction for the whole view.
The first interval after a cut is held until continuity is established again.
These are conservative presentation thresholds, not collision tolerances.

The original renderer consumes arrays in place. A 7,680-byte private save area
holds poses, velocities, allocation metadata and projection fields while the
native arrays temporarily contain renderer copies. All saved fields are restored
before input/world execution. The common-exit snapshot and per-slot validity mask
use another 2,388 bytes; these are slave storage, with no new Chip allocation.
Geometry is rebuilt from restored poses before edge commands and loop exit,
using `E:2a086` (file `2a0b2`), so predicted ranges cannot enter gameplay decisions.
Input interrupts only retain native input RAM; they do not run simulation against
staged poses. The complete save-range table is authored in `timing_scene.s`.

Native positions are `D:919a`, velocities `D:9d6c`, and basis arrays
`D:a148/b450/b750`, each with 12-byte entries. Slots 61–63 are camera/scratch
slots and are saved too. Class 2 stars are direction vectors and receive the
responsive camera rotation, not fictitious world translation. Other active
position-bearing classes are predicted; class 7 attachments use their parent's
projected pose. Explosion images, effect-script sizes/lifetimes and discrete
cockpit indicators retain their world-clock transitions. Their poses can move
between ticks without guessing new animation frames or lifecycle events.

Two native drawing side effects require explicit ownership:

- `E:28c86–28f94` (files `28cb2–28fc0`) regenerates cosmetic debris. A guarded
  eight-byte entry detour runs it once per world boundary with authoritative
  geometry and private visual RNG; the draw call is suppressed. Native modal
  callers retain the original body. Cosmetic random choices still share the
  private renderer stream, so cross-schedule cosmetic identity is not promised.
- `E:2914c–29304` (files `29178–29330`) creates class-7 engine flames in free
  slots through `E:29206 → 9af2` (files `29232 → 9b1e`). These are renderer-only
  attachments. Their native allocation, basis, model, lifetime/script and
  projection fields are part of the save/restore boundary. Additional pictures
  cannot retain a flame allocation into the world or consume free gameplay slots.

### Gate evidence and limits

`tmp/phase10-complete-scenes.json` checks 120 consecutive renderer snapshots and
post-draw restorations from each of two real-flight captures. Every predicted
position matches independent signed arithmetic; every saved range is restored
exactly. Within unchanged world ticks, authoritative positions, velocities,
classes, actions, fuel, energy, shields, armour, targets and gameplay RNG remain
unchanged. These breakpoint-separated pictures are correctness evidence, not a
frame-rate measurement. Published projection coordinates demonstrate movement
in the actual native drawing path, not just a standalone arithmetic test.

| Capture | Checked object predictions | Between-tick position / projected moves | Between-tick orientation changes |
|---|---:|---:|---:|
| `phase10-isolated-fire-pal`, 030, held fire | 2,920 | 1,624 / 476 | 28 |
| `phase10-isolated-turn-ntsc`, 030, held right | 1,997 | 1,124 / 440 | 185 |

Next-tick comparisons use uninterrupted object identities and exclude detected
cuts. Full-one-tick ship-position forecast error is PAL median 0, p95 1.987 km,
maximum 2.491 km (208 comparisons); NTSC hard-turn median 2.834 km, p95 4.357 km,
maximum 8.982 km (189). Constant-velocity classes 3/4/5/8 have zero observed error.
The 813 PAL and 245 NTSC comparable non-player basis forecasts match
the next native orientation (zero measured angular error). This is scoped
trajectory evidence, not a guarantee against future AI/controller changes.
Hard-turn positional correction can remain visible. These forecast-error numbers
cover one tick; they do not measure the extended C1 display-time horizon. Prediction
never alters collision or other authoritative results.

`tmp/phase10-gate-clock.json` covers the preceding uninterrupted 20×100-field
windows, excluding two warm-up windows. PAL measures 9.96188 world updates/s
(−0.381%) and 24.97408 publications/s; NTSC measures 9.97656 (−0.234%) and 29.92968.
Both have zero input-history overflow. The PAL native pause freezes mapped world
state for 20 fields and resumes with a rebase. These are standing measurements
of these workloads using the established 030 observer configuration, not exclusive
CPU/DMA, speedup or physical-hardware claims.

Native 020/040 checks cover 96 pose/isolation cases, 300 signed scaling cases
including longword extremes, four ordinary camera views, native axis equivalence,
script/death/external/disabled cuts, jump/reuse detection and whole-data restoration.
Two additional cases execute the real flame allocator and restore the entire data
hunk exactly. A corrupted saved position is rejected. Separate corrupted prediction
and restoration captures fail the live report. Installer guards, 664 player cases,
126 input records/edge controls, eight modal cases and timer/RNG ownership pass.
Evidence is in `tmp/phase10-final-{native-check,ownership,modal,player,input}/`,
`tmp/phase10-isolated-install/` and `tmp/phase10-report-negatives.json`.

The two flights exercise classes 3/4/5/8/12, temporary class-7 flames and ordinary
forward-camera movement. Every asteroid/model, effect script, scripted camera,
mission transition and physical-device combination has not been played through.
No visual-quality claim comes from a debugger-greyed display. Flight conversion is integrated in phase 11. Unified intro/flight options,
full campaign and hardware play-testing remain release coverage; they are not a
reason to expand this phase into a new performance matrix.


## Phase 11: flight rendering gate

The measured phase-7 profile selects conversion as the useful second rendering
pass: 64–66% of representative 020 instruction cost is in the existing converter,
versus about 8% in drawing; observed chunky changes are only 0.03–1.4% per picture.
The implemented change scans the complete source but converts only changed
32-pixel blocks. It covers the view, cockpit, text and HUD without assuming a
fixed cockpit rectangle or suppressing their native drawing.

### Implementation and boundaries

The normal `--timing` build adds a four-byte detour at `S:178a` (slave file `17aa`)
to `S:7eb8` (file `7ed8`). This replaces the original register save, which the
wrapper performs itself. The existing phase-9 PatchSeg detour at `S:14da` (file
`14fa`) remains. Reconstruction verifies every other original slave byte. No new
game-hunk patch is added in phase 11. English `CUSTOM1=3`, active flight, width
320 and height 200 are all required; inactive flight and other geometries invalidate
both destination records before the original path. Options 0/1/2 keep the original
converter. The original cache request and `Custom5=0–3` limiter stay in place;
this does not yet merge the phase-6 intro cache/converter policy into release options.
`Custom5=4` bypasses the software-converter seam and is outside this gate.

The history pointer is `S:8048` (file `8068`); destination records and their order
are `S:804c/8054` (files `806c/8074`). Startup `S:8056` (file `8076`) allocates
128000 bytes with `MEMF_FAST|MEMF_PUBLIC|MEMF_CLEAR`, before the game claims its heap.
Failure selects the original path. Each of the two planar destinations has its
own 64000-byte last-source image. A first or replaced destination always receives
a full original conversion and source copy. This avoids comparing a back buffer
against the previous picture rendered into the other buffer.

`S:7f6c` (file `7f8c`) compares eight longwords per block. Changed blocks copy
those 32 bytes into history and use an immutable 32-pixel specialization of the
pinned Kalms 030 transform at `S:8082` (file `80a2`), with the actual 8000-byte
plane stride. No code is copied or self-modified. Unchanged blocks issue no planar
stores. After conversion, WaitBOVP protects reuse at the existing single swap and
publication path. There is no new CHIP allocation in the normal build.

The sampled flight source is already FAST, as are the game hunks; the destinations
are CHIP. There is no evidence justifying a blanket drawing-memory patch or
rewrites of the smaller drawing/math buckets here. Native clears remain necessary:
the earlier blanket-clear experiment failed because later work reads their pixels.
Ship scaling, polygon/span, starfield, HUD and text algorithms therefore remain
native. No independent savings in those routines or DMA slots are claimed.

### Output and timing evidence

Native 020/040 checks pass **72 complete output comparisons per build**, for both
normal and twin builds, against the existing converter plus independent pixel
packing. Alternating/replaced buffers, no-change frames, sparse/dense changes,
geometry and active-state transitions, option-off, allocation failure, source
integrity, write bounds and preserved registers are covered. A corrupted planar
byte in an otherwise unchanged block triggers the live twin's abort on both
CPU models. Installer guards/option-off checks and phase-10 native prediction,
whole-data restoration and real flame-allocation cases also pass.

The live twin converts the same source with the original routine into a separate
64000-byte CHIP reference and compares every output longword. Both sides thus
write the same memory class. The accepted runs verify **130 firing pictures on
030 and 40 turning pictures on 020**, with zero output differences. First-use
full conversions and any unfinished final comparison are excluded from pricing.

| Emulator workload | Measured pairs | Original mean / p95 ms | Delta mean / p95 ms | Mean time reduction |
|---|---:|---:|---:|---:|
| 030 established MMU/cache model, held fire | 128 | 15.511 / 16.304 | 3.098 / 4.464 | 80.0% |
| 020 stock multiplier/cache model, held right | 38 | 67.336 / 68.661 | 22.552 / 35.045 | 66.5% |

Candidate maxima are 5.940 / 35.607 ms; original maxima 16.536 / 68.968 ms.
These are read-only observer elapsed-cycle brackets on the retained phase-7
emulator, including interrupts within each interval and excluding limiter,
comparison and display wait. The candidate includes history lookup/comparison;
the original bracket contains the native converter alone. They establish a scoped
conversion saving, not exclusive CPU cost or physical-accelerator performance.
`tmp/phase11-conversion-final.json` records distributions, memory-class checks,
fixture/emulator hashes and capture hashes. A preliminary FAST-reference timing
is not used for the accepted equal-memory comparison.

The **normal**, non-twin 030 flights retain 9.96188 world updates/s in PAL
(−0.381%) and 9.97656 in NTSC (−0.234%), with zero input overflow. Publication
rates are 24.97408 / 29.89642 per second under the retained limiter. Thus no FPS
increase is claimed. The PAL 20-field pause freezes mapped state and resumes.
Forty post-window turning pictures check 628 predictions, 116 between-tick
projected moves, native orientation forecasts and exact restoration of every saved
range; corrupted prediction/restoration controls are rejected. This confirms that
conversion integrates with the phase-10 presentation boundary.

Normal candidate: **33560 bytes**, SHA-256
`80a94f84f0a7d357cbb7bd0bbcf526856105cc2d006603276a1896a15d520266`.
A fresh source build reproduces it exactly; default reconstruction remains identical
to the pinned original. Evidence and commands are in
[development](development.md#phase-11-flight-conversion).

Phase 11 is complete within this measured flight scope. Dense whole-screen changes
can make the per-block approach slower; no universal all-scene/NoCache/040/060
speedup is promised. Full campaign, every ship/asteroid/camera/effect, transitions,
small-memory configurations and physical-hardware visual checks remain phase-12
coverage. The earlier hard-turn prediction correction and unified intro/flight
options remain documented release work. No release or OCS work starts here.

## Phase 11b: measured frame budget (A1–A3)

### A1 instrument

The `--frame-stats` diagnostic build records 15 frame-part events in the slave.
Each records the game's VBL count (`D:7f02`) and the beam line. It saves 16384
records through WHDLoad, so it does not depend on the emulator core or a debugger.
The normal timing build stays byte-identical to the phase-11 candidate. In flight,
`$510` does the native drawing, then calls the converter (limiter, conversion,
WaitBOVP) and publishes. `$46e6` runs after publication.

The gate passes on the established 030 model with held fire
(`tmp/a1-030-observer-fire/check.json`). For every displayed field, the number of
recorded pictures equals the observer's publications at `E:3378e`, apart from
three pictures published on the last line of a field. The recorder flags those as
ambiguous by one field. Recorder and observer elapsed time agree to 0.0 ms over
30.5 s (PAL line 227/3546895 s, 313 lines). Samples in the first lines of a field,
taken before the game's VBL handler has counted it, are corrected by one field;
the report lists how many.

### A2 status: no credible 040 or 060 model

No emulator configuration available here models those CPUs. The real-hardware
reference is still missing:

- The shared non-cycle-exact 040 and 060 presets run at a fixed multiplier (8).
  Their records differ only in noise: 49.09 pictures/s and an identical
  distribution.
- On the cycle-exact 040 core, cache state makes no difference: CACR `00000000`
  and `80008000` give the same results.
- `cpu_speed=max` is slower than `real` in these runs (39.95 against 49.09
  pictures/s), so it is not an upper bound.
- The shared presets' emulated data cache requires the indirect UAE board, and
  this fixture does not boot with it, using either the shared or the debugger
  binary. All accelerated cells use the phase-8 compatibility setting (emulated
  data cache off, no indirect board).

The recorder runs unchanged on real hardware with `NOWRITECACHE`; that is the
route to a calibrated 040. With Psygore's cache request and no WHDLoad option,
the 040 runs with CACR `00000000` (caches off). This emulator does not model the
cost; real hardware would.

### A3 baseline

Nav-1 combat, no input except the observer run (held fire). There are 1166–1416
measured frames per cell after 20 warm-up frames. "Busy" is frame time excluding
the limiter and the post-conversion display wait. Times are emulated elapsed time
and include interrupts. Report: `tmp/a3-report.json`.

| Cell | Custom5 | Pictures/s | Fields per picture | Busy p50 / p95 ms | Limiter / display wait ms (mean) |
|---|---:|---:|---|---:|---:|
| 020 stock, cycle-exact | 1 | 10.75 | mostly 4–5 | 86.6 / 99.3 | 0 / 8.1 |
| 030/50 cycle-exact | 0 | 24.96 | all 2 | 12.5 / 19.8 | 11.2 / 14.1 |
| 030/50 cycle-exact | 1 | 49.92 | all 1 | 11.8 / 17.7 | 0 / 7.1 |
| 030/50, held fire (A1 run) | 1 | 46.80 | 1315×1, 94×2 | 13.4 / 22.0 | 0 / 6.1 |
| 040 shared preset | 0 | 24.96 | all 2 | 12.5 / 25.1 | 11.6 / 12.1 |
| 040 shared preset | 1 | 49.09 | 1390×1, 24×2 | 11.7 / 21.8 | 0 / 6.8 |
| 040/25 cycle-exact core | 0 | 24.96 | all 2 | 16.3 / 30.3 | 7.3 / 12.1 |
| 040/25 cycle-exact core | 1 | 39.95 | 1053×1, 350×2 | 15.9 / 29.7 | 0 / 6.4 |
| 060 shared preset | 1 | 49.09 | as 040 shared | 11.7 / 21.8 | 0 / 6.8 |

The world rate is 9.96–9.98 updates/s in every cell.

Findings:

- `Custom5=0`, Psygore normal, holds every accelerated cell at exactly
  24.96 pictures/s. Frames need 12–16 ms of work and then wait out two fields.
  Turning the limiter off gives 40–50 pictures/s on the same models.
- The remaining drops come from frames that carry a world tick. On the 040
  cycle-exact core, frames without a tick need 15.7 ms (p95 16.6). Frames with a
  tick need 26.6 ms (p95 31.2), of which the world update is 5.8 ms (p95 8.8); the
  rest is tick-time input, geometry and targeting work. On the 030: 11.6 against
  17.3 ms, world 2.8 ms.
- The post-conversion WaitBOVP idles 6–7 ms per frame even unlimited. When
  conversion ends after the bottom of the display, the picture is published in
  the next field and replaced before display (3 of 1413 in the held-fire run).
- Per-frame parts on the 040 cycle-exact core (mean ms): prediction save 0.6,
  native drawing 6.8, conversion 4.5, after-publication `$46e6` 3.6, restore 0.3.
- None of these configurations reproduces the user's below-25 report with
  standard pacing; all hold exactly 25. A slower emulated CPU or modelled
  cache-off cost would produce it.

## Phase 11b: public modes and uncapped flight (B1 gate complete)

The public-option candidate (`reconstruct.py --variant cd32 --release`) uses language-only
CUSTOM1 (0 English, 1 German). CUSTOM5 defaults to 0: enhanced English, or
Psygore normal for German until that port exists. Values 1–4 translate to
Psygore's original 0–3 (normal, unlimited, relaxed, slow), retaining his simulation,
converter and cache request. The blitter option is removed. Values outside the
public ranges abort before language loading. The separate experimental builds
retain their original options; normal `--timing` is still byte-identical to the
phase-11 candidate.

Public-option translation enters at `S:1422` (file `$1442`) before language
selection at `S:142a` (file `$144a`). English+enhanced maps internally to mode 3;
all other choices keep language 0/1 and cannot install the English timing patches
at `S:14da` (file `$14fa`). Enhanced mode uses the existing zero-mask SetCPU query,
preserving WHDLoad policy; it does not enable caches. The header's name, info and
configuration pointers at `S:24/28/32` (file `$44/48/52`) identify the candidate
and its new public options. Version remains **2.0b (13.06.2026)**.

At conversion entry `S:178a` (file `$17aa`), enhanced active flight bypasses
Psygore's TOD limiter `S:17b8` (file `$17d8`). This applies both to changed-block
conversion and full-conversion fallback when history allocation is unavailable.
Inactive/nonflight enhanced conversion still calls the normal limiter. B2 below
now replaces the flight WaitBOVP with queued early-blank presentation and a
pre-conversion ownership wait. The reported horizontal-row glitches remain open.

In the normal B1 artifact, authored entries are `release_setcpu` at `S:1e0c`
(file `$1e2c`), `release_limit` at `S:1e4e` (file `$1e6e`), flight entry at
`S:80c0` (file `$80e0`) and full-renderer entry at `S:84f4` (file `$8514`).
These appended offsets belong to the exact build below, not diagnostic builds.

Native evidence:

- 196 language/mode/cache cases cover accepted and rejected values on 020/040
  models. Enhanced queries preserve policy; Psygore choices retain the original
  request. All four shifted pacing values and the German default are covered.
- 180 pacing/output cases execute both converter paths, three heights, active
  and inactive flight, missing/failed/allocated histories, and both languages'
  original modes. Limiter calls are counted with a TOD stub; complete pixels,
  source/register preservation and write bounds are checked.
- 54 additional full-converter outputs and 72 changing/reused/replaced-buffer
  outputs match the independent planar oracle (the latter also execute the
  original converter). Eight installation cases preserve the complete code hunk
  and registers/CCR according to the existing option-off/install contract.
- Wrong mode translation, uncapped nonflight and capped flight fallback each
  fail the new gate. The normal candidate contains no recorder or VERIFY symbols.
  Fresh original reconstruction is byte-identical to the pinned original.

The diagnostic recorder needed a correctness fix: a 040 capture showed beam
lines 255, 0, 260 within one VBL interval, consistent with a torn VPOSR/VHPOSR
longword read at the 255/256 boundary. The existing monotonicity check rejected
that capture. Two agreeing beam-line reads now guard the sample; six native
race/register/CCR cases and a deliberately broken single-read control pass.
No normal-build instructions changed for this fix. The corrected 030 recorder
matches the independent observer on all 1437 pictures/fields, with zero elapsed
time difference and no ambiguous pictures.

Final frame gate: PAL, Nav-1 combat without held input, 8 MiB FAST, diagnostic
recorder, retained observer SHA-256
`08360549c392f07b1fb3393bf1e071cd0bd5ffcb4048f229d528a1ce628c1313`.
The established compatibility setting disables the emulator's indirect board and
emulated data cache; WHDLoad's cache choices and live CACR are recorded separately.

| Emulator model | WHDLoad options / CACR | Pictures/s | Fields/picture histogram | World updates/s |
|---|---|---:|---|---:|
| 030/50 cycle-exact | CACHE DCACHE / `00002111` | 49.920 | 1415 × 1 | 9.979 |
| 040/25 cycle-exact core | NoMMU / `00000000` | 39.953 | 1053 × 1, 350 × 2 | 9.983 |

Both have zero limiter wait. The remaining mean display wait is 7.1/6.3 ms,
respectively. These are scoped emulator end-to-end measurements, not calibrated
040 hardware results or a universal 50 FPS guarantee. A preliminary 030 capture
without cache options (CACR `00002000`) reached 39.908 pictures/s, histogram
1051 × 1 / 352 × 2, world 9.975/s; its valid original-recorder data is retained
separately and is not a matched performance comparison with the final fixture.
The first 040 boot without the established compatibility setting did not reach
flight and was stopped; neither it nor the rejected timestamp capture is a pass.

Normal slave: 38404 bytes, SHA-256
`dc8e64ffdc39bb624909c47bbbeff8af2fc488dfbb745a6bcfe2e040441986cb`.
Final direct-flight diagnostic SHA-256:
`0bc7e1bfb6490c4fced387a867b1f897607c2e8b02898ac2cf340a3c043726cc`.
Evidence: `tmp/b1-final-native.json`, `tmp/b1-flight-native.json`,
`tmp/b1-install/`, `tmp/b1-recorder-native.json`, `tmp/b1-030-gate/check.json`,
`tmp/b1-frame-gate.json`, and the two `tmp/b1-{030,040core}-gate/` captures.
Commands are in development's B1 section; the public numbering/fallbacks are in
`release/ReadMe`. Save-file work remains outside this gate. German live campaign,
full control/visual acceptance, calibrated 040 performance and release packaging
remain open. The subsequent B2 and C1 gates are below; C2 is complete below; C3 and later work remain open.

## Phase 11b: deferred buffer reuse (B2 gate complete)

The public enhanced-English build retains two CHIP buffers. It finishes a
conversion, queues its completed index, and continues the next world/player and
FAST chunky drawing work immediately. Before either full or changed-block
conversion, it waits only if the previous swap is still pending. The post-conversion
flight WaitBOVP is removed. Nonflight retains normal pacing/WaitBOVP, and Psygore
modes retain their native publication and converter paths. No third buffer or
additional normal-build allocation is introduced.

The request/acknowledgment path follows the buffer-ownership approach in Their
Finest Hour, adapted to this game's OS-generated COP2 lists. Main writes the
index, saved game A4 and planar pointer before publishing a word-sized pending
flag. The VBL callback performs native View/BitMap/COP2LC bookkeeping, restarts
COP2 in early blank, records the new front, then clears the flag. A request remains
pending if the native publication lock is busy or the interrupt arrives late.
Native teardown drains pending work before freeing the View/lists. Pending work
is serviced even if flight has become inactive, preventing a pause/modal drain
from deadlocking. Native main/IRQ register contracts are checked separately.

Game seams (code hunk / executable file):

| Seam | Purpose |
|---|---|
| `E:3378e` / `$337ba` | Queue active-flight publication; inactive calls displaced native publication |
| `E:337ea` / `$33816` | Drain before native viewport teardown |
| `E:34188` / `$341b4` | Service presentation before the existing input-history callback |
| `E:33a12` / `$33a3e` | Unchanged native index/View/BitMap publication called by the IRQ |
| `E:33ce2` / `$33d0e` | Unchanged COP2LC store inside that native helper |

All new game seams have pinned original-byte guards and install only for enhanced
English. Native trampolines resume at `E:33796` / file `$337c2` and `E:337f0` /
file `$3381c`. In the normal B2 artifact, authored entries are queue `S:81a4`
(file `$81c4`), conversion wait `S:8202` (file `$8222`), teardown `S:8210`
(file `$8230`), VBL service `S:822a` (file `$824a`), and post-COPJMP2 marker
`S:8274` (file `$8294`). These appended offsets are build-specific.

The copper deadline is checked against actual lists. The pinned KickEmu 3.1
copinit has 38 initial register/sprite MOVEs, then waits at line 12 and jumps to
COP2. The IRQ lets that initialization finish by waiting until line 4; it begins
native publication no later than line 12 and strobes COPJMP2 only by line 16.
A late completion keeps the buffer unavailable until another VBL. The captured
559-instruction game lists finish setup before display starts at PAL line 72 or
NTSC line 44, even charging four colour clocks per instruction. Both lists use
FMODE 3 and eight correctly spaced planes. This gate covers these pinned
KickEmu lists, not arbitrary replacement display systems.

### B2 correctness and instrumentation

Native checks on 020/040 cover early/torn/late beam reads, late completion after
bookkeeping, lock contention, one acknowledgment per request, blocking reuse,
inactive service, teardown drainage, and native publication/teardown live-out.
Deliberately permitting early reuse or removing COPJMP2 fails. The 196 option/cache
cases, 180 pacing/output cases, 54 full-converter outputs, 72 changing-buffer
outputs and whole-game-hunk installation checks pass. Original reconstruction
and the standalone experimental timing build remain byte-identical to their
previous references.

Displayed frames are measured with a separate IRQ-owned ledger, not inferred
from main-loop publication requests. It records actual field/line, index, planar
pointer and copper pointer. Main-frame records and the display ledger share the
original **65552-byte diagnostic FAST allocation** (8192 main records and up to
2047 display records); normal builds include neither. This budget is native-tested.
An initial larger diagnostic allocation pushed the chunky source into CHIP and
produced a false rendering regression; those captures are rejected. The live gate
now requires a FAST source and two aligned CHIP destinations.

The observer comparison uses the recorder's exact epoch, read from its saved
state, rather than choosing an offset from a repeating one-frame-per-field pattern.
For each accepted run, all displayed frames match the independent post-COPJMP2
observer; elapsed time differs by less than 0.002 ms. All 1987 observed converter
entries target the buffer other than the current front. Every observed handoff
is at line 4; late deferrals and input-history overflows are zero. The diagnostic
also aborts if a converter is about to touch the front buffer. The NTSC three-field
screen sample was inspected; this is not full visual acceptance or closure of the
user's horizontal-row report.

### B2 frame gate

Nav-1 combat without held input, 8 MiB FAST, retained observer with the established
cache-model compatibility settings. The 030 uses CACHE DCACHE (CACR `00002111`);
the cycle-exact 040 core uses NoMMU (CACR `00000000`) and remains **uncalibrated
against real 040 hardware**. Figures describe these diagnostic emulator windows.

| Model / video | Displayed pictures/s | Fields/picture histogram | World updates/s | Mean pre-conversion ownership wait |
|---|---:|---|---:|---:|
| 030/50 PAL | 49.920 | 638 × 1 | 9.925 | 7.6 ms |
| 040/25 core PAL | 49.920 | 638 × 1 | 9.929 | 2.2 ms |
| 030/50 NTSC | 59.826 | 642 × 1 | 9.955 | 4.3 ms |

These ~11–13 s windows meet the scoped display-rate gate and 10 Hz ±1% world gate.
Waits occur before planar writes after the next chunky picture has been drawn;
there is no flight post-conversion wait. Main-loop work intervals still vary
(world-tick frames remain heavier), so C4 is not closed by the regular displayed
cadence. C1 display-time prediction and C2 player translation are complete below.
C3 heading-aware prediction, long missions, physical hardware and user visual acceptance remain
open. No claim that all movement now feels like the display rate is made.

Normal slave: 38916 bytes, SHA-256
`65de422bd4f161b97e3ae208dd4249b81fe2bb551a08a7de1e0574bc743c2830`.
Diagnostic direct-flight slave SHA-256:
`2163e8f139acce712e58fffbba08f32b4dc731334719595f2448056b7d661b8e`.
Evidence: `tmp/b2-buffer-final.json`, `tmp/b2-options-final.json`,
`tmp/b2-pixels-final.json`, `tmp/b2-install-final/`,
`tmp/b2-recorder-budget.json`, `tmp/b2-final-gate.json`, and
`tmp/b2-{030,040,ntsc}-gate/{check,buffer-check}.json` with the raw ledgers,
observer events and memory samples. Commands are in development's B2 section.
B3's no-third-buffer constraint is retained; the C1 gate follows below.


## Cached 040 display corruption: emulator MMU write attributes

The horizontal-row corruption reported with B2 is reproduced with the unchanged
release slave (`65de422bd4f161b97e3ae208dd4249b81fe2bb551a08a7de1e0574bc743c2830`).
The pinned FS-UAE core has six incorrect MMU ATC hit paths in
`src/include/cpummu.h`: ordinary and locked byte/word/long stores translate using
`atc_data_cache_write`, then take cache attributes from `atc_data_cache_read`.
Independent read-entry replacement can therefore apply copy-back attributes to a
CHIP store whose actual MMU descriptor is write-through. The CPU sees correct
planar pixels while display DMA reads stale physical CHIP bytes. `ChipNoCache`
alone does not resolve this emulator defect.

A local emulator correction takes both address and attributes from the write
entry. No slave change, per-frame flush or disabled cache is required. The
project launcher selects this correction for its default 040/060 emulator; an
explicit `FSUAE` override remains available. The shared installation is untouched.

The read-only instruction-loop observer samples after conversion at code-hunk 0
`$31ff2` (English file `$3201e`), decoding all eight planes independently against
the chunky source, through both CPU-cache and physical-DMA views. It stops the
intro at hunk 3 `$de0`, the Origin FX fade entry, and requests a normal frontend
screenshot. No GDB stops, profiler, guest writes or cache flushes intervene.
Python independently decodes the saved snapshots. Earlier debugger/profiler
captures did not expose this cache failure; they are insufficient acceptance
instruments for it.

The unfixed full-intro control had 259 bad DMA conversions out of 306, with zero
CPU pixel mismatches; a ChipNoCache control still had 257. The corrected emulator
passes all 306 conversions with zero CPU or DMA pixel mismatches. CACR remains
`$80008000` (both caches enabled). Evidence lives in
`tmp/glitch-audit-cached-v2`, `tmp/glitch-audit-chipnc`, and
`tmp/mmu-intro-verified`. The corrected frontend Origin FX capture has no visible
row corruption. The direct Nav-1 flight fixture also passes 120 full-height
(320×200) conversions with zero CPU/DMA differences and both caches enabled;
its frontend cockpit capture is clean (`tmp/mmu-nav1-check`). The fixture hash is
`2163e8f139acce712e58fffbba08f32b4dc731334719595f2448056b7d661b8e`.
The reproducible matched-source negative control, built with only the six-line
correction omitted, fails 19 of its first 20 intro conversions
(`tmp/mmu-control-check`); its CPU pixels still match.
These are correctness observations, not performance measurements.

The correction covers all six affected write paths, but live acceptance here is
040-specific. Broader campaign/modal coverage, 060 validation and real-hardware
acceptance remain open. C1 is complete below; phase 12 remains deferred.


## Phase 11b display-time prediction: C1 gate complete

The buffered release's scene entry now predicts from the last consumed field to
`current field + 1 + pending swap`. It retries a clock read if an IRQ changes the
field mid-snapshot. The numerator is `residual debt + 10 × (target − consumed)`;
the denominator remains PAL 50 / NTSC 60. The release publisher at `E:3378e`
(file `$337ba`) copies target, source clock, debt and selected numerator into
IRQ-owned request metadata before publishing the pending flag. A later render
cannot overwrite those values. The IRQ never displays a future target early.

The existing pose snapshot/restore and cut rules are unchanged; prediction still
cannot affect simulation, targeting, collision or gameplay RNG. The queued delay
requires prediction beyond the next world boundary: its bounded maximum is now
one tick plus two fields (140 ms PAL / 133.3 ms NTSC). The tested steady pipeline
uses two-field lookahead, reaching 120 ms PAL / 116.7 ms NTSC. Clipping to the old
one-tick limit would repeat the final phase; C1's gate requires the full actual
display-time fraction instead. Longer overruns retain the cap, and late blank
publication still defers safely; such misses fail the C1 checker rather than being
silently counted as correctly timed pictures. Arbitrarily slow frames and locked
modal transitions are not claimed to meet this scoped flight gate.

The `--frame-stats` display ledger has 32-byte entries: the original field, line,
index, planar and copper fields plus target field, consumed field, residual debt
and prediction numerator. Both clock fields are relative to the recorder epoch,
with wrapping subtraction. `display_time_check.py` independently computes the
expected numerator from the actual displayed field, requires all steady phases,
and rejects wrong-fraction and wrong-target negative controls. The independent
A1 publication observer and B2 ownership/copper checks remain separate gates.

| Model / window | Displayed pictures checked | Prediction errors / missed targets | Pictures/s | World updates/s |
|---|---:|---:|---:|---:|
| 030/50 PAL, established cache model | 661 | 0 / 0 | 49.920 | 9.926 |
| Cycle-exact 040 core PAL, NoMMU | 661 | 0 / 0 | 49.920 | 9.929 |
| 030/50 NTSC, established cache model | 665 | 0 / 0 | 59.826 | 9.956 |

All three windows have one displayed picture per field, publish at line 4, retain
two CHIP buffers and one FAST source, and have zero input overflows or late
blank deferrals. The 040 core remains uncalibrated against physical hardware.
Evidence: `tmp/c1-final-{030,040,ntsc}` and `tmp/c1-final-fps.json`.
A fourth, uninterrupted cached-040 run uses the corrected shared `FSUAE_MMU`
with `CACHE DCACHE`, the indirect UAE board and data-cache emulation enabled.
All 661 predictions match, with zero missed targets; its recorder measures
49.920 pictures/s and 9.928 world updates/s. It uses no debugger or
read-only publication observer, so its independent-observer coverage comes from
the three model gates above. Evidence: `tmp/c1-final-cached040`.
Native checks cover 176 target/queue/wrap cases and two forced IRQ races on
020/040, 96 scene/restore cases, 420 signed arithmetic cases through the extended
horizon, recorder torn-read controls, publication locks/late IRQs, 196 option/cache
cases, 180 pacing cases and 54 complete converter outputs. Earlier C1 native
converter and installer checks also pass; they exercise unchanged routines.

Normal slave: 39044 bytes, SHA-256
`6c4efafbf982288a63df5abb1d36a9ebdf4287249bdfd7953edf7ca799ed070b`.
The direct-flight recorder is `tmp/c1-final-frames`; its build manifest pins the
fixture after startup-argument adaptation. The diagnostic ledger allocation is
now 98304 bytes and remains outside the game's declared memory budget.

C2 player translation is complete below. Angular/velocity forecasting quality,
visible hard-turn corrections, long missions and hardware calibration remain open. The
old phase-10 one-tick forecast-error measurements do not establish error bounds
for the newly extended horizon. Release work remains paused.


## Phase 11b player translation: C2 gate complete

Controlled English flight now commits player velocity and position once per
elapsed field, after that field's rotation. World ticks retain fuel, action timers,
throttle commands, collisions and other objects; they do not move the player a
second time. C3 heading-aware forecasting is recorded below. Phase 12 stays paused.

### Native model and patch seams

English code-hunk 0 file offsets are `E + $2c`. Data offsets below are relative
to the data hunk, not loaded addresses. Player position is `D:919a`, velocity
`D:9d6c` (fixed8 displacement per world tick), forward basis `D:a148`, set speed
`D:99be`, and the camera position is slot 61 at `D:9476`.

Native `E:7d1a` (file `$7d46`) mixes motion with gameplay effects. Ordinary desired
velocity is forward × set speed / 256 through `E:2b7f0`. Afterburn action 1 uses
`(2 × model.word(+22) + 40) << 8`; braking action 3 requests zero. The model index
is `D:97f6`, with 104-byte records at `D:53a4`. Action expiry at `E:7e10` consumes
`D:bb14` and returns to ordinary thrust. Active burn/braking fuel charges are
200/140 through `E:15900`; ordinary fuel remains at `E:cb78`.

The field wrapper reuses the original acceleration solver `E:7f78–8078`
(file `$7fa4–80a4`) with its native local-frame ABI. It retains the engine capability
from `E:15848`, engine condition, flag query at `E:29f94`, alignment calculations,
and doubled action-1/3 acceleration. It restores the cosmetic effect byte at
`D:bae8`; no fuel, timer, RNG or other game-data changes escape the field wrapper.
Two guarded six-byte jump seams replace the velocity add entry `E:807a`
(file `$80a6`) and position add entry `E:80b6` (file `$80e2`). The actual vector adds
are at `E:809a` and `E:80e0`; the original epilogue is `E:80ea`.

Each axis carries signed remainders for both acceleration and displacement:
`step = trunc((native increment × 10 + carry) / field Hz)`. Six independent
remainders survive render-frame grouping and reset on timing rebase or loss of
controlled flight. The implementation splits quotient and remainder before
multiplication to avoid 32-bit overflow. Eligible states are player type 12,
ordinary camera, no script, and actions −1/1/3. Other objects, external camera,
scripted states, unsupported actions and non-world native calls retain native
motion. The scheduled world still records its acceleration scratch at `D:bb2c`.

`E:2a8` dispatches collision/gameplay `E:76e4` before object motion `E:7b4e` and
camera rebuild `E:680e`. These routines therefore see the already committed
field pose. Render-only player translation forecasts from that pose using current
velocity and only the remaining one/two-field display lead; it does not add the
world residual debt twice. Full scene restoration prevents that future pose from
reaching collision or gameplay code. Collision cadence remains 10 Hz; high-speed
swept collision and whole-campaign equivalence are not claimed.

### Native correctness and tolerances

`translation_check.py` executes the original native solver as the per-field
oracle on identical state. Across 020/040 and PAL/NTSC, 28 two-second trajectories
cover steady flight, acceleration ramp, ordinary braking, action-3 braking,
turning, afterburn and afterburn turns (3080 fields, 560 ticks). Fractional velocity,
position and carry match exactly. Field writes are confined to player position
and velocity; world bookkeeping matches the native routine byte-for-byte after
excluding those intentionally retimed vectors. Fuel, action and timer differences
are zero. Native camera rebuilds introduce no tick correction.

A separate original 10 Hz trajectory quantifies the change from finer integration:

| Trajectory | Maximum speed difference (km/s) | Maximum position difference (km) |
|---|---:|---:|
| Steady | 0 | 0 |
| Ramp | 7.461 | 13.555 |
| Ordinary braking | 3.867 | 9.078 |
| Turn | 0.789 | 31.109 |
| Afterburn | 31.016 | 44.336 |
| Afterburn turn | 30.449 | 52.697 |
| Action-3 braking/expiry | 48.008 | 20.442 |

The regression allowances are 5% of the initial/set/burn speed envelope and 10%
of two seconds' travel at that envelope, with exact fuel equality. Action-3 expiry
has a separate speed allowance: one native acceleration step plus at most one
fixed8 velocity LSB per sampled field. At expiry the native routine resumes thrust
at the world boundary, whereas the field integrator has already consumed that
interval under braking. This is a documented transition difference, not evidence
of universally equivalent trajectories. Subsequent AI/collisions can differ with
the changed trajectory; fuel exhaustion and long campaign transitions remain
unverified.

`translation_contract_check.py` passes 1284 signed arithmetic cases including
32-bit extrema, 12 whole-data native fallbacks, four render/restore cases and two
carry resets. Disabled-scaler and injected player/camera-position changes are
rejected by the corresponding oracles. Installer guards, 96 scene/isolation and
420 scale cases, 664 angular checks, 196 option/cache cases, 180 pacing cases,
54 complete converter outputs, 72 pixel cases, recorder/publication checks and
176 C1 target cases plus IRQ race controls also pass.
Evidence: `tmp/c2-native-complete.json`, `tmp/c2-contracts-complete.json`,
`tmp/c2-scenes.json`, `tmp/c2-angles`, `tmp/c2-options.json`, `tmp/c2-pixels.json`,
`tmp/c2-buffer-native.json`, `tmp/c2-recorder.json`, `tmp/c2-display-native.json`.

### Live gate and remaining frame-budget gap

Diagnostic-only counters surround the actual native world call and compare both
player and camera positions. They perform no gameplay writes. All four windows
pass with zero corrections:

| Model / input | Fields advanced | World ticks checked | Pictures/s |
|---|---:|---:|---:|
| PAL 030, steady | 809 | 161 | 49.920 |
| PAL cycle-exact 040, steady | 809 | 161 | 49.920 |
| PAL cycle-exact 040, held right | 938 | 187 | 41.754 |
| NTSC 030, held right | 884 | 147 | 54.233 |

All independent A1 publication counts and B2 ownership/copper checks pass:
661/661/657/663 pictures respectively, one FAST source, two CHIP buffers,
publication at line 4, no input overflow or late-blank deferral. The steady PAL
runs also pass C1 with zero missed prediction targets. Held turns fail C1's
strict display-time check: 122/657 targets on 040 and 72/663 on NTSC are missed
because pictures finish too late for their forecast field. Safe buffer ownership
does not make these predictions timely. The prior C1 build in the same 040 turn
setup measures 42.722 pictures/s and 112/657 misses. C2 measures 41.754 in that
window; changed trajectories also change rendering workload, so this comparison
is not an isolated cost attribution. This remains C4 work, not a waived C1 pass.

Evidence: `tmp/c2-{030-gate,040-steady,040-gate,ntsc-gate}`,
`tmp/c2-control-c1-turn040`, `tmp/c2-fps.json`, `tmp/c2-turn-comparison.json`.
The established observer uses its baseline cache model; the 040 core is not
hardware-calibrated. These are measured emulator windows, not a 50/60 FPS promise
for all scenes or physical hardware. Cached-MMU pixel acceptance remains the
previous scoped check; C2 does not change conversion, buffers or cache policy.

Normal candidate: 39820 bytes, SHA-256
`c45d7bd9b88b923319fca4ff2cdb0dcf902646d6702b245db6034be3b59de385`.
The recorder fixture is `tmp/c2-frames`, pinned by its post-adaptation build
manifest. Version remains 2.0b (13.06.2026). Stop before C3.


## Phase 11b heading-aware extrapolation: C3 gate complete

Buffered enhanced English flight now predicts ship velocity after predicting its
pitch/yaw/roll. It uses the native thrust solver toward that future heading,
retaining inertia and engine capability. Simply aligning velocity to the heading
is incorrect: it erases drift. The controlled player remains C2-owned; projectile,
effect and debris classes keep constant-velocity prediction. No world rules change.

For horizon `f/hz`, rotate the basis with the existing scaled angular steps,
compute native full-step acceleration `a` against that basis, stage
`v' = v + trunc(a*f/hz)`, then `p' = p + trunc(v'*f/hz)`. This deliberately matches
the original endpoint integration at one tick; it is not continuous-physics
half-acceleration integration. The renderer restores velocity, position and basis
before gameplay. No persistent prediction accumulation or extra AI invocation occurs.

The new wrapper reuses `E:7f78–8078` (file `7fa4–80a4`) and the existing guarded
`E:807a` seam (file `80a6`), returning through `E:80ea` (file `8116`). Desired
velocity uses `E:2b7f0` (file `2b81c`), as native `E:7f3e–7f64` does. Normal
thrust uses `D:99be+4*i`; afterburn uses model word +22 from `D:53a4`, with
`(2*value+40)<<8`; braking targets zero. `D:a148+12*i` supplies the already
predicted forward vector. The solver's cosmetic byte `D:bae8+i` is restored
immediately. Fuel, action/timer updates, RNG and AI are never invoked by this wrapper.

Eligibility is ship slots 1–9, class >=11, action -1 or stable action 1/3 with
`D:bb14+2*i > 1`, and native motion-stage `D:ba52+2*i != 1`. Action expiry,
scripted/special motion and the existing cut guards retain current velocity.
The normal experimental `--timing` build retains its previous velocity policy;
Psygore modes and German are unchanged. C1 horizon bounds remain in force.

### Forecast and isolation evidence

`tmp/c3-heading-final.json` replays all 120 retained
`phase10-isolated-turn-ntsc` renderer inputs through the actual candidate on native
68020 and 68040 models. Each model checks 1,877 predictions against the original
motion routine, with 424 changed forecasts, and exact whole-data restoration.
The separate 140 fractional/action cases cover PAL/NTSC, zero/partial/full/extended
horizons, afterburn, braking, action expiry and native fallback. A deliberately
disabled solver fails the forecast oracle. Existing corrupted-restoration controls
also remain effective.

| One-tick trajectory comparison | Count | Old p95 / max km | C3 p95 / max km |
|---|---:|---:|---:|
| Non-player ships, same recorded inputs | 149 | 4.374 / 8.982 | 0.255 / 6.348 |
| Constant-velocity classes 3/4/5/8 | 441 | 0 / 0 | 0 / 0 |

The phase-10 headline p95 4.357 km included the player (189 comparisons); C3 uses
149 world-ship comparisons because C2 now advances the player separately.
The regression gate requires p95 below half that headline and maximum below
three quarters, without excluding unexpected speed changes. Observed reductions
are 94% and 29%. The largest residual coincides with a new AI set-speed command
(from fixed8 7476 to 9114). C3 cannot predict future control decisions; there is
still an occasional visible correction. These measurements bound this retained
one-tick trajectory only, not arbitrary AI changes or the extended C1 horizon.

Other passing checks: 96 scene/isolation cases and 420 signed-scale cases in both
release and experimental builds; C2's 1,284 carry cases, 12 native fallbacks and
four render-isolation cases; eight installer/option cases with whole-hunk and
register/CCR checks; 196 release option/cache cases, 54 complete converter outputs
and 180 pacing/output cases.

### Required live frame-rate gates

The frame-stats recorder and independent publication observer agree on all 661
030 and 656 cycle-exact 040 pictures. Both runs retain one FAST source, two CHIP
buffers, line-4 publication, zero late-blank deferrals and zero input overflow.
C2 records zero player/camera position corrections across 349 actual world ticks.

| Window | Pictures/s | World updates/s | Player fields / checked ticks |
|---|---:|---:|---:|
| PAL 030 steady | 49.920 | 9.925 | 809 / 161 |
| PAL cycle-exact 040 held right | 41.535 | 10.008 | 941 / 188 |

See `tmp/c3-fps.json` and per-run `check.json`, `buffers.json`, `translation.json`.
The 030 display-time gate passes all targets. The 040 held-turn display-time gate
still fails on 119/656 targets/fractions due to rendering overruns; this remains
C4 work, not waived by C3.
The previous C2 held-turn result was 41.754 pictures/s. These windows do not
establish an isolated performance improvement or regression. The 040 remains
uncalibrated against hardware; no new CPU matrix or release work was undertaken.

Normal candidate `tmp/c3-final/WingCommanderCD32.Slave`: 40,124 bytes, SHA-256
`ba4c088be9f634efaaee8a1889a2e19fa0380a0a788c0e49b32d5024f2483a6e`.
A fresh source rebuild reproduces these bytes exactly. The phase-12 save/load
stash remains untouched. Stop before C4.


## Phase 11b frame-time spikes: C4 steady-flight gate complete

C4's steady-flight **displayed-interval** gate passes on the current C3 build.
No scheduler or game-code change was necessary: B2's deferred two-buffer reuse
already absorbs the measured world-tick work spikes in these windows. This is a
verification result, not a new speed improvement or a claim that turning stalls
are fixed. Phase 12 remains paused; stop before D1.

### Measurement and attribution

`frame_report.py`'s existing `frame_ms` means draw-entry to next draw-entry; it is
an internal work interval. It can vary even when every displayed picture arrives
on the next VBL. `frame_spike_report.py` instead joins FSTAT 16 queue submissions
to the IRQ's actual displayed-picture ledger and measures display-to-display
intervals. It requires one recorded queue request per displayed picture, drops
20 warm-up pictures, and classifies each interval by completed world ticks between
its two queue submissions. The world begin/end pairs must be complete.
This is correlation across an overlapped pipeline, not isolated cost attribution.

Relevant existing code-hunk offsets: native world `E:2a8–2da` (file `2d4–306`),
converter/buffer index work around `E:33772` (file `3379e`), native publication
`E:33a12` (file `33a3e`), and VBL instrumentation `E:34162` (file `3418e`).
Slave labels `timing_world`, `release_publish`, `release_presented` and
`frame_stats_display` supply the diagnostic boundaries; no new game seam is added.

`tmp/c4-spikes.json` uses the same immutable C3 diagnostic fixture in all cells:
SHA-256 `bd10fe37b73b0b42d127e683cf8aca52b394c5f2b5f099ad317aad37452ede94`.
It reuses the retained C3 030 steady and 040 turn captures, plus one new
`tmp/c4-040-steady` capture of the missing current-build steady 040 case.
No additional CPU matrix was run.

| PAL window | Display intervals in fields | Display median / p95 / max ms | Pictures/s |
|---|---|---|---:|
| 030 steady | 639 × 1 | 20.032 / 20.032 / 20.032 | 49.920 |
| Cycle-exact 040 steady | 639 × 1 | 20.032 / 20.032 / 20.032 | 49.920 |
| Cycle-exact 040 held turn | 525 × 1, 92 × 2, 18 × 3 | 20.032 / 40.064 / 60.096 | 41.535 |

Both steady windows contain 511 measured intervals without a world tick and 128
with one; every interval in both groups is exactly one field. In the 040 window,
queue-to-queue p95 is 20.224 ms without a tick and 29.312 ms with one; the latter's
world work has p95 6.976 ms. These internal spikes do not become visible gaps.
The 030 queue-to-queue p95 is 20.608 ms in both groups. No interval contains more
than one world tick, so there is **no measured forced-stall/catch-up cadence claim**.
The existing bounded chronological catch-up scheduler remains unchanged.

The held-turn control is deliberately not labelled passing: display p95 is two
fields without an intervening world tick and three with one. Tick-associated
queue intervals have p95 51.520 ms, including world-work p95 8.896 ms; intervals
without a tick still have queue p95 30.912 ms. Both scene work and world work
remain relevant to the later cost investigation. It still misses 119/656 target
fields and fractions, and still fails `display_time_check.py`. C1 accuracy in
heavy scenes is not waived or fixed by C4's steady-flight result.

### Checks and boundaries

The cadence gate requires at least 500 intervals and 100 tick-bearing intervals,
and median = p95 = **one field**. Requiring one field prevents a uniformly slower
25-FPS run from passing just because its percentiles match. Deliberate missed-field,
half-rate and no-world-coverage controls all fail. Input/output hashes and fixture
identity are retained in the report. The companion `frame_report.py` uses a slightly
different draw-boundary crop (638 steady intervals); its display rate agrees.

The new 040 capture passes independent observer/recorder agreement for 661
pictures, all 661 display targets/fractions, and converter/copper ownership:
one FAST source, two CHIP buffers, line-4 publication, zero late deferrals and
zero input overflows. C2 also checks 809 fields and 161 actual world ticks with
zero player/camera position corrections. `tmp/c4-fps.json` reports world rate
within 1% of 10 Hz on both steady cells and the turn control. Previous C3 native
checks remain applicable because the production source and built slave are unchanged.

The normal candidate is still the C3 40,124-byte slave, SHA-256
`ba4c088be9f634efaaee8a1889a2e19fa0380a0a788c0e49b32d5024f2483a6e`.
The observer retains the established cache-model settings; cycle-exact 040 numbers
are not physical-machine calibration. Heavy-scene stalls, extended deadline misses,
forced-stall cadence and real-hardware acceptance remain explicit gaps for D/E.
The phase-12 stash remains untouched.

## Phase 11b rendering costs: D1 model profile complete

D1's practical model profile is complete; **the calibrated-040 portion remains
blocked on A2's missing hardware reference**. No game/slave or emulator code was
changed for D1. D2 below implements the prediction changes selected by this
profile. The D1 measurements neither fix the held-turn overruns nor close
release acceptance.

### Instrument and scope

`render_cost.py` adds selected PCs to the existing read-only host observer through
`frame_capture.py --cost-scopes`. A call-site timestamp is paired with the next
instruction at the **same stack pointer**. The class-2 star branch is similarly
paired with its dispatch-loop return. Timestamps use the emulator's cycle clock,
converted by its recorded base clock × 64, not host time or CPU frequency labels.
The window matches the recorder's complete draw-to-draw intervals after 20 warm-up
pictures: 639 in each steady run, 635 in the turn. Costs include interrupts, bus
stalls, callees and call/return overhead. They are **inclusive elapsed time**, not
exclusive CPU utilisation. Nested rows must not be added.

The unchanged C3 diagnostic release fixture has SHA-256
`bd10fe37b73b0b42d127e683cf8aca52b394c5f2b5f099ad317aad37452ede94`.
The existing observer emulator has SHA-256
`08360549c392f07b1fb3393bf1e071cd0bd5ffcb4048f229d528a1ce628c1313`.
The three final captures are `tmp/d1-030-steady`, `tmp/d1-040-steady` and
`tmp/d1-040-turn-final`; each retains scope configuration, raw events, CPU/cache
settings, ledger hashes and a cost report. The 030 uses the established MMU model
with `CACHE DCACHE`; the 040 uses the established cycle-exact core with `NoMMU`.
Both retain the diagnostic emulator's baseline cache model, including
`cpu_data_cache=false`. Neither is a physical 040/25 measurement or a retest of
the corrected cached-MMU emulator's pixels.

Relevant native code-hunk offsets (English file offsets in parentheses):

| Scope | Entry or call-site boundary |
|---|---|
| View clear | Call `E:0306–030c` (`0332–0338`) to `E:31cd6` (`31d02`) |
| Enclosing scene | Call `E:0320–0326` (`034c–0352`) to `E:294d4` (`29500`) |
| Geometry | All absolute calls and authored slave calls to `E:2a086` (`2a0b2`) |
| Object dispatch | Call `E:294f0–294f6` (`2951c–29522`) to `E:2ca3e` (`2ca6a`) |
| Stars | Class-2 branch `E:2caa6` (`2cad2`) until loop head `E:2ca5a` (`2ca86`) |
| Object bitmap / scaled / rotated drawing | Calls `E:2cac4`, `2cb04`, `2cb48` (`2caf0`, `2cb30`, `2cb74`), each ending six bytes later |
| Cockpit/view composition | Call `E:0c4c–0c52` (`0c78–0c7e`) to `E:2cf0a` (`2cf36`), copying the split view rows back into the composed image |
| Post-publication cockpit/HUD work | Authored call to `E:46e6` (`4712`), including targeting/bookkeeping, not drawing alone |
| Text glyphs | Absolute calls to `E:2fd6a` (`2fd96`); formatting/layout stays in its enclosing scope |

The requested polygon bucket resolves here to the native object bitmap paths:
`E:2efe8`, `2ec98`, `2d746` (file `2f014`, `2ecc4`, `2d772`), including
TM6 image selection, scaling and rotation. There is no separately measured
3D-polygon bucket; do not describe this profile as a polygon-rasteriser census.
The star row overlaps the bitmap row. Geometry overlaps the scene/world scopes.
Slave listing anchors bracket `timing_scene_begin`, its bulk pose backup,
`timing_scene_end`, `timing_scene_snapshot`, `flight_delta` and each
`flight_kalms_block` call. The conversion residual is delta-total minus changed
block calls: **comparison, loop overhead and changed-history copies together**,
not pure comparison instruction time.

### Measured costs and next-step decisions

Mean / p95 **milliseconds per draw-to-draw interval**, including zero for a scope
not called in that interval. Per-call distributions and counts are in the reports.
Zero scaled/rotated or glyph work in steady flight means those paths were not
exercised in that window, not that they are free.

| Scope | 030 steady | 040 model steady | 040 model held turn |
|---|---:|---:|---:|
| Clear | 0.514 / 0.514 | 0.744 / 0.712 | 0.755 / 1.366 |
| Stars | 0.146 / 0.167 | 0.171 / 0.206 | 0.086 / 0.131 |
| Object dispatch, inclusive | 0.167 / 0.190 | 0.190 / 0.224 | 1.894 / 8.682 |
| Object bitmap | 0.144 / 0.165 | 0.168 / 0.202 | 0.787 / 3.861 |
| Object scaled | 0 / 0 | 0 / 0 | 0.187 / 0.950 |
| Object rotated | 0 / 0 | 0 / 0 | 0.901 / 7.330 |
| Cockpit/view composition | 3.800 / 3.854 | 2.908 / 3.104 | 2.931 / 3.373 |
| Post-publication cockpit/HUD | 2.786 / 2.865 | 3.709 / 3.737 | 3.848 / 4.098 |
| Glyph drawing | 0 / 0 | 0 / 0 | 0.083 / 0.141 |
| All geometry calls | 1.895 / 4.836 | 4.076 / 10.031 | 4.500 / 14.656 |
| Prediction including backup | 0.649 / 0.868 | 0.986 / 1.740 | 1.229 / 1.996 |
| Bulk pose backup alone | 0.262 / 0.262 | 0.313 / 0.278 | 0.289 / 0.278 |
| Restore | 0.265 / 0.265 | 0.279 / 0.279 | 0.282 / 0.279 |
| World-boundary snapshot | 0.049 / 0.244 | 0.129 / 0.518 | 0.146 / 0.518 |
| Comparison/loop/history residual | 2.048 / 2.100 | 4.097 / 4.110 | 4.139 / 4.486 |
| Changed-block converter calls | 0.193 / 0.323 | 0.303 / 0.490 | 1.363 / 4.879 |
| Delta conversion total | 2.242 / 2.407 | 4.400 / 4.592 | 5.501 / 9.381 |

**D2:** repeated geometry is the larger opportunity than copying poses alone.
There are 1,020 geometry calls over 639 steady frames and 1,094 over 635 turn
frames. The turn's mean call costs 2.612 ms; total geometry p95 is 14.656 ms per
frame. Bulk backup plus restore averages only 0.571 ms on that model. Skipping
rebuilds still needs a correctness contract for targeting, input and world work;
these inclusive costs are not promised savings.

**D3:** cockpit/view composition is a stable 2.9–3.8 ms per picture; clear is
another 0.5–0.8 ms. This supports investigating region-specific composition and
clear/redraw. It does not justify reviving the unsafe blanket-clear bypass.
Post-publication HUD also costs 2.8–3.8 ms and includes gameplay-sensitive work.

**D4:** comparison/loop/history overhead matters: about 2.05 ms on 030 and
4.10–4.14 ms on the 040 model. Only 10,493 blocks are converted over 639 steady
040 pictures (16.4 of 2,000 blocks per picture); the turn converts 45,676 over
635 (71.9 per picture). This is against each destination's history, not the
immediately preceding image. Dirty-region tracking is worth a correctness-priced
experiment, not an established saving. D5’s model evaluation is complete below;
any future hardware converter selection still depends on A2. Stars and glyphs do not justify separate rewrites.

### Heavy-turn limits and checks

The held turn still displays **41.535 pictures/s**, with 524 one-field,
92 two-field and 18 three-field intervals in the frame report's crop. The
C4 display-ledger crop includes one extra one-field interval. Both steady runs
remain **49.920 pictures/s**, 638 one-field intervals in the frame report.
World rates are 9.925/s (030 steady), 9.929/s (040 steady) and 10.008/s
turning, within 1% of 10 Hz.
All 119/656 held-turn prediction misses remain unchanged.

In the turn, 317/635 internal draw-to-draw intervals exceed one field. Within
that group, object dispatch averages 3.589 ms (p95 10.038), geometry 6.737 ms
(p95 15.843), and delta conversion 6.502 ms (p95 12.269). These overlapping
measurements identify work associated with the long frames; they do not assign
each missed publication to one cause. An internal long interval is not itself a
missed display: steady runs can wait for ownership yet display every field.
The C4 tick/no-tick display correlation therefore remains relevant.

Extra-observer on/off controls are **byte-identical in both frame and display
ledgers** against the retained C3/C4 runs on all three configurations. The
independent A1 observer check matches all 661 / 661 / 656 displayed pictures and
elapsed time (largest difference below 0.001 ms). Paired calls reject missing
returns, wrong stack pointers, repeated entries and backwards clocks; per-picture
scope counts are checked. A changed display ledger is a rejecting control.

Coverage limits: this is one steady Nav-1 window on each model and one held-turn
040 window, not the entire combat/afterburner/campaign matrix. Text formatting,
individual HUD widgets, exclusive IRQ costs and detailed bitmap scanline costs
are not separately attributed. The ordinary candidate remains byte-identical to
C3, and the phase-12 stash is untouched. Calibrated 040 measurements remain an
explicit follow-up under A2 before hardware or E1 acceptance claims.


## Phase 11b prediction overhead: D2 complete

The buffered English release now backs up occupied slots and skips a redundant
geometry rebuild when queued pad input cannot dispatch an edge. D2 is complete
on the required current models. D3 follows below; calibrated 040 timing remains
blocked on A2, and phase 12 stays paused.

### State and geometry contracts

`timing_scene_slots.s` replaces the 7,680-byte bulk copy with 120-byte records
for nonzero object types plus camera/scratch slots 61–63. Type zero is the only
empty value: stars, hidden classes and existing class-7 attachments remain saved.
The field set is unchanged. Angles, effect words and projection words remain
separate parallel arrays, correctly gathered into each record. Empty slots are
left untouched until native rendering allocates one. A saved mask and slot list
preserve the first backup across reuse and restore precisely those slots.

The native allocator `E:2b632` (English file `2b65e`) selects a free slot from
10–60. The guarded six-byte detour at `E:2b648` (file `2b674`) backs up selected
slot D2 **before** the first write at `E:2b652` (file `2b67e`), then replays the
displaced operations and resumes at `E:2b64e` (file `2b67a`). This covers
render-only engine flames created by `E:2914c` (file `29178`), including stale
bytes in previously empty slots. Exhausted allocation never reaches the detour;
unstaged/native execution passes through with native register/CCR results.
All six displaced bytes are checked before installation. Nonbuffered builds
retain the original bulk-copy path.

`timing_edge_geometry` compares **every queued 16-byte pad sample** with native
current pad data `D:c6c8`. The queue normally contains samples even when nothing
changes. Only an entirely unchanged queue (or an empty queue) permits deferring
the first rebuild to targeting. Any transition, in any sample, retains both
calls. The real edge dispatcher and pulse merging still run. Native
`E:19278` / `E:19128` (file `192a4` / `19154`) dispatch release/rising edges;
identical current/previous pad bytes cannot invoke a command. Keyboard dispatch
remains after the targeting rebuild.

There is one essential side effect to retain: `E:2a0c6–2a0d4` (file
`2a0f2–2a100`) copies current range `D:a4dc` to previous range `D:a55c` before
`E:2a086` rebuilds it. After the single rebuild, the authored history pass copies
the new current range to previous range for slots 0–60, excluding classes 0/7
exactly as native. Class 1 and negative classes are not excluded. Whole-data
comparisons prove the same result as two native rebuilds on the scoped cases.
The post-world/cosmetic rebuild, draw-time geometry and ordinary-loop exit
rebuild remain in place. No prediction math, world rate, clear/redraw policy or
conversion algorithm changes.

### Correctness evidence

`tmp/d2-final-equivalence.json` records both 68020 and 68040 Unicorn checks:
240 retained whole-data geometry pairs, 240 transition-guard cases, eight
class/view boundaries, 16 unchanged native pad-queue cases, 1,280 guarded byte
transitions, eight occupancy/restore cases and 12 allocator/register comparisons.
Reused-slot checks retain the first backup. Removing range-history replay or
bypassing the lazy allocation backup is rejected by the same whole-data oracle.
Existing checks retain 96 pose/isolation cases, 420 signed-scaling cases, two
real native flame-allocation cases, the C3 forecast/error bounds, C2 arithmetic
and fallback contracts, installer option/register/CCR checks and release
option/cache/converter checks. The unchanged experimental bulk-copy path also
passes its pose/flame checks. These are correctness checks, not speed estimates.

The final normal release is 40,928 bytes, SHA-256
`c7fe5c1ea7acb9363a3042330be07a9f7d3c8de36306f895f7240bc845b46fe5`.
The final Nav-1 frame fixture is 41,796 bytes, SHA-256
`17bbb088e900e279b175b188e96f497cdc1d9cb58241d09d4ca8d2cffba700e3`.
Version remains **2.0b (13.06.2026)**. Derived builds and evidence stay in `tmp/`.

### Model costs, displayed rates and remaining gaps

Same instruments and cache-model limitations as D1. The final held-turn cost
capture and its control have byte-identical frame/display ledgers. The buffer
checker now resolves its conversion event by symbol; appended cost events no
longer make it inspect the wrong registers. The observer is unchanged.

| 040 held-turn scope | D1 mean / p95 ms | D2 mean / p95 ms |
|---|---:|---:|
| Geometry, all calls | 4.500 / 14.656 | 3.864 / 11.286 |
| Initial pose backup | 0.289 / 0.278 | 0.185 / 0.204 |
| Prediction including initial backup | 1.229 / 1.996 | 1.097 / 1.604 |
| Restore | 0.282 / 0.279 | 0.155 / 0.184 |

Geometry calls fall from 1,094 to 937 over 635 measured picture intervals:
unchanged-input world boundaries now do two rebuilds instead of three, including
the retained post-world rebuild. Initial backup excludes lazy attachment backups
inside native scene drawing; restore includes every saved slot. Costs remain
inclusive of interrupts/stalls and nested work. The fixed-input D1/D2 windows
cover slightly different elapsed simulation time as frame rates change, so these
are workload measurements, not instruction-isolated savings.

| PAL model gate | Displayed frames/s | World updates/s | Fields per displayed interval |
|---|---:|---:|---|
| 030 steady | 49.920 | 9.925 | 638 × 1 |
| Cycle-exact 040 steady | 49.920 | 9.927 | 638 × 1 |
| Cycle-exact 040 held turn | 42.087 | 10.007 | 525 × 1, 100 × 2, 9 × 3 |

The 040 held turn improves modestly from D1's 41.535 frames/s. It still misses
118/656 prediction targets (D1: 119/656); this is **not** a global C1 deadline or
E1 performance pass. Both steady gates retain zero prediction mismatches and
one displayed picture per field. Recorder/observer counts match for all
661/661/656 pictures, with at most 0.001 ms clock difference. Buffer ownership,
CHIP/FAST placement and copper setup pass, with no input overflow or late swap
deferral. C2 reports zero position/camera corrections over 161/161/186 ticks.

Evidence: `tmp/d2-final-030`, `tmp/d2-final-040-steady`,
`tmp/d2-final-040-turn`, `tmp/d2-final-040-turn-cost/costs.json` and
`tmp/d2-final-fps.json`. Commands are in development.md. No fresh corrected-MMU
pixel capture, long campaign, forced-stall cadence or physical-hardware acceptance
is claimed. The calibrated 040 gate remains blocked on A2. The phase-12 stash
is untouched; D3–D5 model results follow below; calibrated acceptance remains open.

## Phase 11b view regions: D3 complete

D3 is complete on the required current models. D4 follows below.

The native renderer already preserves the cockpit with a region map; D3 does
not need another cockpit cache or a blanket clear bypass. The new
`view_regions.s` accelerates those existing regions without changing which
pixels are cleared, copied or left alone. It adds no allocations, cached image,
dirty flags or self-modifying drawing code. World scheduling, prediction, HUD
work, drawing order and conversion remain unchanged.

### Region contract and offsets

The guarded call sites are `E:0306` (English file `0332`) for view clear and
`E:0c4c` (file `0c78`) for composition. Only the buffered enhanced English
installer redirects them. Their six original call bytes, including relocated
targets, are checked before any patch write. Inactive flight tail-calls native;
Psygore modes and German do not install the hooks.

The surface at `D:9154` describes the view, sharing the split row table with the
composed surface at `D:912c`. The Nav-1 view bounds are `(0,10)–(319,114)`.
Native `E:2cc36` (file `2cc62`) scans the cockpit aperture and builds a row/span
map. `D:6f2c` holds the split scratch allocation and `D:6f3c` the span table.
Each 14-byte span has three instruction-displacement words and source/destination
pointers; `E:2ceae–2cebc` (file `2ceda–2cee8`) encodes them. The native copier
at `E:2cf0a` (file `2cf36`) reads that map at every composition. A retained
Nav-1 map contains 134 spans. Cockpit gaps are never copied over.

The new clear accepts only zero-colour, 320-wide row-table surfaces with
`x=0..319`, ordered `y=0..199` bounds and zero bulk-size field. It clears every
byte of each selected row using 32-byte stores. Other colours, clipped widths,
bulk surfaces and inactive flight use `E:31cd6` (file `31d02`) unchanged.
In particular, it does not restrict clears to the visible aperture or leave
stale scratch pixels. The original shared clear and the setup scan at `E:2cd00`
(file `2cd2c`) remain intact, preserving the dependency that rejected the
phase-4 blanket-clear bypass.

Composition decodes the current native map, keeps exact byte heads/tails and
short spans, and batches longword copies. Forward overlap retains native
longword order. Rebuilt maps take effect immediately; there is no invalidation
state. Batching uses the existing `render_selected=30` cached 020/030 selection.
The current 040 model measured native composition faster, so 040/060 and the
uncached selection retain the native copier. That is a model-based conservative
choice, not calibrated hardware evidence. The faster row clear is retained on
both required models.

The call sites use these as void routines: scratch registers and flags are
redefined before use (`E:3766` / `E:31fc6`, files `3792` / `31ff2`). Native
callee-saved registers are preserved. No shared drawing routine is globally
replaced.

### Correctness evidence

`view_regions_check.py` executes both native and replacement routines on 68020
and 68040 Unicorn cores. Each run covers 16 retained-memory comparisons,
96 clear/fallback shapes, 2,560 span cases, 80 overlap cases and four no-map
fallbacks. Widths 1–320,
all source alignments, destination alignment changes, byte tails, short records,
permuted rows, cropped rectangles, colours, bulk clear and inactive/CPU-selection
fallbacks are included. Whole buffers, sentinels and nonzero callee-saved
registers are compared. Deliberately missing clears and truncated spans are
rejected. These are correctness checks, not performance estimates.

The tests also pass on fresh flight memory, loading both FAST and CHIP: the
split scratch/map can reside in CHIP even though the final chunky image is in
FAST. A FAST-only replay is insufficient for those captures. Evidence is
`tmp/d3-gate-native.json` and `tmp/d3-gate-current-pixels.json`. Installer checks
reject changed operands at both new call sites and preserve the complete
option-off game hunk/register state. Existing release checks retain 196
option/cache cases, 54 complete converter outputs and 180 pacing/output cases.

### Build and measurement scope

Normal release: 41,392 bytes, SHA-256
`26030484bcd275dd5b5989b2f4712c20363a0c8c72598cc6475bb5ff71c715f6`.
Nav-1 recorder fixture: 42,260 bytes, SHA-256
`df0c38d40fe196f25d72034d0e33be3f7f65c3f9c1bbffde1b52d84f3d0a9036`.
The equal-size native-path control has SHA-256
`d035c57fca33d87a7e9d83b017efad8cdc1ddd9cde20019f596dc5fc700c7812`;
only its two fallback branch bytes differ. Version remains **2.0b (13.06.2026)**.

The observer binary and machine/cache models are unchanged from D1/D2. The
030 uses the baseline MMU model with `CACHE DCACHE`; the cycle-exact 040 uses
`NoMMU`. Both retain the diagnostic baseline cache model, including
`cpu_data_cache=false`. A2's calibrated-040 gate remains blocked. These are
model measurements, not physical 030/50 or 040/25 performance claims.
Costs use the same read-only call-site brackets and emulated cycle clock, with
20 warm-up pictures omitted. They include interrupts and bus stalls. The
held-turn arms cover slightly different simulation time as rendering changes;
per-frame scope differences are workload results, not an isolated CPU benchmark.

### Measured costs and displayed cadence

The final held-turn cost capture and ordinary-observer control have byte-identical
frame and display ledgers. Other cost reports explicitly record that observer
neutrality was not separately repeated for that capture. The instruments and
call-site probes are unchanged from D1/D2.

Mean / p95 **milliseconds per draw-to-draw interval**:

| Scope and workload | Native-path control | D3 |
|---|---:|---:|
| 030 steady clear | 0.514 / 0.514 | 0.510 / 0.510 |
| 030 steady composition | 3.843 / 3.855 | 3.425 / 3.438 |
| 040 held-turn clear | 0.734 / 0.713 | 0.172 / 0.165 |
| 040 held-turn composition, retained native | 2.906 / 3.260 | 2.937 / 3.259 |

The useful measured savings are 0.418 ms per picture in 030 composition and
0.562 ms in 040 clearing. The steady 030 already fills every field, so its
saving becomes available time rather than additional displayed pictures. The
retained native 040 composition has no claimed speed-up. Do not add these
savings across machines or to inclusive parent scopes.

| PAL model gate | Displayed frames/s | World updates/s | Fields per displayed interval |
|---|---:|---:|---|
| 030 steady | 49.920 | 9.925 | 638 × 1 |
| Cycle-exact 040 steady | 49.920 | 9.927 | 638 × 1 |
| Cycle-exact 040 held turn | 42.493 | 10.006 | 532 × 1, 95 × 2, 8 × 3 |
| Same-size 040 held-turn native control | 42.087 | 10.007 | 525 × 1, 100 × 2, 9 × 3 |

The held turn still has **112/657 missed prediction targets**, compared with
118/656 in its native-path control. This is a modest rendering-cost improvement,
not a global C1 deadline or E1 acceptance pass. The two steady gates retain zero
prediction mismatches. All required candidate gates pass buffer ownership,
FAST final-chunky / CHIP planar placement, copper setup and independent frame
count checks, with zero late swap deferrals or input overflows. Player/camera
corrections remain zero across 161/161/185 checked ticks. Recorder/observer
counts match all 661/661/657 pictures, within 0.001 ms elapsed clock difference.

Evidence stays under `tmp/d3-gate-*`; `tmp/d3-gate-fps.json` records final frame
rates and the cost captures retain their raw events and scope configurations.
No new campaign, forced-stall, corrected-MMU frontend pixel or physical-hardware
play-test is claimed. Native pixel equivalence includes both retained and fresh
flight memory; it is not a replacement for E2's visual acceptance. A2 remains
blocked, phase 12 stays paused, and the phase-12 stash is untouched.

## Phase 11b comparison cost: D4 practical gate complete

The D4 comparison-cost gate is complete on the required current models. The
retained change is a compact full-image comparison, **not drawing-based dirty
rectangles**. D5 model evaluation follows below; calibrated 040 timing remains blocked on A2.

### Scope decision and implementation

D1 measured a material comparison/loop/history cost, but drawing dirtiness is
not final pixel change. The native view clear at `E:31cd6` (English file `31d02`),
called at `E:0306` (file `0332`), rewrites all selected rows. The retained Nav-1
view covers 320 × 105 bytes through its split row table. Composition at `E:2cf0a`
(file `2cf36`), called at `E:0c4c` (file `0c78`), then copies aperture spans.
Marking these writes dirty cannot by itself distinguish the small number of
changed pixels from pixels cleared and redrawn identically. HUD/text and other
writers, previous-object erasure and each planar buffer's separate age also
need coverage before any region can safely be excluded from comparison.

Drawing-based tracking is therefore **deferred, not implemented or measured as
unprofitable**. The practical D4 change takes a smaller, independently testable
saving without inventing a dirty-region completeness contract. A future region
experiment must price marking and invalidation as well as skipped comparisons,
and retain complete-output verification and conservative unknown-writer fallbacks.

`render_source.py` emits eight advancing `CMPM.L` comparisons per 32-pixel block,
using scratch A0/A1. A3/A5 retain the original block starts, so every unequal
longword reaches the unchanged 32-byte history copy and Kalms block converter.
Equal blocks make no planar stores. The two 64000-byte histories, first-use full
conversion, destination replacement, geometry/nonflight invalidation, allocation
fallback, public options and pacing are unchanged. Every source byte remains
covered; there is no new game-hunk patch, allocation or persistent dirty state.

In the ordinary release the changed region is `S:8d3c–8d8d` (slave file
`8d5c–8dad`); in the recorder fixture it is `S:909a–90eb` (file `90ba–910b`).
The region is still 82 bytes: the candidate's branch skips 44 bytes of zero
padding. This keeps all subsequent symbols, data placement and file sizes
identical to D3. `--comparison-control` emits the original instructions and is
diagnostic-only, with `verify_only=true` in its build metadata. The control
slaves are byte-identical to the D3 parent, not just equal-sized alternatives.

### Correctness and focused measurements

- `flight_render_check.py`: 72 whole-output native 020/040 cases against the
  original converter and independent bit packing, including alternating/replaced
  buffers, sparse/dense/no changes, inactive/geometry/option transitions, register
  preservation and allocation failure. The shared experimental `--timing
  --flight-verify` build also passes 72 output cases and both corrupt-output
  abort controls (`tmp/d4-timing-twin-check.json`).
- `comparison_check.py`: 128 single-byte cases spanning every byte in the first
  and last blocks, complete planar/history/source checks, saved registers and
  write bounds. Omitting the final comparison is rejected on both CPU models.
  Candidate/control differences are confined to the declared region, and every
  symbol retains its address.
- Live captures: both planar buffers match independent packing of their own
  retained histories on 030 steady, 040 steady and 040 held turn: six complete
  buffers / 384000 bytes. A changed output byte is rejected. These are end-window
  snapshots, not an every-frame live twin or a subjective visual play-test.
- Existing release gates: 196 option/cache cases, 54 complete nonflight converter
  outputs, 180 pacing/output cases and eight installer cases pass; the installer
  checks the full code hunk and registers/CCR, including rejecting corrupt operands.

Mean / p95 milliseconds per draw-to-draw interval, after the established warm-up:

| Scope | Unchanged D3 control | D4 |
|---|---:|---:|
| 030 steady comparison/loop/history | 2.048 / 2.100 | 2.031 / 2.075 |
| 030 steady total delta conversion | 2.242 / 2.406 | 2.224 / 2.383 |
| 040 held-turn comparison/loop/history | 4.143 / 4.488 | 3.304 / 3.457 |
| 040 held-turn total delta conversion | 5.622 / 9.860 | 4.665 / 8.512 |

The 040 comparison residual is 0.839 ms / 20.3% lower in this window. The 030
change is small and is not a material throughput claim. Residuals include loop
and history-copy overhead, interrupts and bus stalls; they are not exclusive
comparison instruction costs. Turn trajectories differ when rendering time
changes: the changed-block call means are 1.479 versus 1.362 ms. Do not attribute
that difference to the unchanged Kalms converter or add nested rows.

| Recorder window | Pictures/s | Fields per picture | World updates/s |
|---|---:|---|---:|
| D4 030 steady | 49.920 | 638 × 1 | 9.925 |
| D3 control 030 steady | 49.920 | 638 × 1 | 9.925 |
| D4 cycle-exact 040 steady | 49.920 | 638 × 1 | 9.927 |
| D4 cycle-exact 040 held turn | 43.424 | 543 × 1, 89 × 2, 3 × 3 | 9.965 |
| D3 control cycle-exact 040 held turn | 42.493 | 532 × 1, 95 × 2, 8 × 3 | 10.006 |

The turn FPS difference is 2.2%, below the shared 3% general throughput-claim
threshold; report the window result, not a general speedup. The directly measured
comparison residual supports keeping the change. Both in-session controls repeat
D3's frame and display ledgers byte for byte. Candidate cost-observer on/off
ledgers also match byte for byte on the turn. Other cost reports explicitly do
not claim a separate observer-neutrality pair for their captures.

The independent observer agrees with all 661 / 661 / 658 candidate pictures;
maximum elapsed-time disagreement is below 0.002 ms. Steady prediction targets
all match. The held turn still misses **100/658** targets (control: 112/657), so
its strict display-time check remains a failure. Buffer checks retain one FAST
source, two CHIP targets, swaps at line 4, eight planes and FMODE 3, with no late
deferrals or input overflows. Player/camera checks show zero corrections over
161 / 161 / 181 world ticks. This is not a global C1 deadline or E1 acceptance pass.

Same observer SHA-256 and baseline cache models as D1–D3: cached 030 MMU with
`CACHE DCACHE`, and cycle-exact 040 with `NoMMU`; diagnostic `cpu_data_cache=false`
on both. No calibrated 040, corrected-MMU frontend visual retest, NTSC retest,
forced stall, campaign or physical-hardware acceptance is added here.

Evidence: `tmp/d4-final`, `tmp/d4-final-control`, `tmp/d4-frames`,
`tmp/d4-frames-control`; `tmp/d4-final-native.json`, `tmp/d4-final-boundaries.json`,
`tmp/d4-live-pixels.json`, `tmp/d4-options.json`, `tmp/d4-install/report.json`,
`tmp/d4-fps.json`, `tmp/d4-misses.json` and each `tmp/d4-*` capture's reports.
The normal slave remains 41392 bytes, SHA-256
`585ae02c164df96573173b936b84841b942a8cc030d7ef6c18e1ca3a87bc8c6a`.
The 42260-byte Nav-1 recorder fixture has SHA-256
`75582cc7c4564329ad7d0455ceda4d5e440e75099a2effb1a2275e2abc393da4`;
its D3 control is
`df0c38d40fe196f25d72034d0e33be3f7f65c3f9c1bbffde1b52d84f3d0a9036`.
Version remains **2.0b (13.06.2026)**. Phase 12 and its saved stash remain untouched;
OCS work is not started.

## Phase 11b Kalms families: D5 model evaluation complete

D5 is complete on the current models. **Retain the current converter selection.**
The user excludes real-hardware validation at this stage, so hardware calibration
is separate follow-up under A2, not a D5 completion gate. These results do not
establish the best routine on physical 040/060 hardware. E1/E2 and phase 12 remain
open. No production assembly or cache policy changes in D5.

### Candidates and semantics

Kalms does provide CPU-specific routines: the pinned
`c2p1x1_8_c5_030` and `c2p1x1_8_c5_040` sources in
`manifest/kalms-c2p.tsv` are the applicable 1:1, eight-plane, contiguous-plane
families. The latter explicitly targets 040/060. The upstream
[collection](https://github.com/Kalmalyzer/kalms-c2p) also contains other pixel
formats and layouts, which are not interchangeable with this surface.
Both families were already embedded for full surfaces; cached 020/030 nonflight
rendering already selects the 030 family. Flight used the 030 family for every
changed 32-pixel block, regardless of CPU, and the original converter for a new
buffer's full conversion. D5 specifically re-evaluates those flight choices.

Both candidates use immutable generated constants (320×200, 8000-byte plane
stride), not Kalms' mutable initialisation or SMC. The 040 single-block candidate
retains that stride with a 32-pixel input extent. Its full-stream scheduling and
prefetching cannot be assumed useful for isolated blocks; timing decides.

`--c2p-experiment` generates five diagnostic arms from the D4 release path:
030 changed blocks (`control`), 040 changed blocks (`block040`), and forced full
conversion with original/030/040 routines. The latter three keep the same history
copy, preserving two-buffer state. They measure sustained full conversion, not
just the two cold destination fills or nonflight intro conversion.
Every diagnostic arm is 42356 bytes with identical shared symbol locations;
96 padding bytes relative to the normal recorder remove size/alignment as an
inter-arm variable. Diagnostics never alter the normal release.

In these recorder builds, the block slot is `S:9186–9455` (file `91a6–9475`),
full-conversion call `S:9080` (file `90a0`), and forced-full switch `S:9048`
(file `9068`). Full Kalms entries are `S:9a70` / file `9a90` (030) and
`S:a280` / file `a2a0` (040). The block candidate changes only its reserved slot;
full candidates change the two-byte NOP to `moveq #0,d7` and, where applicable,
the full-call displacement. Original code, frame scheduling, allocation and
buffer ownership remain unchanged.

All five arms pass **360 native whole-output comparisons** on 020/040 ISA models:
alternating and replaced buffers, small/sparse/dense changes, 128/166/200 heights,
inactive flight and allocation failure. Register preservation, source integrity
and store bounds pass. The separate D5 checker verifies exact shared layout,
allowed changes and full-call targets; replacing the block converter with RTS
is rejected on both ISA models. **All 20 live planar buffers (1,280,000 bytes)**
match independent packing of their own histories. Buffer ownership checks pass
for the 040 block candidate on both models. These are memory/pixel checks, not a
new subjective display-glitch or campaign acceptance pass.

### Measurements and disposition

Same-session deterministic Nav-1 held-turn captures, `CUSTOM5=0`, frame recorder
and read-only cost observer. The 030 uses the existing MMU/cache baseline and
`CACHE DCACHE`; the cycle-exact 040 uses the existing `NoMMU` model. Both retain
the diagnostic baseline's `cpu_data_cache=false`; the 040 core is not a calibrated
040/25 or the corrected MMU frontend used for the user's visual acceptance.
Observer binary SHA-256:
`08360549c392f07b1fb3393bf1e071cd0bd5ffcb4048f229d528a1ce628c1313`.
The first 20 draw records are warm-up. Windows end at recorder capacity, so
full-conversion arms cover longer simulated time and different trajectories;
these are workload results, not identical-source leaf benchmarks.

| Model / converter | End-to-end frames/s | Fields per picture (count × fields) | Delta service mean / p95 ms |
|---|---:|---|---:|
| 030 / current 030 blocks | 47.533 | 605×1, 32×2 | 3.288 / 7.406 |
| 030 / 040 blocks | 47.604 | 606×1, 31×2 | 3.244 / 7.224 |
| 030 / full original | 30.630 | 234×1, 387×2, 3×3 | 17.363 / 18.203 |
| 030 / full Kalms 030 | 35.496 | 374×1, 256×2 | 13.044 / 13.874 |
| 030 / full Kalms 040 | 24.839 | 611×2, 6×3 | 20.802 / 21.233 |
| 040 core / current 030 blocks | 43.424 | 543×1, 89×2, 3×3 | 4.665 / 8.512 |
| 040 core / 040 blocks | 43.255 | 542×1, 90×2, 4×3 | 4.703 / 8.969 |
| 040 core / full original | 17.814 | 162×2, 397×3, 43×4 | 33.634 / 34.394 |
| 040 core / full Kalms 030 | 16.179 | 82×2, 382×3, 133×4 | 38.565 / 39.258 |
| 040 core / full Kalms 040 | 16.475 | 101×2, 379×3, 119×4 | 37.575 / 38.469 |

Delta service includes comparison, conversion and history for block arms;
full arms include conversion plus their identical full history copy. All costs
include interrupt/bus elapsed time. The changed-block call totals alone are
1.162 / 4.913 ms mean/p95 for 030-on-030 versus 1.098 / 4.604 for 040-on-030;
on the 040 model they are 1.362 / 5.031 versus 1.387 / 5.307. Changed workload
counts and trajectories prevent treating these totals as per-block speed ratios.

- **Changed blocks:** retain 030 on both models. FPS differences (+0.15% on 030,
  −0.39% on the 040 core) are below the 3% meaningful-change threshold. There is
  no measured reason to introduce CPU dispatch into the flight path.
- **Full conversion on 030:** the 030 family beats the original in this workload,
  consistent with the existing nonflight selection. Even this best full arm
  remains substantially below changed-block throughput. No new full-flight mode
  or cold-fill-only optimisation is justified by these sustained-window results.
- **Full conversion on the current 040 core:** neither Kalms family wins against
  the original. Keep the original fallback; do not retry this same model matrix
  without a changed premise. A calibrated cache/memory reference is such a change.

All ten independent frame/observer reconciliations pass (640–660 pictures on 030,
620–658 on 040; maximum elapsed disagreement below 0.002 ms). World rate remains
9.929–9.986 Hz on 030 and 9.965–9.994 Hz on the 040 model, within the
existing ±1% gate. No recorder overflow is accepted.
The padded 040 control's frame and display ledgers are byte-identical to the
retained D4 held-turn control without cost scopes. This is cross-session/layout
repeatability evidence, not a newly measured same-session observer on/off pair;
all cost reports explicitly label separate neutrality as unchecked. No claim of
a small speedup, global prediction-deadline pass, NTSC gate, 060 timing or physical
hardware result follows from this experiment.

Normal release SHA-256 remains
`585ae02c164df96573173b936b84841b942a8cc030d7ef6c18e1ca3a87bc8c6a`,
byte-identical to D4 and to the current preinstalled archive's slave. Diagnostic
fixture hashes and changed ranges are in `tmp/d5-pixels.json`; raw captures and
cost/frame reports are under `tmp/d5-{030,040}-{control,block040,full-original,full030,full040}`.
`tmp/d5-fps.json` consolidates cadence; `tmp/d5-*-native.json` records the native
comparisons. Reproduction commands are in development's D5 section.

## Cannon spawn: first-interval prediction hold

The enhanced English release now predicts newly constructed projectiles in their
first world interval. Native velocity was already available; two independent
continuity guards caused the reported hold. Construction and simulation remain
native; the fix records presentation metadata only.

### Native sequence

All `E` addresses below are English code-hunk offsets; file offsets add `2c`.

| Step | Code / file offset | Verified behavior |
|---|---|---|
| Held-fire input | `18f3a` / `18f66` | Calls `06fe`; preview's `timing_fire_gate` suppresses this call, so only committed world-tick input fires. |
| Player fire eligibility | `06fe` / `072a` | Requires player `D:94c6 == -1` and positive gun energy, then calls `c9d2` / `c9fe`. |
| Gun enumeration | `c9d2` / `c9fe` | Iterates the player's weapon mounts; enabled class-8 entries call `c458` / `c484`. |
| Slot construction | `c4cc` / `c4f8` | Calls `9a86` / `9ab2`; allocator `2b632` / `2b65e` searches empty slots 10–60. The player path has a fallback at `9a5a` / `9a86` if allocation fails; that fallback is not exercised by the reproduction. |
| Identity and pose | `9a0a` / `9a36`, `c4ee` / `c51a`, `c53a` / `c566` | Initializes model/class and clears position/velocity, copies the shooter's basis, then sets mount-relative position through `2b5cc` / `2b5f8`. |
| Lifetime and velocity | `c55e–c662` / `c58a–c68e` | Loads projectile life from the weapon descriptor; projects shooter velocity onto the bolt's forward direction through `2ac88` / `2acb4`, then adds the weapon's forward speed. Class 8 also computes its aim point. Velocity is ready before return. |
| Player cooldown | `c87a–c898` / `c8a6–c8c4` | For the player's class-8 shot, reloads the player's own `D:94c6` from the weapon cooldown table. This field is not exclusively object lifetime. |
| Scheduled world | `02a8` / `02d4` | Lifecycle at `76e4` / `7710` precedes processing/integration at `7b4e` / `7b7a`. `76a8` / `76d4` decrements non-sentinel countdowns. |
| First motion | `7d1a` / `7d46`, `80b6–80e0` / `80e2–810c` | Class 8 takes the ordinary position-plus-velocity path in the second processing pass, before the post-world prediction snapshot. |

The enhanced scheduler commits native input **before** this world update, then
calls `timing_scene_tick` and `timing_scene_snapshot`. A surviving player bolt
therefore already has velocity and one native position step when first drawn.
The held point is its first post-update position, not necessarily its muzzle
spawn coordinate. Collision/destruction can remove a bolt before it reaches
this presentation path; the reproduction isolates the surviving-shot case.

### Cause in the previous build

The previous `timing_scene_snapshot` first clears each prediction bit, then requires unchanged
class/model and a non-increasing `D:94c6 + 2*slot` before accepting continuity.
An empty-to-class-8 slot fails the identity check. A recycled matching slot can
also fail the lifetime-reload test. Copying the new position and velocity into
the snapshot does not set its prediction bit until the next accepted snapshot.

Separately, the player's gun-ready sentinel is `-1`. Reloading that same timer
for a shot makes it increase, even after the native countdown step. The generic
lifetime test therefore clears the **player's** prediction bit. At the start of
`timing_scene_begin`, a false player bit skips the whole world-object prediction
loop as though the player had teleported. The camera still follows its existing
path; this is a suppression of world-object extrapolation, not proof that the
entire screen or player control freezes.

Both guards must be addressed. Merely permitting a new projectile through the
slot guard still leaves the whole-view guard active on its firing tick. Merely
ignoring player cooldown reloads still leaves the new projectile unpredicted.
After the next ordinary update, unchanged identities and decreasing timers pass;
position prediction then uses the already-existing native velocity smoothly.
The hold covers one 10 Hz simulation interval, nominally 100 ms. The exact
visible duration depends on render/display timing and is not measured on hardware
by this native check. Input waiting for its next world tick is a separate latency.

### Constructor-certified first-interval prediction

`whdload/timing_projectiles.s` records the completed native slot's class/model and
its shooter's observed cooldown. The guarded English hook sites are:

| Hook | Code / file offset | Coverage |
|---|---|---|
| Gun return | `c912` / `c93e` | Shared player/AI `c458` construction, including class 8 bolts and class 11 guided launches. |
| Alternate AI shot return | `c316` / `c342` | `c1e4` model-48 class-5 approximate shot effect. |
| Missile/effect return | `ca5e` / `ca8a` | `ca38` class-10 path, including delegation from `c458`; no shooter cooldown reload here. |
| Common initializer return | `9a52` / `9a7e` | Revokes pending birth/cooldown when any slot is reinitialized, even to the same class/model. |

Each hook preserves the original epilogue, registers and condition codes. No
allocation, velocity, lifetime, energy, collision or firing rule changes. Failed
slots and render-staged constructors cannot certify a birth. Only completed
weapon constructors may certify classes 5, 8, 10 or 11; arbitrary effects and
ordinary identity changes do not gain the exception.

The post-world snapshot accepts a pending birth only while its class/model still
match and its lifetime remains live (class 5 uses its native effect script, not
the word lifetime). It still requires a valid previous snapshot and unchanged
view. Ordinary slots retain continuity checks. A constructor-certified shooter
cooldown may equal the recorded value or one less, accounting for the native
countdown between player input and snapshot; identity, action and position-cut
checks still apply. Actual player cuts still suppress whole-world prediction.
Birth and cooldown masks are consumed after every snapshot and cleared on clock
rebase, so records cannot bridge modal transitions. Multiple mounts retain
separate slot identities. The renderer uses the existing velocity/heading-aware
forecast and restores the authoritative data before gameplay resumes.

`tools/projectile_spawn_check.py` executes complete native constructors against
an unmodified-code reference on 020/040 ISA models, for shooters 0 and 1 and
weapon models 24–33 plus the alternate model-48 path. All 44 constructors preserve
the entire data hunk, returned registers and materialized CCR. Sound enqueue is
stubbed equally in both arms. The checker includes native countdown/integration
for classes 5/8/10 and the native class-11 launch transition, then tests five PAL
render fractions: 220 samples restore the entire authoritative data hunk. The
constant-velocity classes match exact signed displacement; class-11 samples use
the existing guided forecast rather than asserting a constant-velocity oracle.
Class 10's native constructor can provide zero velocity; this fix does not invent
motion absent from the simulation.

Four two-mount cases retain both births. Fifty-six rejecting controls cover each
original guard independently, death, model replacement, expiry, view/first-snapshot
cuts, mismatched cooldown, player jumps, same-model reinitialization, inactive or
staged construction, invalid slots and modal rebasing. These are isolated semantic
checks, not complete collision/AI world replay or hardware timing measurements.
Retained evidence is under `tmp/projectile-fix-final-*`. Installer, option-off,
scene-restoration and whole-output converter regression checks also pass.

The short Nav-1 held-fire recorder gate uses `tmp/projectile-fix-frames2` with
`CUSTOM5=0`. These are end-to-end displayed-picture rates, not native execution
throughput:

| Model | Displayed frames/s | World updates/s | Display intervals (fields) |
|---|---:|---:|---|
| PAL 030 baseline, CACHE/DCACHE | 49.92 | 9.93 | 638 × 1 |
| PAL cycle-exact 040, NoMMU | 48.03 | 9.94 | 612 × 1, 25 × 2 |

The independent observer agrees with all 661/660 recorded publications; the
trimmed analysis window supplies the intervals above. Both runs pass FAST/CHIP
placement, two-buffer ownership, line-4 publication and zero input-overflow
checks. The 040 remains an uncalibrated model; occasional two-field pictures are
still present. This is not a hardware smoothness acceptance or E1 completion.
Reports: `tmp/projectile-fix-fps.json` and each `tmp/projectile-fix-0?0-fire/`
`check.json`/`buffers.json`. Normal release SHA-256:
`f2bcdd984e2d2ec67b24054ef0d2888d449740d7fe79b76e94b35d963b00a647`.
The enlarged diagnostic build required long PC-relative transfers for the
renderer fallback and original 128-line converter; regression checks cover their
unchanged output. No converter algorithm or cache policy changed.


### Intro 10 Hz world and extrapolated presentation

The enhanced English ship/title and asteroid-credit world now uses the same
10 Hz scheduler and bounded display-time extrapolation as flight. This is the
selected working rate, not a historical-rate proof from the PC recording.
Other languages/options and the separate music-cued Origin logo remain native.
Flight controls are not enabled in the intro: a separate activation flag shares
only the world clock, scene prediction and display queue.

Offsets below are English executable code-hunk offsets (`E`); file offsets are
`E + 0x2c`. Data offsets (`D`) are relative to hunk 1 (stored file base `0x3a048`).

- `E:1fd00..1fd8e` (file `1fd2c..1fdba`) is replaced by a script loop that
  advances its native index/title geometry only on world updates: 296 native
  calls to `E:02a8`, over 1480 PAL fields in the isolated scheduler check.
- Credits detour update/draw/finish at `E:1fdda`, `1fde0`, `1fe14` (file
  `1fe06`, `1fe0c`, `1fe40`). Native text/page tests at `E:1fdec` and `1fe30`
  retain their 220/320-field deadlines. Music interrupt code is unchanged.
  The eight-byte exit span at `E:1fe44` includes the old backward branch;
  explicit destinations are `E:1fc8e` (repeat) and `E:1fe4c` (skip).
- Scripted view 15 uses camera slot 61. Native `E:7056` advances its position
  and basis during updates; rendering predicts and restores it alongside the
  objects. Calling the native camera update again per picture would double-step
  the camera. Intro prediction also allows object slot 0 to rotate.
- Asteroid generation/cleanup `E:98a2`, formerly called by drawing at `E:032e`
  (file `035a`), now runs once per intro tick after native visibility rebuild
  `E:2a086`. `E:9836` supplies the spawning proxy, `E:969a` allocates class 4,
  and `D:5212` holds the slot list. Cleanup `E:97b2` temporarily uses the world
  counter `D:914c` instead of draw counter `D:9150` for its modulo-20 selection.
  Leaving generation in drawing caused snapshot restoration to discard new
  asteroids: this explains the missing field behind the credits and is fixed.
- Background flash `E:15fb4`, called at `E:02f8` (file `0324`), and the
  `E:65f4` emission predicate are tick-owned in the intro. Render randomness
  uses a private seed; authoritative gameplay RNG `D:6f18` is restored.

Validation uses normal release `tmp/intro-clock-release-r2` (SHA-256
`fdd92fbbda8689e3ec3ab2353d5baa866859469a684026841fd71527e0a6de8d`) and
recorder build `tmp/intro-clock-stats-r2` (SHA-256
`2ea7d7301a6756ca9bdb9d90d31924f3fb7dfdc3978e16a3234f19e7907a8166`).
Native 020/040 checks pass 12 PAL/NTSC clock schedules, 96 camera/object
prediction/restoration cases, title completion, flash/emission ownership and
both credit exit destinations. Sixty actual native draws from live title/credit
states show between-tick projected movement, including 81 changed asteroid
projection samples per ISA model, while restoring authoritative poses, object
identities/lifetimes and gameplay RNG. That check excludes composition/C2P and
interrupt execution; live publication checks cover the display path separately.
Installer guards, option-off/converter checks (196 options, 54 outputs, 270
pacing cases), 44 native projectile constructors, 220 spawn renders and the
96-case flight scene regression also pass.

| PAL model / section | Displayed frames/s | World updates/s | Recorded pictures |
|---|---:|---:|---:|
| Cached 030, title | 48.98 | 9.985 | 786 |
| Cached 030, asteroid credits | 49.92 | 9.978 | 319 |
| Cycle-exact 040, title | 25.30 | 9.980 | 751 |
| Cycle-exact 040, asteroid credits | 29.13 | 9.950 | 186 |

These are end-to-end recorder measurements, not a matched optimization benchmark
or hardware guarantee. The 8192-record cap truncates the 030 title measurement to
16.03 seconds; the 040 title covers 29.65 seconds. Independent observers agree
with every recorded publication (786/319 on 030, 751/186 on 040). Both models
complete exactly 296 title updates and the first credit page in 320 fields.
The 030 full-cycle run completes all 18 credit pages and repeats; both runs
then reach the menu with intro/flight/staged/pending flags clear. Audio timing
code and credit deadlines are preserved, but this does not assert a pixel- or
music-cue-identical title sequence after selecting a new world rate.

Reports are `tmp/intro-clock-report-r2.json`,
`tmp/intro-clock-live-poses-r2.json`, `tmp/intro-clock-native-r2.json` and the
section `check.json` files under `tmp/intro-clock-0?0-r2/`. The 040 core remains
uncalibrated against hardware. E1, full campaign acceptance, separate Origin-logo
motion work and phase 12 release work are not completed by this gate.


## Phase 13: OCS static investigation

Phase 13 is complete as an investigation and implementation plan only. No OCS
runtime patch, emulator benchmark or hardware compatibility result is claimed.
The [ordered plan](ocs-plan.md) is authoritative for subsequent work. In
particular, the blitter/CPU crossover remains a measurement question, not a CPU
family assumption. Reproduction commands are in
[development](development.md#phase-13-ocs-static-investigation).

### Identity, notation and loader

Here `O:` is English OCS code hunk 0, `OD:` is its data hunk 1, `O3:` is code
hunk 3, and `OS:` is the original OCS slave code hunk 0. All addresses below are
**hunk offsets**, except explicitly labelled file or PatchSeg offsets. To obtain
a file offset add the payload base in this table; BSS/tail storage has no file
bytes. Existing `E:`, `D:` and `S:` elsewhere in this document remain CD32-only.

The supplied pinned OCS archive matches a fresh extraction file for file. Its
`WingCommander.Slave` is byte-identical to the installer's
`WingCommanderECS.slave`. Only `data/Wing.english` is supplied; no German executable
was available to inspect. Both slave and game are ordinary HUNK files.

| File | Bytes | SHA-256 | WHDLoad CRC16 |
|---|---:|---|---|
| `WingCommander.Slave` | 5324 | `eec155c946e8a247e2c4811fc2279d476c330f2d1b5797cc0defb35918913913` | `b380` |
| `data/Wing.english` | 278304 | `eff90d6cfbc80b008e5e508ff6488f221b6e7243958aaff6fdfd0b06e6724a30` | `00e8` |

| Hunk | File payload base (hex) | Stored / allocated bytes (hex) |
|---|---|---|
| Slave 0 CODE | `0020` | `14a8 / 14a8` |
| Game 0 CODE | `002c` | `358c8 / 358c8` |
| Game 1 DATA | `39948` | `7bb8 / f5b8` |
| Game 2 BSS | none | `0 / 4` |
| Game 3 CODE | `41e4c` | `1d94 / 1d94` |

Game hunks have no explicit Chip/Fast allocation flags. Allocated game hunks total
289,816 bytes before loader bookkeeping. Relocations matter: the entry jump in
hunk 0 targets hunk 3, not hunk 0. The Manx/Aztec-style startup establishes A4 at
`OD:7ffe` (`O3:14d0`). The zero-filled data allocation extends beyond stored data.

| Slave evidence | Meaning |
|---|---|
| `OS:000c`, `000e` | Header v17, flags `3402`; neither ReqAGA nor Req68020 |
| `OS:0010`, `0020` | 512 KiB base/Chip requirement, 960 KiB expansion request |
| `OS:002a`, `002c`, `0ef4` | `34005.a500`, 256 KiB Kickstart image |
| `OS:01ee`, `01fc` | Reserve 256 KiB for ROM; remaining expansion pool `b0000` (704 KiB) |
| `OS:0f81` | C1 German, C2 cheat, C3 system, C4 mission; no native C5 |
| `OS:10e8`, `147c` | Control tags obtain CPU attention flags |
| `OS:10f4`–`1110` | SetCPU value `032a`, or `3b3d` for 040, mask `7f3f` |
| `OS:1120`, `1130` | English file probe with German fallback |
| `OS:1158`–`117e` | CRC selectors `116d`, `00e8`, `262d` and three patch lists |
| `OS:11b8`, `11ca`, `11e0` | LoadSeg, PatchSeg, then enter loaded code |

These header requirements are not a measurement of total host/preload RAM. The
original ReadMe's 512 KiB Chip plus 1 MiB other-memory requirement needs fresh
verification with an enhanced slave. Do not call ordinary public allocation
“Fast RAM”: native `AllocMem` can return another memory class.

The supplied revision selects the list at `OS:1302`. Its eight entries are:

| Original PatchSeg offset | Mapped hunk offset | Action |
|---|---|---|
| `026a3c` | `O:26a3c` | Subroutine patch to `OS:13a0` (audio/custom-register helper with beam waits) |
| `027132` | `O:27132` | Longword replacement `0c400ed0` |
| `027740` | `O:27740` | Longword replacement `00bfe001` |
| `0272b2` | `O:272b2` | Jump to `OS:138e` (`clr.w 8(a5)` then return) |
| `044eba` | `O3:0036` | Two-byte NOP |
| `045526` | `O3:06a2` | Word `7001` |
| `045528` | `O3:06a4` | Skip entry, argument 4 |
| `0463a8` | `O3:1524` | Byte `60` |

The hunk-3 PatchSeg base is `44e84`, the sum of prior **allocated** hunk sizes,
not a file offset. The hunk-3 changes bypass native memory/startup checks. Other
CRC lists start at `OS:12bc` and `1348`; absent executables prevent assigning
verified revision/language maps or enhancement offsets to them.

### Native chunky, blitter and display contract

The original expectation that OCS would have no C2P was wrong. The native path
converts a byte-addressed chunky surface to four planar bitplanes through queued,
multistage blits. This is a separate implementation from the CD32 eight-plane
path. Static evidence establishes the mechanism; the P13A2 functional gate below
establishes pixel selection and queue ownership. Actual beam publication and
usable overlap under contention remain live work.

| OCS hunk offsets | Static finding |
|---|---|
| `O:31de2`–`31e0a` | Surface allocation: even-rounded width times height; one byte per pixel |
| `O:31e10`–`31e22`, `33b60`, `33b76`, `33b94` | Flag selects Chip or public allocator; row table allocated separately |
| `O:31e7c`, `322e0`, `31e98` | Width-based row stride, surface clear, composition/copy |
| `O:32554`–`325c6` | Surface dimensions/source copied into conversion descriptors |
| `O:324e0` | Two `29c`-byte conversion descriptors |
| `O:334e4`–`3350a` | Planar width rounds to 16 pixels, row bytes = width/8, height has two extra rows, depth = 4 |
| `O:3323e`–`33268` | Three planar-sized regions allocated in Chip RAM: two display buffers and shared conversion scratch |
| `O:33aea`, `33af6` | Bitmap plane pointers skip two row strides; only four planes populated |
| `O:33348`, `333b4` | Direct planar clear/pixel writes also exist |
| `O:3260a`–`3262a` | Wait for previous conversion, rotate buffer, submit selected descriptor |
| `O:32646`–`328c6` | Staged blitter controls/masks, including `ff00`, `f0f0`, `cccc`, `aaaa` |
| `O:3291e`–`3298e` | Three submissions with field wait and partial completion waits |
| `O:3299c`–`329de` | Queue-node setup and graphics.library QBlit (vector -276) |
| `O:329e4`, `32a26`, `32dba` | Conversion callback chain entries |
| `O:33426`, `33442`, `3385a`, `33a6e`, `33aa8` | Buffer indices and Copper publication route, ending at COP2LC write |
| `O:3381a`, `3398e`, `339c0` | View, LoadRGB4/MakeVPort, MrgCop setup |
| `O:33872`, `34076` | Teardown and field-wait path |

At the initialized 320×200 geometry (`O3:004a`–`0052`), the planar formula gives
32,320 bytes per region, 96,960 bytes for all three. This is **two display buffers
plus workspace**, not triple buffering. A CPU backend might remove 32,320 bytes
of workspace only after proving no remaining consumer uses it. It would still
need its own code/history/state budget. Viewport height is separately adjusted
at `O:33970`; preserve borders, row padding and plane offsets in the pixel oracle.

The blitter can only consume Chip-accessible sources. The source pointer passes
from the surface into descriptors at `O:32586` and `325c6`; moving that surface
to Fast RAM while keeping the native queue is invalid. Conversely, some surfaces
already select public allocation. A runtime allocation/consumer census must
identify precisely which drawing work benefits from a move, rather than globally
rewriting memory flags.

`O:3293a`–`32942` waits for the field clock to change between queue submissions.
`O:32976`–`32984` waits for the first two flags; `O:32990` waits for the third,
including at the next frame's entry. Thus the existing path includes both pacing
and asynchronous completion. Measuring just one callback, or comparing a paced
blitter frame with an unpaced CPU frame, would conflate conversion throughput,
overlap and scheduling. The crossover experiment must report all of them.
Neither native blitter speed on 68000 nor CPU/Fast superiority on 020 is measured
by this investigation. Preserve both candidates until P13C2 establishes a choice.

Direct planar writes also mean that changed-block histories need more than a
chunky-source comparison. Publication and source ownership must be correct for
both backends before introducing incremental conversion. No AGA FMODE setting
belongs in an OCS backend, even with a 68020 or faster CPU.

### World, clock and intro anchors

| OCS hunk offsets | Static role |
|---|---|
| `O:0694`–`06c2` | Flight loop: input `18d14`, world `02be`, decorated draw `0512`, systems `4460` |
| `O:02be` | World dispatcher; includes `745a`, `78c4`, `6584`, `1445a` and update counter |
| `O:02e6`–`0330` | Draw divisor, clear, world draw `28548`, conditional asteroid path `9618` |
| `O:0512`, `0b80` | HUD/simulator/message composition and frame-finish route to `3260a` |
| `O:78c4` | World object dispatch, slots 0 through 60 |
| `O:79fc` | Angular update using the per-object angular arrays |
| `O:7e2c`–`7e56` | XYZ position advances by XYZ velocity |
| `OD:8928`, `94fa`, `8e8c` | Position, velocity and class arrays (A4 + `092a`, `14fc`, `0e8e`) |
| `OD:88da`, `88de` | World-update and draw counters (A4 + `08dc`, `08e0`) |
| `O:342a2`–`342b4` | VBL handler increments `OD:77fe`, decrements countdown at `OD:7802` |
| `O:34082`, `34098`, `340ba`, `34122` | Countdown, wait and supervisor STOP/field-change paths |
| `O:26ece`, `26ef8` | CIAB TOD references in the audio code |
| `O:33f28`, `33f38`, `33f74`, `33f88` | Native joystick/CIA fire sampling |

The field clock is A4 minus `0800`, not the CD32 offset. Ten world updates per
second is the selected shared design target; native OCS speed/range-unit and
full side-effect mapping are still required. The table is a starting map, not
an assertion that CD32 FR-01–FR-23 are already proven on OCS.

The title's world loop is at `O:1ef24`–`1efb0`, with 296 updates, odd-update draws,
thresholds 135/235 and a title drawing parameter changing from 200 to 16.
That parameter feeds the sprite-scaling routines at `O:1ed64`/`1ed9e`; it does
not resize the conversion bitmap. Credits capture the
field clock at `O:1eff8`, call world/draw at `1effc`/`1f002`, check the text deadline
of 220 fields at `1f00e`, finish drawing at `1f036`, and check 320 fields at `1f052`.
`O:1f060` compares against **15 pages**, then `1f06a` branches back to `1eeb2`.
CD32 has 18 pages. Shared timing therefore needs variant-specific script constants.
Render-side asteroid generation at `O:0330`/`9618` needs the same ownership
investigation that prevented missing CD32 credit asteroids. Other scripted routes
around `O:1f760` and `1fc8c` must be identified separately, not assumed to be this
intro. Music and credit timing remain native unless independent evidence requires
an explicit change.

### Sharing and base-CPU constraints

`tools/reconstruct.py` now requires explicit variant selection (P13B1 below).
Enhanced timing generation remains CD32-only until the OCS ABI and ISA gates pass;
`cd32_runtime.py` retains CD32-specific discovery guards.
The runtime inputs and launcher previously assumed CD32 hashes, names, hunk sizes, patches or Kickstart inputs.
P13A3 adds explicit OCS selection to `runtime_inputs.py` and `amiga/run.sh`, plus
a separate `ocs_runtime.py` locator. CD32 discovery still uses its own patched
converter; OCS uses its native startup relocations and original slave helpers.
Extract variant maps and shared mechanics rather than duplicating whole tools.

The common design is reusable, but the current assembly is not all 68000-safe:
`timing_clock.s`, `timing.s` and `release_buffer.s` use long multiplication;
scene/translation prediction uses long signed multiply/divide; slot helpers use
scaled indexing; flag-saving hooks use `MOVE CCR`; render code has long branches
and eight-plane assumptions. Instrumentation itself has newer-ISA dependencies.
Native math entries `O:2c6c0` and `2c710` are possible base-CPU building blocks,
subject to ABI/rounding tests. `MOVE SR` is legal on 68000 but privileged on later
CPUs: do not substitute it unconditionally for a CCR read.

Share compile-time algorithms for elapsed fields, input history, prediction,
selective state restoration, projectile identities/cooldown handling and frame
statistics. Keep native function/field maps, loaders, palettes, plane geometry,
backend publication and scene scripts distinct. The shared algorithms need
base-CPU versions even when the chosen A500 converter remains the blitter.

### Kalms candidates and sibling evidence

The local Kalms checkout is pinned to commit
`d8ecf79a3325615305dd800ae7704b518e0d9dda`. The two examined four-plane bitmap
routines and hashes are recorded in `manifest/ocs-c2p-candidates.tsv`. Both
`c2p1x1_4_c5_bm_word.s` and `c2p1x1_4_c5_bm.s` assemble with `-m68000` (560 and
744 code bytes respectively). Assembly success is not pixel, speed or integration
validation. “68020 path” here means a proposed longword-write selection, not that
the upstream longword routine inherently requires 68020 instructions.

Their ABI takes width/height/x/y in D0–D3, chunky source in A0 and BitMap in A1.
Width must be a multiple of 32, x byte-aligned, depth at least four and row storage
large enough. The source masks low nibbles. Native OCS bit/nibble order still needs
the independent oracle; duplicating high and low nibbles in fixtures would hide
an incorrect adapter.

Legends of Valour `whdload/c2p.s` selects the word routine on 68000/68010 and the
longword routine through attention-flag bit 1 on 68020+. Its
`docs/performance-patches.md` documents high-nibble/192-byte-stride adaptations,
window alignment, independent pixel checks and CPU-only allocation ownership.
Reuse the dispatch/testing pattern, not those game-specific format changes.

Battlehawks 1942 `docs/c2p.md` records a native delta converter outperforming full
conversion on its A500 workload and an initially wrong pixel oracle hidden by
flat scenes. This supports measuring changed content and checking all colours;
it does not predict Wing Commander's winner. Their Finest Hour supplies examples
of selected 68000/020 math paths; Powerdrome documents Fast RAM/DMA ownership.
Sibling numbers are not Wing Commander measurements. No new upstream download,
vendored converter or runtime implementation is part of phase 13.

### P13A1: byte-identical OCS reconstruction

P13A1 is complete. `tools/ocs_reconstruct.py` generates assembly only under
`tmp/`, assembles 1,210 instructions with `-m68000 -no-opt`, and regenerates the
one-code-hunk container. The resulting **5,324 bytes** match the original slave
exactly (SHA-256 `eec155c946e8a247e2c4811fc2279d476c330f2d1b5797cc0defb35918913913`).
Known code islands are instructions; headers, ROM patch tables, strings and
initial state remain generated data. All three game patch lists are regenerated
with WHDLoad `PL_` macros. The original KickEmu code is retained, not rebased.
Full-file equality preserves its ROM relocation, cache policy, language fallback,
cheats, system/mission options and native unsupported-revision abort.

The selector instructions begin at `OS:115c`, `1166`, `1170` (slave file offsets
`117c`, `1186`, `1190`). Their CRC/list pairs are `116d → 12bc`, `00e8 → 1302`,
`262d → 1348`. Each has eight patches and END. The first two equality branches
converge at `OS:117c`; the final inequality branches to `OS:1470` (abort reason 9).
Only the supplied English `00e8` executable has a verified whole-file SHA.
The other selectors are preserved, but their absent executables have no approved
enhancement map. No enhanced hooks or runtime SHA checks are added by P13A1:
these are **build-time guards** for subsequent work, alongside the unchanged
original runtime CRC selector.

`manifest/ocs-patch-sites.tsv` pins eight original English source windows by
hunk offset, file offset, length and SHA-256. Hunk-0 file coordinates add `002c`;
hunk-3 coordinates add `041e4c`. The protected windows are `O:26a3c` (6 bytes),
`27132` (4), `27740` (4), `272b2` (6), and `O3:0036` (2), `06a2` (2), `06a4`
(4), `1524` (1). The skip-site window includes the skipped instruction; it does
not assert that every protected byte is overwritten. Future added hook sites
need their own guards. Fingerprints contain no executable bytes.

The reproducible gate at `tmp/p13a1-check-final/checks.json` passes two fresh,
identical source/payload/slave/report builds; altered and truncated slave/game
rejections; CD32 input rejection; a real altered-game CRC collision retaining
`00e8`; synthetic inputs with the two unverified CRCs; independent mutations of
all eight protected windows; 12 selector instruction/CRC/target/branch mutations;
and an assembled-instruction sabotage caught by the payload identity check.
Existing outputs, paths outside `tmp/` and symlink escapes are rejected. The
original OCS file set and hashes remain unchanged. Synthetic CRC fixtures do not
stand in for testing unavailable game revisions.

P13A1 executed no emulator, Kickstart or game code. Byte identity is its
preservation proof. The P13A2 functional display contract and P13A3 matched live
boots follow below. CD32 reconstruction and runtime assembly remain unchanged.

### P13A2: native display and allocation contract

P13A2 is complete for the pinned English OCS executable. Evidence combines static
tracing with **isolated execution of original 68000 instructions in Unicorn and
an independently written functional ascending-area blitter model**. It is not a
full game boot, OS scheduling simulation, beam-timing test or performance result.
`tools/ocs_display_check.py` compares native conversion against a scalar pixel
oracle, exercises allocation/free and direct writers, and checks queue ownership.
See [commands and limits](development.md#p13a2-native-display-contract-check).
Offsets use the `O:`, `OD:` and file-base notation above.

#### Pixel layout and bounded native quirks

For source byte `s[y*W+x]`, the displayed four-bit colour is the **high nibble
when `(x+y)` is even, low nibble when odd**. These are two independently meaningful
colours for checkerboard dithering. A solid colour `c` uses byte `c*17`; neither
nibble is generally unused. Plane 0 holds colour bit 0; the left pixel occupies
the most significant bit of its byte. A future Kalms adapter must preserve this
selection rather than feed the original bytes into a low-nibble-only routine.

`O:334e4` computes row bytes `R=ceil(W/16)*2`, per-plane bytes `P=R*(H+2)` and
four-plane region size `4P`. Bitmap pointers at `O:33aea` skip two leading rows;
bitmap Rows remains H. ViewPort height is **H−1** (`O:33970`–`33976`), so the last
allocated logical row is outside the visible comparison. Its native conversion
is incomplete; do not extend display height merely because the allocation fits.
Native descriptors use W/8 and W/16; the checked conversion contract requires
16-pixel-aligned widths and even heights. Surface allocation rounding to even
width alone does not make arbitrary dimensions safe for this converter.

The model reproduces four black pixels at visible `(x,y)=(1,1),(3,1),(9,1),(11,1)`.
The oracle records this exception explicitly; a control without it differs.
**P13A3 confirms this edge quirk in the live FS-UAE blitter result below**;
it is not a real-hardware finding or permission to patch it. All other visible pixels
match the independent nibble selection/packing formula. An odd-height 32×17
control writes beyond the native planar allocation; it is a rejecting control,
not a supported view. P13A3 checks the live 320×128 and 320×200 geometry. C1
must cover other required sizes before preserving or deliberately correcting them.

The 15 fixtures cover 320×200, ×166, ×128, ×16 and 32×16, each with all 256
colour pairs, independent random nibbles and solid white. Each runs against both
destinations, then repeats with changed out-of-image source padding: **45 positive
conversions**. Checks include opposite-buffer preservation, source immutability,
planar allocation guards and no final-stage chunky reads. A mutation of the
native first callback's C mask at `O:32cba` must break the pixel comparison.
The gate also rejects low-nibble-only packing and records the odd-height failure.

At 320×200 the first phase reads source-relative bytes `[-312,64632)`, the second
`[-628,64316)` although the allocated source is only `[0,64000)`. Adjacent Chip
memory is read by the native pipeline, including before the source. Changing
those outside bytes does not change visible output in the checked fixtures.
This is **not** permission to put unmapped or non-Chip memory next to a source:
retain Chip-accessible margins or remove the overreads in a replacement backend.
The harness supplies two rows on both sides and checks all DMA accesses against
its Chip-memory model. These ranges describe reads, not extra native allocation.

#### Descriptors, queue and ownership

Display state at `O:331b8` has region bytes at +0, workspace at +4, display bases
at +8/+c, original dimensions +10/+12, rounded dimensions +14/+16, row bytes +18,
plane bytes +1a, depth +1c, next-draw index +1e, submitted index +20, active flag
+22 and 16 RGB4 entries +24. The allocation order is display 0, workspace,
display 1. At 320×200: R=40, P=8080, region=32320, combined=96960 bytes.

Conversion state `O:324a8` contains surface +0, W/H +4/+6, source +8 and two
668-byte public descriptors +10/+14. Native `O:3257c` populates each descriptor:
W/H +0/+2, W/8 +4, W/16 +8, chunky +c, destination planes **3,2,1,0** +10..+1c,
workspace planes 3,2,1,0 +20..+2c, strip-count-minus-one +30, and an 18-command
stream at +32. Commands are 28 bytes, followed by a zero word; construction is
`O:32646`–`328c6`. Both descriptors share the source and workspace.

| Queue node / callback / flag (O:) | Work and readers | Release condition |
|---|---|---|
| `328c8` / `329e4` → `32c90` / `3291a` | 4 blits per 16-pixel strip; chunky to workspace | First flag cleared after its last blit |
| `328e2` / `32a26` → `32a66` / `3291b` | 8 blits per strip; chunky to selected destination | Second flag cleared after its last blit |
| `328fc` / `32dba` → `32dca` / `3291c` | 18 commands in groups 4+6+4+4; destination/workspace ping-pong, no chunky reads | Third flag cleared in final continuation |

`O:3299c`–`329de` initializes nodes and calls QBlit (graphics vector −276).
Callbacks return −1 for another continuation and 0 when finished. The functional
model completes each blit before invoking its next continuation; this tests the
native instruction/control sequence, not actual interrupt scheduling.

Submission `O:3291e` waits only for the first two flags (`32976`–`32984`) before
returning: **the chunky source can be drawn again while the final phase runs**.
Destination, workspace, final command stream and queue nodes remain owned until
`O:32990` retires the third phase. Entry `O:3260a` waits there before `O:33426`
rotates indices and resubmits. The ownership test leaves stage three busy and
rejects a new-frame attempt before rotation; releasing it permits the wait.
The two source-reading phases must both finish before changing/freeing source.
Descriptors and node metadata are CPU-read, so public memory is sufficient;
source, workspace and destination are DMA-read and must be Chip-accessible.

`O:3293a`–`32942` also waits for field counter `OD:77fe` to differ from saved
`O:32916`. This is scheduling delay, separate from conversion service time.
Do not charge it to blitter throughput or remove it in a matched native baseline.

Final completion `O:32dfe`–`32e2e` clears the third flag at `32e02`, uses the
publication nesting guard `OD:77ae`, and calls `33442` → `3385a` → `33a6e` →
`33aa8` (COP2LC), then saves the field counter. `33426` sets the submitted index
from next-draw and advances next-draw modulo two. The functional check verifies
that publication selects the submitted buffer, after all 18 final blits, and
that the flag clear precedes COP2LC within the same callback. Flag completion
alone does **not** mean the beam has displayed the new picture. Actual Copper
latch deadline, nesting/deferred cases and tearing remain live gates.

#### Display allocation and safe release inventory

`O:33b60` requests flags `10003` (CLEAR|CHIP|PUBLIC); `33b76` requests `10001`
(CLEAR|PUBLIC). Public is not a guarantee of Fast RAM. `33b94` reaches AllocMem;
`33c8e` records up to 120 pointer/size pairs, and `33c48`/`33cbc` untrack before
FreeMem at `33c80`/`33c88`. `33c6a` drains the registry during overall cleanup.

| Allocation / owner | Size and consumers | Native path and safe-release requirement |
|---|---|---|
| Chunky surface / surface descriptor | even-rounded W × H, Chip for conversion; CPU drawers plus first two QBlit phases | `31dc4` selects Chip, `31da8` public, `31de2` allocates; `32476` frees source and row table, clears pointers. Caller must retire both readers before free/reallocation. |
| Row table / surface | 4H public bytes; CPU-only biased row pointers | `31e10`–`31e22`, released with source at `32476`; no remaining CPU drawer may reference it. |
| Two conversion descriptors / conversion state | 2×668 public bytes; callback/CPU command readers | `324c0`/`324e0`; `32526` calls `32638` to wait final conversion and close view before freeing both. |
| Two displays plus workspace / display state | 3×4R(H+2) Chip bytes; blitter reads all, display DMA reads published planes | `3323e`–`33268`; `3327c` closes/restores graphics via `334b6`/`33674` before releasing the allocation. Retire conversion and detach display before reuse/free. |
| Two BitMaps / native inline storage | At `335b4`, `335dc`; four plane pointers each, stride 40 bytes | `33aea` rebuilds; storage stays in code allocation. DMA reads the pointed-to Chip planes, not these CPU-only structs. |
| Two generated Copper lists / graphics.library | OS-sized Chip lists, references at `3360c`/`33610`; Copper reads instruction data | `339c0`/`33a26` use MakeVPort/MrgCop; rebuild waits two fields (`339fc`, `33a00`) before FreeCprList at `33a12`. View teardown `33872` detaches/reloads view, waits two fields (`33898`, `3389c`), frees viewport/list storage (`338a8`, `338c0`). |
| Hidden Intuition screen bitmap / display setup | 615 Chip bytes; native screen/display setup | `336fc`–`3370c` allocate, `3372e` opens screen, `33774` closes, `33780` frees. Keep backing memory until CloseScreen has detached its consumer. |
| Sprite data / native sprite slot | 4×(spriteHeight+1)+8 Chip bytes, control/data/terminators; sprite DMA | `31ca6` allocates, `31cca`–`31ce2` fills, `31cea`–`31d20` binds via ChangeSprite. CPU table owns allocation. `31bf2` frees blocks; `31b7c` calls FreeSprite. Detach old binding and retire DMA before freeing; full exit-order/field confirmation remains C4–C5/E2. |

The inventory is for the display/conversion subsystem; it is not a whole-game
DMA audit. Audio remains a separate native subsystem and its allocations must
remain untouched by the later display-memory move. OS-generated Copper/screen
allocation sizes and simultaneous Chip high-water usage require live discovery.
Sprite free code has no explicit WaitTOF at the block-free site; do not mistake
this static free-path identification for proof of safe live exit ordering.

The allocation check executes native allocation/registry/free instructions with
host AllocMem/FreeMem stubs, exercising 96960 Chip bytes, two 668-byte descriptors,
64000+800-byte surface/table, public surface allocation, even-width rounding,
biased row pointers and full cleanup. A forced row-table allocation failure
returns zero but leaves the previously allocated source owned by the surface;
explicit `32476` cleanup reclaims it. Native partial setup is not transactional.
OS initialization/teardown and field services are stubbed and reported as such.

#### Direct planar writers and remaining live checks

`O:33348` clears all four planes, including pad rows, in the next-draw buffer
when active. `333b4` clips unsigned x/y, adds two row strides and writes bits
0–3 with MSB-first masks. Native execution checks all 16 colours, three rejected
coordinates and a full-region colour clear. Known clear callers include `O:bba`
and `3039c`/`303b4`; future changed-block history must account for these writes,
view rebuilds and palette changes, not just chunky source equality.

The check also builds both BitMaps and exercises the actual final publication
path against synthetic graphics/Copper metadata. Functional gates pass; actual
beam deadlines and full sprite detach/exit ordering are not established by that
isolated gate. P13A3 below confirms the live pixel edge, allocation placement,
name-frame completion/publication and original/reconstructed boot agreement.
Measured baseline follows in **P13A4**; full transition/teardown ownership remains
part of C4–C5/E2. No backend is selected and no game/slave runtime bytes change.


### P13A3: OCS launcher and matched live baseline

**P13A3 is complete.** The launcher selects OCS and CD32 explicitly, with separate pinned runtime
archives, drawers, slaves and KickEmu ROM inputs. The nominated OCS machine is
PAL 68000/OCS, 512 KiB Chip and 4 MiB true Fast RAM, no trapdoor slow RAM. It uses
the shared directory-drive host boot and the unchanged slave's Kickstart 1.3.
No OCS runtime patch, backend selection or performance measurement is included.

**Live layout.** `ocs_runtime.py` finds the native countdown signature at
`O:34082–340b0`, verifies all four DOS segment allocations/links, and checks the
entry relocation `O:0002` → `O3:1476` and A4 setup `O3:14d0` → `OD:7ffe`.
The patched helpers `O:272b2` → `OS:138e` and `O:26a3c` → `OS:13a0` identify the
slave independently; its header must match. A preload copy fails these checks.
All six snapshots verify the discovered layout and the live A4 register.
Eight negative cases reject bad sizes, links, entry/A4 relocations, either slave
helper, the slave header, and a preload-only snapshot.

**Native input and checkpoints.** The route changes no guest instruction or data;
only debugger-native keyboard events enter the normal input queue. All addresses
below are code-hunk offsets (`O` file offsets add `2c`).

| Checkpoint | Native site and route |
|---|---|
| Origin | Input poll `180c8`; capture, then Escape |
| Title motion | Intro entry `1edde`, release Escape; capture `1efb0` with D2 = 100 |
| First credits | `1f03c`, after its first picture submission; then Escape |
| Campaign menu | Enter `1f396`, release Escape, capture ready poll `1f43c` |
| Simulator | Select Vega, reach flight loop `0694`, capture completed iteration `06c2` |
| Name prompt | `16c1a` → input poll `16992`; retire pending final conversion at `32e2c`, return to `16992`, capture two fields |

The menu's initial pointer is (159,99), over the absent Secret Missions option.
Native Up (`4c`) moves it into Vega's rectangle (45,51)–(279,89); the harness waits
for y ≤ 80, releases Up and presses Return (`44`). At `1f44e`, selected index D2
must be zero. This is why reusing the CD32 Return-only tape failed. The simulator
then proceeds without further input through death to the name question. No name
is entered. Ordinary flight and the separate cinematic `1f760` route are distinct.

**Memory and pixels.** Native Exec MemHeaders report attributes `0005`
(PUBLIC|FAST) and `0003` (PUBLIC|CHIP), with the Chip upper bound at 512 KiB.
The four game hunks and A4 are in the true Fast allocation. At each checkpoint,
the chunky source, both display regions and the distinct shared workspace are
aligned, non-overlapping and entirely in Chip RAM. Four planes retain the A2
row/padding geometry. This is a successful nominated configuration, not a minimum
memory measurement or support claim for other CPU/memory setups.

The completed name frame independently matches all **63,680 visible pixels**
(320 × 199), covering 14 colour indices. The source uses both nibbles in the A2
checkerboard order; low-nibble-only packing fails. The four model edge pixels
(1,1), (3,1), (9,1), (11,1) are also black in the live blitter result although the
source predicts colour 6 there. Thus this scoped A2 quirk is now **confirmed in
FS-UAE**, without cropping or silently correcting it. The three completion flags
are clear before the name snapshot; reaching `32e2c` proves the native final
completion/publication route ran. Two captured fields then show the text prompt.
This does not establish a universal beam deadline or sprite teardown ordering.

**Capture instrument.** The previous debugger used uninitialized host framebuffer
storage (`src/od-fs/fsvideo.cpp`), exposing heap bytes at screenshot column 752.
Paired runs had identical game/Chip state but differed in that exported border.
The local `--ocs-pixels` build initializes host display storage and uses PNG for
multi-field captures, avoiding the old lossy JPEG path. Shared files and guest
execution are unchanged. The gate compares the entire 754 × 576 RGB screenshot;
no border exclusion, ignored state bytes or pixel tolerance is used.

The six paired checkpoints pass with **zero differing state bytes or pixels**:
289,816 game-hunk bytes, 524,288 Chip bytes and 434,304 RGB pixels per checkpoint.
The old/new screenshot-instrument controls also preserve all six game/Chip
snapshots exactly. The final report is `tmp/p13a3-compare.json`. Additional negative fixtures
reject pending conversion, a changed **published** pixel, a Fast DMA source,
overlapping allocations and a wrong row stride (`p13a3-negative-checks-2`).

Evidence remains under `tmp/`: final original/reconstructed captures are
`p13a3-original-pixels` and `p13a3-rebuilt-pixels`; the rebuilt slave is
`p13a3-reconstructed`. Automatic discovery is `p13a3-layout-final`; input isolation
and overwrite refusal are `p13a3-input-check-2`. Reproduction is in
[development](development.md#p13a3-ocs-launcher-and-live-layout-gate).

Limits: these are emulator state/pixel checks with debugger pauses, not a speed
benchmark or real-hardware visual acceptance. Full intro repetition, every view,
sprite detach/release, exceptional exits and minimum RAM are not certified here;
their existing C4–C5/D4/E2 gates remain. The separate P13A4 baseline is recorded
below. CD32 E1/phase 12 remain paused.

### P13A4: short native OCS baseline

**P13A4 is complete on the nominated emulator model.** The pinned original OCS
slave runs unchanged on PAL 68000/OCS, 512 KiB Chip and 4 MiB true Fast RAM. Two
250-field windows cover the first asteroid-credit page and simulator flight with
Space held to fire. Each lasts **5.007972 emulated seconds**. These are baseline
measurements, not improved OCS performance or real-hardware measurements. No turn,
CPU matrix, CPU converter, pacing removal or backend selection was added.

#### Clock and observer gate

The preset's numeric `7093790` frequency reaches an overflowing integer expression
in the pinned emulator, producing **231** internal units per CPU clock. The new
measurement-only `OCS_STOCK_CLOCK=1` uses zero frequency/multiplier to select the
core's native PAL 68000 unit, **256**. The reporter rejects the old unit; the
initial `tmp/p13a4-on` capture is excluded. A3's earlier paired state/pixel gate
remains valid for its matched configuration, but must not supply performance
numbers for the corrected stock-clock baseline.

The independent field clock is 28,375,160 / 8 colour clocks/s, with 512 internal
units per colour clock. All 250 intervals in each window are exactly
227 × 313 × 512 units: **49.920409 fields/s**, not an assumed exact 50 Hz. No host
wall-clock time enters the results. Instruction charges account for 99.893% and
99.891% of elapsed time; the remaining 5.36/5.44 ms per whole window is outside
recorded instruction bodies, including dispatch and boundary fragments. It is not
silently charged to drawing, DMA service or a guessed idle category.

`ocs_observer.inc` observes the cycle-exact 68000 dispatch and actual plane-0 DMA
fetches without guest writes or emulated cycle charges. `ocs-window` begins at the
next field edge and freezes the entire window after 250 fields. There are no
interior debugger stops, input changes or Barto profiles. Observer-off disables
PC/scoped-cost/source/DMA observations while retaining identical field-window
bookkeeping. Across both boots, **all eight checkpoints match every game-hunk byte,
all 512 KiB Chip RAM and every full 754 × 576 RGB pixel**. Window clock edges and
native counters also match exactly. No crops, masks or tolerances are used.

The DMA observer records each field's actual display allocation independently of
native publication PCs. Each window has 250 single-buffer fields, with no observed
within-field buffer switch. Its 29/27 new-buffer transitions match the native
publication sequence exactly, with no unmatched interior or pending final picture.
This is a scoped counter agreement, not a universal no-tearing or beam-deadline
claim. Eleven negative controls reject bad CPU clock units, missing world counts,
DMA fields, publications or conversion stages, bad field durations, an unfrozen
denominator, an invalid change census, missing instruction accounting, and changed
or truncated state/pixel bytes.

#### Measurements

| Metric | Asteroid credits | Simulator flight/fire |
|---|---:|---:|
| Displayed new pictures / 250 fields | 29 | 27 |
| Displayed pictures/s | **5.79** | **5.39** |
| Completed world updates / updates per second | 28 / **5.59** | 27 / **5.39** |
| Display interval mean / p50 (ms) | 171.70 / 180.29 | 185.68 / 180.29 |
| Display interval p95 / p99 / maximum (ms) | 220.35 / 234.97 / 240.38 | 220.35 / 235.37 / 240.38 |
| Complete display intervals | 28 | 26 |
| World scope mean / p95 (ms) | 44.93 / 102.72 | 34.03 / 47.20 |
| Drawing through pre-submission mean / p95 (ms) | 105.75 / 121.61 | 90.50 / 98.80 |
| First QBlit submission to final completion mean / p95 (ms) | 55.99 / 60.28 | 92.80 / 95.32 |
| Sum of three conversion stage spans mean (ms) | 53.79 | 88.73 |
| Inter-stage queue/scheduling residual mean (ms) | 2.20 | 4.07 |
| Explicit field-wait span mean (ms) | 0.00592 | 0.00592 |
| Publication to first new-buffer DMA mean / p95 (ms) | 18.34 / 25.66 | 15.45 / 21.46 |
| Source bytes changed, mean / maximum | 1.152% / 3.833% | 0.438% / 1.148% |
| Changed 32-byte source blocks, mean / maximum | 5.248% / 11.094% | 2.133% / 4.550% |

The world/drawing/submission counts need not match at field-bounded edges. Complete
conversions number 29/27; comparable source pairs number 28/26. Drawing spans
number 28/26. Full means, p50/p95/p99/maxima and sample counts are in
`tmp/p13a4-report.json`. Short-window percentiles describe these samples only.

The CPU's measured blitter-poll instructions consume **16.52/15.38 ms total** over
the respective five-second windows; field-spin instructions consume 0.106/0.099 ms.
The native completion-flag wait scopes average 0.0273/0.0180 ms over 116/108 calls;
the maximum is 1.087/0.0180 ms. These include the wait wrapper and any preemption,
not just idle CPU time. The explicit field-clock check does not meaningfully stall
this workload. That observation does not authorize removing native synchronization.

Drawing, world work and final asynchronous conversion **overlap**. Their inclusive
scope times must not be summed as a frame budget. Stage service here means the
elapsed native callback stage, including contention, blitter polling and internal
continuation/interrupt dispatch. It is not isolated DMA throughput. The residual
separates initial/between-stage scheduling from those stage spans; the explicit
field wait can overlap service, so it is reported without adding it a second time.
No converter or RAM-placement crossover follows from these figures.

#### Probe ownership and offsets

All game addresses below are OCS code-hunk offsets; file offsets add `2c`.

| Observation | OCS site / meaning |
|---|---|
| World | `O:02be` entry with saved-return/SP matching; `02dc` after update-counter increment, reconciled against `OD:88da` |
| Drawing/composition | `O:02e6` entry to `3260a` pre-conversion entry; includes clear, scene drawing, text/HUD/composition on the selected route |
| Source change | `O:32626`, before submission; source/size from `O:324a8` state; compare every native source byte and each 32-byte block with the previous submitted source |
| Queue submissions | `O:329de`, three native QBlit calls per complete conversion |
| Service stages | `O:329e4`→`32a0a`, `32a26`→`32a4a`, `32dba`→`32e02` |
| Explicit field wait | `O:3293a`→`32944`; CPU spin instructions `3293e`, `32942` |
| CPU blitter polling | Native `BTST D0,(A3)` / backward-branch pairs within `O:32a66`–`32db8`; individual instruction charges, excluding surrounding setup |
| Completion wait | `O:3407e` entry/return; `32990` final-reader retirement also recorded |
| Publication | `O:33aa8` COP2LC write, followed independently by display DMA from one of the two regions in `O:331b8` |
| Scene positives | Asteroid routine `O:9618` reached; flight input calls `O:06fa` 27 times and the gun routine `c748` four times during held fire |
| Memory | Exec MemHeaders at field edges and native allocation-return/free-entry landmarks `O:33b98` / `33c88`; no such allocator landmark occurs inside these windows |

#### Memory and limits

The native KickEmu pools have 523,232 Chip bytes and 713,496 Fast bytes. All 251
free-memory samples per window agree internally (no sampled fluctuation).

| Window | Native Chip pool used / free | Native Fast pool used / free |
|---|---:|---:|
| Asteroid credits | 404,040 / 119,192 bytes | 711,832 / 1,664 bytes |
| Simulator flight/fire | 381,704 / 141,528 bytes | 712,448 / 1,048 bytes |

These used values are the **sampled window high-water** marks. Relative to physical
configured RAM, 1,056 Chip bytes and 3,480,808 Fast bytes lie outside these native
pools. Subtracting only native free bytes from physical capacity gives
405,096/382,760 Chip and 4,192,640/4,193,256 Fast bytes unavailable to this allocator.
That includes reservations and preload outside the native pool; it is not a claim
that game allocations consume nearly 4 MiB or that 4 MiB is the minimum. Boot-wide
allocation peaks, allocator-failure behaviour and minimum RAM remain C4/E2 work.

The current native code couples much world progress to drawn pictures. These
windows measure that baseline; they do not prove the later 10 Hz scheduler can or
cannot sustain its budget. They cover one first-credit asteroid sample and early
simulator flight/fire, not every combat load, view, turn, intro repeat or hardware
configuration. P13B3 is next only on request; CD32 E1/phase 12 remain paused.

Accepted evidence: `tmp/p13a4-stock-on`, `tmp/p13a4-stock-off` and
`tmp/p13a4-report.json`; instrument `tmp/p13a4-debugger-final/fs-uae`, SHA-256
`c634549a6f443dfbe1287f597e88cd447559e01de94ae9d652b3b572fd445c2d`.
[Reproduction commands](development.md#p13a4-short-native-ocs-baseline).


### P13B1: compile-time variant definitions

P13B1 is complete. `tools/variants/cd32.py` and `ocs.py` separate verified English
input identities, stored/allocated hunk layouts, locator signatures, native
entry points, A4 fields, object bounds, bitmap layout, scene constants and hooks.
All addresses in these maps are hunk offsets (or explicitly named file payload
bases); A4 fields are signed displacements from data hunk +`7ffe`.

| Definition | CD32 | OCS |
|---|---|---|
| World / draw / finish entry | `E:02a8 / 02e4 / 0c40` | `O:02be / 02e6 / 0b80` |
| Asteroid entry | `E:98a2` | `O:9618` |
| Field clock | `D:7f02`, A4 −252 | `OD:77fe`, A4 −`0800` |
| World / draw counters | `D:914c / 9150` | `OD:88da / 88de` |
| Position / velocity / class | `D:919a / 9d6c / 96fe` | `OD:8928 / 94fa / 8e8c` |
| Native dispatch slots | 0–60 | 0–60 |
| Planes / leading rows | 8 / 0 | 4 / 2 |
| Chunky colour | byte | high/low nibble by checkerboard parity |
| Title updates / credit pages | 296 / 18 | 296 / 15 |

Names denote roles, **not identical calling conventions**. OCS dispatch bounds
are not proof of CD32's 64-slot prediction storage layout. That size is deliberately
absent from the OCS map. OCS enhanced timing hooks are also absent and requesting
them rejects explicitly. Its verified original audio/clear hooks and three
revision selectors remain separate from CD32's timing/presentation hook lists;
A1's displaced-site manifest still guards all eight original English patches.
German and unavailable OCS revisions gain no enhancement support.

The first shared pieces are DOS segment-chain traversal, explicit-CPU static
inventory, definition-to-assembler equates, and the existing guarded patch
emitter driven by the CD32 hook map. Intro world/draw/finish/asteroid calls,
clock/counter accesses, title thresholds and the geometry-history slot bound
consume compile-time symbols. Kalms specialization consumes the CD32 bitmap
width and supported heights. Equates add no bytes or runtime variant branches.
The locators keep their different native signature/relocation/helper checks.

This is incremental extraction: remaining CD32-only native call ABIs, prediction
fields, patch-resume/displaced-instruction recipes and device publication stay
in their existing adapters until their OCS counterparts are verified. P13B2 below establishes
68000 execution safety for the shared units; D1 owns the full OCS timing/side-effect map. Merely
assembling OCS equates does not certify the shared runtime algorithms for 68000.

The four CD32 outputs compare byte for byte against builds made from `495542d`
before this refactor: release **43,544 bytes**, timing **33,584**, renderer
**12,076**, original **7,728**. Release SHA-256 remains
`fdd92fbbda8689e3ec3ab2353d5baa866859469a684026841fd71527e0a6de8d`.
Original OCS remains **5,324 bytes**, SHA-256
`eec155c946e8a247e2c4811fc2279d476c330f2d1b5797cc0defb35918913913`.
The A1 repeat/identity/revision/site/ISA/output-preservation checks pass.
Both explicit static-analysis routes pass; retained live snapshots still locate
correctly. Wrong allocation sizes, unterminated chains, opposite-variant dumps,
missing/invalid variant selection, a CD32 build given the OCS slave and an OCS
release request all reject. Changing the consumed field-clock map and rebuilding
also fails the byte-identity gate; changed/truncated binary controls reject.

Existing focused CD32 gates pass: eight installer/option cases with full code and
register/CCR checks, 12 intro clock schedules, 96 pose/camera/restoration cases,
and 72 whole-output native converter comparisons on 020/040. No game boot was
run and no performance result is inferred. The subsequent B2 ISA gate is below. See the
[reproduction commands](development.md#p13b1-compile-time-variants-and-byte-preserving-sharing).


### P13B2: shared 68000 execution safety

**P13B2 is complete.** `shared_cpu.py` selects instruction sequences at build time
for the owned assembly units. CD32's accelerated source is returned verbatim;
there is no runtime variant test in a hot loop. The 68000 alternative uses
`shared_math.s` and is also executable in user mode on the tested 020/040 models.
The builder consumes the selector for timing, publication and diagnostics.
The OCS enhancement build still rejects: this work supplies reusable mechanisms,
not unverified OCS native offsets or hooks.

#### Arithmetic, addressing and flags

| Mechanism | Base-ISA contract |
|---|---|
| Long multiply | Two word products give the low 32 bits of a signed/unsigned long times the bounded positive word factor (10, rate 50/60, or prediction fraction through 80). Wrap is intentional. |
| Signed division | Divide the unsigned magnitude in two word stages, then restore the sign. Positive rate is 50/60; `INT_MIN` is supported; truncate toward zero. Division by zero or a negative rate is outside this contract. |
| Prediction/translation | Execute the existing quotient/remainder algorithms, including sign normalization of carried remainders. No native math routine or unverified OCS math ABI is reused. |
| Indexed operands | Preserve scratch address registers with MOVEM; ADDAs sign-extend word indices before repeated addition. Both operands of memory-to-memory moves are handled. Address computation leaves all flags unchanged. |
| PC-relative tests | LEA plus indirect TST/CMPI avoids the newer-CPU PC-relative forms; preserve the scratch address register and the test's resulting flags. |
| Far native calls/jumps | Construct a tail-dispatch frame with the original registers, flags and callee argument-stack layout. The native entry/ABI still belongs to its variant adapter. |
| Branches | Use word branches after expansion. Vasm must reject out-of-range branches/PC references; the eventual linked OCS image must pass that check too. |
| Condition-code saves | Capture C/V/Z/N with Scc and X with ROXL, build a word and restore the incoming CCR before returning. No SR read/write and no supervisor-mode assumption; all registers are preserved. |

Multiply/divide helpers preserve D4/D5 and every other non-destination register;
their CCR is scratch. Audited callers consume the result, then ADD/CMP or another
flag-setting instruction before a conditional decision. They do not depend on
long-MUL/DIV overflow flags. These are bounded timing/prediction helpers, not a
general 68020 instruction emulator. Unreviewed arithmetic operands, unsupported
expanded operations and stack-relative expanded operands reject. New source
forms still require an ISA audit and executed contract checks.

#### Execution-path audit

The 13 audited units are `timing`, `timing_clock`, `timing_player`, `timing_input`,
`timing_presentation`, `timing_scene`, `timing_intro`, `timing_translation`,
`timing_projectiles`, `timing_scene_slots`, `view_regions`, `release_buffer` and
`frame_stats` (all under `whdload/`). This includes the `timing_patchseg` startup
wrapper, pause/autopilot rebasing and exceptional `timing_bad` exit path, input
interrupt and projectile-return flag saves, publication interrupt early/future/
late/locked/success paths, recorder disabled/full paths, allocation and flush.
All conditional arms assemble; execution is scoped below, not claimed for every
adapter/native callback. CD32 release-option/header code, eight-plane converters,
cache policy and original slave code remain variant-specific. The OCS original
startup/interrupt/exit paths retain the identical A1 reconstruction.

Per-unit assembly fixtures use explicitly reported external placeholders and
CD32 field definitions to cover the existing source, **not** invented OCS hook
maps. The native publication boundary in the executed IRQ fixture is an RTS mock
for CD32 `E:33a12` (file `33a3e`); it checks the shared wrapper, not OCS Copper or
blitter completion. The recorder fixture keeps CD32's `D:7f02` field counter and
synthetic beam reads. P13B3 still owns the OCS recorder/observer interface; C5 owns
OCS publication, and D1–D4 own native timing/input/prediction integration. Full
OCS linking must resolve real callbacks and check final branch reach, stack and
memory budgets. No enhanced OCS boot, C2P choice or performance claim follows.

#### Gate results

`tmp/p13b2-accepted/report.json` records:

- **52 base-ISA assemblies:** 13 complete units under four buffered/diagnostic/
  verification profiles, using the actual FSTAT macro.
- **10,400 arithmetic/scheduler samples**, plus modal/stall edge checks: full
  signed-long boundaries, deterministic random values, PAL/NTSC rates, fractions
  through one tick plus two fields, signed carried remainders, field wrap and
  large-stall modulo accounting. Independent integer arithmetic/elapsed-time
  ledgers check the 68000 implementation on 000/020/040 and the original on 020/040.
- **7,680 operand/flag cases:** all 32 XNZVC combinations, user/supervisor modes,
  positive/negative word indices, long indices, two memory operands, PC-relative
  tests, long branch alternatives and far call/tail-call stack contracts. Compare
  registers, observable memory and flags against the accelerated instructions.
- **810 wrapper cases:** recorder stable/torn beam reads and actual publication
  wrapper idle/future/late/locked/success exits. Native publication is mocked;
  register/CCR and stack preservation are checked on the three models.
- **Seven rejecting controls:** native long multiply, scaled indexing and CCR
  reads fail the base assembler; unknown division/stack forms reject; deliberately
  lost X and a wrong arithmetic factor fail their independent expected results.

Four CD32 binaries are byte-identical to P13B1: release 43,544 bytes, timing
33,584, renderer 12,076, original 7,728. Original OCS remains 5,324 identical bytes.
The existing variant rejection/locator, eight installer/option, 12 intro-clock
schedule and 96 intro pose/camera/restoration checks also pass. No FS-UAE/game
run was required. These are functional CPU-model results, not cycle benchmarks
or real-hardware acceptance. Stop at B2; B3 starts only on request.

### P13B3: shared instrumentation and validation interfaces

**P13B3 is complete as an instrumentation-interface gate.** `frame_schema.py`
now owns the WCFS/WCDS binary formats, while the explicit-variant
`instrumentation_check.py` selects the existing CD32 recorder/observer gate or
the OCS native observer adapter. The OCS guest recorder is assembled and executed
in CPU tests, including native-data/event replay; it is **not installed into the
OCS slave**. Native OCS hooks, IRQ integration, allocation and measured guest
recorder cost remain responsibilities of the later components that install them.
There is no new converter, timing policy, release or emulator run in this step.

#### Shared format and OCS event ownership

Existing CD32 event IDs 1–16 and WCFS/WCDS layouts are unchanged. WCFS adds
17 (`render_complete`) and 18 (`native_publication`). OCS exports use the
independent field edges and colour-clock samples from the retained A4 observer;
the report explicitly labels them **host observations, not guest WCFS captures**.
WCDS contains actual first DMA of a newly displayed OCS buffer, with its matching
Copper publication. The CD32 adapter retains its existing publication-time ledger
and early-VBL checks. A shared wire format does not make those two timestamp
sources identical; do not feed the OCS export to the CD32 cost summariser.

| OCS event | Code-hunk offset | File offset | Check |
|---|---:|---:|---|
| World entry / completed update | `02be` / `02dc` | `02ea` / `0308` | Completed event agrees with `OD:88da` counter delta |
| Drawing entry | `02e6` | `0312` | Agrees with `OD:88de` counter delta in the native default windows |
| Rendered source ready, before conversion | `3260a` | `32636` | Entry/completion ordering, including window-edge work |
| Conversion entry / first blitter stage | `32626` / `329e4` | `32652` / `32a10` | Native three-stage queue checks retained |
| Final blitter completion | `32e02` | `32e2e` | Publication must use the same completed buffer index |
| Copper publication | `33aa8` | `33ad4` | Aligned Chip pointer, reconciled with independent plane-0 DMA |

The field clock is `OD:77fe` (file `41146`, A4−`800`), not CD32's `D:7f02`
(file `41f4a`, A4−`fc`). Plane-0 allocations and plane extent come from
`O:331c0`/`331c4`/`331d2` (files `331ec`/`331f0`/`331fe`). Every observed fetch
must fall within the named buffer's plane-0 range. No CD32 line-4–16 deadline or
AGA fetch assumption is transferred to OCS.

`native_validation.py` shares strict hunk comparisons, actual MEMF_CHIP extent
and non-overlap checks, and variant-selected pixel decoding. OCS retains four
planes, checkerboard nibbles, two leading rows and the four independently verified
black edge pixels. CD32 retains eight planes and byte colours. Its pixel fixture
also agrees with the existing independent NumPy packing oracle. Native revision
locators and OS memory-header traversal remain in their existing variant adapters.

#### Callable recorder contract

`recorder_source.source(variant, capacity)` reuses the existing owned
`frame_stat` body, selecting the variant field operand and B2's 68000 lowering.
`recorder_window.s` adds begin/freeze entry points without borrowing a CD32
resload pointer, allocator or publication hook. Default capacity is 2,048 events:
8,208 bytes of caller-owned Fast storage; the OCS callable code/state is 688 bytes.
These are component sizes, not a measured installed-game memory requirement.

Begin receives the buffer, variant data hunk and nominal 50/60 Hz. The caller
must validate aligned, disjoint Fast storage and its lifetime, and serialise all
calls on one task. Null pointers or invalid Hz disable recording. The first active
sample establishes the epoch without emitting an event. Subsequent calls preserve
all registers and CCR, including X, in user and supervisor modes. Freeze disables
recording before writing a header for the completed prefix; no disk I/O occurs.
The buffer fills once. Consumers must reject a saturated window or nonzero
`frame_stats_dropped` instead of silently accepting incomplete evidence.

A timestamp gets at most four attempts to reconcile the field counter and two
beam reads; exhausting these increments the dropped-sample counter and returns.
This bounds the diagnostic loop. CPU execution checks observe at most 118
instructions on the tested OCS paths, including fourth-attempt success; stable
replayed events use 79. These are **instruction counts, not cycle costs or A500
performance measurements**. IRQ callers must not share this main-task recorder;
OCS IRQ publication remains a separate host observation until its later integration.

#### Accepted evidence and limits

The retained A4 on/off captures are revalidated with the new interfaces. Across
eight checkpoints, all native hunks, Chip bytes and full RGB pictures remain
exact; the 63,680-pixel name-screen oracle and its edge/nibble controls pass.
Matched field edges and counters have zero emulated-cycle difference. This bounds
the **read-only host observer's emulated effect**; it measures neither host wall
cost nor the future guest recorder's runtime overhead.

| 250-field window | World ticks | Draw entries | Rendered pictures | Publications | Actually displayed |
|---|---:|---:|---:|---:|---:|
| Asteroid credits | 28 | 28 | 29 | 29 | 29 |
| Simulator/fire | 27 | 27 | 27 | 27 | 27 |

Both windows begin with drawing already underway; asteroid drawing finishes before
the end, while flight drawing is pending at both edges. These boundaries explain
the distinct counts; a submission is never counted as actual display. All 500
observed fields contain one display allocation, and the 56 new-buffer changes
match completed-image publications. The original A4 11 rejecting controls remain;
five additional controls reject bad DMA addresses, Fast Copper pointers, wrong draw
counts, missing render completion and publication of the wrong completed buffer.

The OCS recorder passes all 32 CCR values in both privilege modes on 68000/020/040;
the shared accelerated version passes on 020/040 (320 flag/lifecycle cases total).
Capacity, freeze, null setup, PAL/NTSC, field wrap, each retry-success position and
repeated torn/advancing-clock failure pass. Replaying 230 asteroid and 216 flight
records with captured OCS data produces byte-identical WCFS on all three models
(1,338 emitted records). Deliberately poisoning the CD32 field location does not
affect OCS. Wrong-clock and missing-second-beam-read recorder mutations are
rejected, as are 16 shared schema/state/pixel/allocation controls.

Retained CD32 PAL buffered/unbuffered and NTSC reports are identical before/after
the parser extraction. The independent CD32 gate still matches all 657 publications
in its held-turn capture (0.00113 ms elapsed-time difference). Fresh CD32 release
and original OCS builds remain byte-identical to B2. Evidence is in
`tmp/p13b3-gate/`, `tmp/p13b3-ocs-gate/`, `tmp/p13b3-cd32/` and
`tmp/p13b3-cd32-parser.json`; derived exports, assembled components and binaries
remain in `tmp/`. Later live guest integration still needs its own overhead,
allocation/failure, native ABI and IRQ checks; these CPU replays do not close them.
The following P13C1 gate adds experimental converter components without installing hooks.


### P13C1: experimental four-plane converters

**P13C1 is complete as a component correctness gate.** `tools/ocs_c2p.py`
verifies both sources in `manifest/ocs-c2p-candidates.tsv` before assembling the
owned `whdload/ocs_c2p.s` adapter with Kalms' unchanged word-write and longword-write
routines. Generated source, binary, listing and reports stay in `tmp/`. Standard
OCS/CD32 builds do not include these components; native QBlit remains unchanged.
There is no automatic CPU/backend selection or new live emulator run in this gate.

#### Conversion contract and native view coverage

The adapter stages one row into 320 bytes of private stack storage, selecting the
high nibble at even `(x+y)` and the low nibble at odd `(x+y)`. It supplies the
resulting four-bit colours to either Kalms leaf with height one. This shares the
format adapter without changing the upstream shuffle, needing a whole-frame
copy, or importing another game's stride/nibble assumptions. Row one retains the
four native black pixels at x=1,3,9,11. Both candidates incur the staging pass and
per-row call overhead: **C2 must measure the complete adapter**, not just Kalms'
leaf. No speed or CPU/memory crossover claim follows from instruction execution.

| Verified source | File offset | Meaning for this component |
|---|---|---|
| `OD:00c4`, `00e4`, `00f4` | `039a0c`, `039a2c`, `039a3c` | View rectangles select 320×200, 320×166 and 320×128 |
| `O:0c34`, `0c9e`, `32554` | `00c60`, `00cca`, `32580` | Bind the selected native surface and copy its width/height |
| `O:334e4` | `33510` | Row R = ceil(W/16)×2, plane P = R×(H+2), depth four |
| `O:33aea`, `33970` | `33b16`, `3399c` | Plane pointers skip two rows; displayed height is H−1 |

The pinned executable and exact rectangle values are checked in the test.
Native source rows are dense W bytes. The 320×16 fixture is a synthetic minimum
height check, not evidence that the title resizes its bitmap; the earlier title
parameter wording is corrected above. The CPU contract covers all even heights
16–200 and all 32-pixel widths 32–320. Widths 16,48,…,304 return a native request
before touching source or destination; they do not invoke an incompatible Kalms
leaf. All ten fallback widths also pass the original blitter/pixel oracle at
height 16. Odd heights are explicitly invalid, **not** sent to the known unsafe
native odd-height path. Unsupported non-16-aligned widths, out-of-range sizes and
null/odd pointers are rejected before pixel access.

The callable seam takes A0=chunky source, A1=base of four contiguous destination
planes, D0.L=W, D1.L=H. It returns D0=0 for completed CPU conversion, 1 for a
request to use original QBlit, or 2 for invalid input. D1–D7/A0–A6 are preserved;
CCR is explicitly clobbered. `ocs_c2p_word` and `ocs_c2p_long` share this ABI;
`ocs_c2p_native` only returns the native request. **A native request is not a
completion event.** Its caller must still execute the original submission,
wait/completion and publication protocol. This interface does not replace that
protocol or simulate it with a synchronous CPU return.

Callers must supply valid, disjoint source/destination/stack/code extents, own a
nondisplayed destination, and retire outstanding native QBlit work before CPU
entry. Nonzero/even pointer checks cannot prove allocation ownership. Planes
remain Chip-resident for display DMA; the CPU source can be Chip or Fast and the
stack should be Fast. Actual allocation placement and failure handling belong to
C2–C4 integration. There is no allocator, native patch, IRQ hook or publication
in this component. Both paths assemble with `-m68000`; the proposed 68020+ use of
longword writes is a candidate policy rather than an ISA requirement.

Only the H−1 visible rows in each plane are written. The two leading rows and
last allocated logical row remain unchanged; native scratch/invisible writes
are not reproduced. Tests explicitly guard those rows. They do not extend the
viewport or claim full allocation equality with native scratch. Plane order is
colour bits 0,1,2,3 with MSB-first pixels. Both source and plane bases work at
0 and 2 modulo 4, retaining the 68000 even-alignment requirement.

#### Accepted checks and limits

`tmp/p13c1-accepted/report.json` records isolated execution of original 68000 code
with the A2 functional blitter, the independent scalar pixel oracle and both CPU
candidates. This is functional-model evidence, not FS-UAE timing or real hardware.

- 94 native conversions and 606 CPU conversions: all three native sizes, all ten
  CPU widths at height 16, an 18-row boundary, independent random nibbles, all 256
  nibble pairs and solid white. Native and CPU visible pixels agree with the oracle.
  The CPU count includes all 93 admitted even heights on 68000 word/68020 long.
- Word path executes on 68000/020/040 models; longword path on 020/040. Stores to
  planes are checked to be exactly words or longwords respectively. Both paths
  preserve the opposite destination across alternating calls, source bytes,
  allocation guards, row padding and immutable code. Every CPU data read/write
  is range-checked; no source overread or write outside visible rows is permitted.
- 320 incoming-CCR/user/supervisor ABI cases, 50 explicit native fallback cases,
  80 invalid geometry/pointer cases, and the native-request entry on each model.
  Four generated-code mutations (low-nibble-only, wrong parity, missing edge,
  wrong leading rows) fail. Independently changed copies of each pinned upstream
  input are rejected and preserved.

The combined component is 1,666 bytes, SHA-256
`4161f8aaa3838623d07acf730558589eed1fb4833dfa726bb234e22cde2ce2ce`.
Observed maximum stack use is 508 bytes below entry SP; reserve at least 512
bytes **plus interrupt/headroom requirements of the eventual caller**. This is
a component footprint, not a measured A500 minimum memory budget.
Fresh standard builds in `tmp/p13c1-release` and `tmp/p13c1-native` match B3 byte
for byte: CD32 43,544 bytes (`fdd92fbb…`), original OCS 5,324 (`eec155c9…`).

Stop at C1. C2 must wire the experimental arms into matched native scheduling,
validate the installed instrumentation, and measure staging, conversion, queue
waits, overlap and actual displayed pictures. C3–C5 still own selection, memory
and publication. No end-to-end enhancement, performance claim or release is made.

### P13C2: measured OCS converter crossover

**P13C2 is complete on the scoped emulator models.** Retain the native blitter
on the measured 7.09 MHz 68000, with either true Fast or slow expansion RAM, and
on the measured 14.19 MHz 68020 without true Fast RAM. On the 68020 with true Fast
RAM, the longword CPU converter **with a Fast chunky source** wins both checked
scenes by about 6% over matching images. CPU/Chip does not win. This is a measured
profile recommendation for C3, not a universal CPU threshold. C3 below applies the recommendation at the
bounded seam; normal builds await production memory ownership. Normal OCS and CD32 slaves remain byte-identical to C1.

#### Controlled experiment and matching

`ocs_crossover.py` makes an explicitly experimental copy of the pinned native
slave with a 73,728-byte owned reservation: 8,192 bytes for converter/code space,
64,000 bytes for a source and 1,536 trailing guard bytes. This diagnostic-only
file-backed reservation is identical across arms; it is not the production memory
allocator or minimum-RAM design. The original source, workspace and allocation
registry remain allocated. No change reaches an installed game tree or release.

The bounded installer stops after native final-reader retirement at `O:3260e`
(file `3263a`), checks all three queue flags, input identity and displaced bytes,
then changes `O:3291e` (file `3294a`) only for a CPU arm. It preserves native
rotation, the field-counter wait, and the original completion/publication body
at `O:32e06` (file `32e32`). CPU conversion is synchronous in the main task;
native conversion retains its asynchronous third phase. Both publish through the
native nesting guard and Copper path. No native pacing is removed. Full CPU
cost includes checkerboard staging, all per-row calls and the adapter. Unsupported
converter results trap in this diagnostic; C3 owns production fallback.

Each run covers 250 uninterrupted PAL fields, **5.007972 emulated seconds**, with
native audio and identical controls. Warp only shortens host waiting; field ticks
remain 227×313×512. CPU cycle units are 256 on 68000 and 128 on 68020, corresponding
to 7.09379 and 14.18758 MHz. Numeric frequency and multiplier remain zero, selecting
the core's calibrated defaults. CPU/memory/blitter cycle-exact modes are on,
MMU/JIT/immediate blits are off; observed CACR is 0/1 respectively. The 020
instruction cache remains enabled. Loaded hook execution is proved by absence of
QBlit submissions in CPU arms, retained hook bytes and completed native publication.
C3 below installs a once-only FlushCache contract at the bounded seam;
production allocation/transition integration remains C4.

Within each CPU/memory/scene group, **all four starting game hunks and all Chip
RAM match exactly** before installation. The observer retains every submitted
chunky source in a binary stream and checks every completed visible conversion
against an independent pixel oracle, including checkerboard nibbles and four
native black edge pixels. The decision table uses the common **byte-exact source
prefix**, bounded further to completed and displayed images. It reports intervals
between those matched pictures, not unlike amounts of simulation in five seconds.
The native game still advances much world state once per picture; slower arms
reach fewer updates. Credit-clock changes eventually end the matching intro
prefix. Full 250-field rates are retained separately, never used as proof of
identical end-state progression across backends.

#### Matched results

All configurations use 512 KiB Chip and OCS. F means 4 MiB true Zorro-II Fast RAM;
S means **no true Fast RAM**, with 1.75 MiB slow expansion RAM. The slow case boots;
it is not an unsupported-memory omission. CPU word conversion is used on 68000,
longword conversion on 68020. Times are milliseconds. Short-window p95 values
are sample descriptions, especially the six-interval A500 flight comparison.

| CPU / RAM / scene | Backend/source | Matched pictures | Display FPS | Interval p95 | Full conversion mean |
|---|---|---:|---:|---:|---:|
| 68000 / F / asteroids | Native/Chip | 10 | **7.488** | 140.22 | 58.51 |
| same | CPU/Chip | 10 | 2.455 | 420.67 | 307.70 |
| same | CPU/Fast | 10 | 2.455 | 432.69 | 307.11 |
| 68000 / S / asteroids | Native/Chip | 10 | **6.607** | 172.27 | 65.44 |
| same | CPU/Chip | 10 | 2.442 | 432.69 | 309.25 |
| 68020 / F / asteroids | Native/Chip | 51 | 13.000 | 80.13 | 55.31 |
| same | CPU/Chip | 51 | 11.829 | 100.16 | 39.80 |
| same | CPU/Fast | 51 | **13.867** | 80.13 | 37.05 |
| 68020 / S / asteroids | Native/Chip | 25 | **7.488** | 160.26 | 65.07 |
| same | CPU/Chip | 25 | 6.021 | 200.32 | 83.34 |
| 68000 / F / flight/fire | Native/Chip | 7 | **5.990** | 180.29 | 92.56 |
| same | CPU/Fast | 7 | 1.619 | 620.99 | 493.59 |
| 68020 / F / flight/fire | Native/Chip | 47 | 9.941 | 120.19 | 100.09 |
| same | CPU/Chip | 47 | 9.689 | 120.19 | 68.91 |
| same | CPU/Fast | 47 | **10.582** | 100.16 | 65.16 |

The independent 250-field rates (native / CPU-Chip / CPU-Fast) are
5.791/2.396/2.396 for 68000/F asteroids, 5.391/2.396 for 68000/S,
12.979/11.781/13.578 for 68020/F and 6.989/5.990 for 68020/S.
Flight/fire gives 5.391/1.597 for 68000 native/CPU-Fast, and
9.784/9.585/10.583 for the three 68020/F arms. These are *different progressed
workloads*; the matched table is the backend decision evidence.

Native conversion overlaps later CPU work. On matched 68020/F asteroid pictures,
its conversion interval overlaps 15.43 ms of world work and 21.47 ms of drawing
per picture; in flight these are 7.62/31.52 ms. CPU conversion has zero such
main-task overlap. Thus a shorter CPU conversion alone does not prove higher FPS.
Matched 020 flight world means are 7.49/7.44/7.48 ms for native/CPU-Chip/CPU-Fast;
drawing means are 31.53/21.27/16.74 ms. These are inclusive elapsed scopes, including
interrupts/contention; do not sum overlapping phases or call them exclusive CPU cost.

The native queue/scheduling residual averages 2.31 ms in 000/F asteroids,
0.83 ms in 020/F asteroids and 11.15 ms in 020/F flight. Its explicit field-wait
component averages 0.006/0.119/10.489 ms respectively and can overlap blitter
service; it is not added again. Detailed stage sums, flag-poll time, world/draw
means and percentiles, publication delay and instruction accounting remain in
the reports. CPU adapter time includes its retained field check.

The observer counts actual occupied-bus waits in the emulator's `dma_cycle`,
separating bitplane-occupied slots from other DMA slots. These are CPU arbitration
stalls, not all Chip-access time or isolated blitter throughput. Across the whole
020/F asteroid window, native incurs 1,487.80 ms other-DMA plus 281.66 ms bitplane
waits; CPU-Chip incurs 14.14/48.68 ms and CPU-Fast 4.10/26.37 ms. Flight gives
1,486.71/446.42, 12.70/13.74 and 5.65/9.67 ms. These window totals have different
completed-picture counts, and must not be interpreted as per-picture savings.

#### Fast-source ownership finding

The flight compositor owns more aliases than the primary surface/row table.
`O:2be60`–`2be7a` (file base +`2c`) copies rows to the shadow table referenced by
`OD:6fb6` (file `408fe`), then replaces backed rows with pointers into its separate
backup allocation. `O:2bf74` (file `2bfa0`) executes the 12-byte CPU-copy stream
at `OD:6fba` (file `40902`); `O:2bf40` swaps its +4/+8 source/destination columns.
The stream ends with operation `fffa`; the shadow table is stream base +`bb8`.

The Fast arm must rebase the primary rows, shadow entries still referencing the
active source, and **both** command-pointer columns that reference that source.
Backup pointers, opcodes/counts and allocations stay intact. Merely changing the
surface source and primary table loses compositor pixels; merely looking for a
second identical table misses its backed rows. The retained faulty flight arms
fail exact source matching, and one also exposes writes to the old Chip source.
The corrected arms match flight inputs and leave the retired Chip source unchanged.
This is concrete C4 work: construct/rebind these owners deliberately through
view transitions; do not turn the diagnostic snapshot rebase into a production
scan-and-replace allocator.

Both native allocator pools advertise expansion memory as attributes `0005`
(PUBLIC|FAST), including the slow-memory test. Physical mapping distinguishes the
banks: true Fast lies in the configured `200000`–`600000` bank; slow expansion in
`c00000`–`dc0000`. These are **hardware memory-map ranges**, not game offsets.
The loader reservation and native expansion pool are verified inside the selected
bank. Do not classify trapdoor slow memory as uncontended Fast merely from Exec's
MEMF_FAST flag. The measured slow configurations are comparison cases, not a
replacement for the A500/true-Fast project baseline.

#### Gate and limits

Actual plane-0 DMA identifies the displayed allocation independently of publication
PCs. Each accepted field uses one display buffer. Interior publications match
DMA transitions; at most one publication in the final field can remain pending
past the cap. The 15 accepted windows pass 520 independent four-plane pixel checks;
converter code and reservation guards remain intact. Native queue waits, field
pacing and direct-plane/Copper paths remain present. The source move is restricted
to the active bounded scene; allocation failure, transitions, cleanup and general
publication deadlines remain C3–C5/E2.

Three observer-off controls (000 native asteroids and both CPU/Fast flight arms)
match game hunks, complete Chip RAM, Fast source bytes, field clocks and native
world counters exactly: zero measured emulated-cycle effect. Eight deliberate
report sabotages reject bad CPU clock, pixels, missing DMA/source coverage,
wrong source bank, unfrozen endpoint, wrong world count and missing instruction accounting. The earlier incomplete
Fast move is a separate rejecting ownership control. Neither observer instrumentation
nor the stopped-guest loader runs in a normal slave; no guest recorder is installed.

No staged Fast-to-Chip/blitter arm or pacing-removal arm is selected. The required
comparisons already distinguish the measured profiles; a staged path would add
copying and another lifetime contract without demonstrated benefit. That is an
unmeasured alternative, not a claim it can never win. There is no calibrated
intermediate CPU/clock boundary, 030/040 result, hardware speed claim or general
accelerator policy. For unknown profiles C3 must retain native fallback/override.
No broad matrix is needed to resolve the observed, consistent profile choices.

Accepted evidence: `tmp/p13c2-final-*` for the ten asteroid cells,
`tmp/p13c2-flight-68000-native`, `tmp/p13c2-flight-68020-native`,
`tmp/p13c2-flight-68020-chip-long`, `tmp/p13c2-flight-owned-*` for flight,
`tmp/p13c2-check-*-final.json`, and `tmp/p13c2-accepted-final.json`.
Instrument SHA-256: `432c44f7a9b59dd0454727851faecd413a308f5e557da42af0772ade61e764d6`.
Normal OCS SHA remains `eec155c946e8a247e2c4811fc2279d476c330f2d1b5797cc0defb35918913913`;
CD32 release remains `fdd92fbbda8689e3ec3ab2353d5baa866859469a684026841fd71527e0a6de8d`.
C3 selection is complete below. [Reproduction](development.md#p13c2-measured-converter-comparison).


### P13C3: conservative backend selection

**P13C3 is complete at the bounded conversion seam.** The owned 68000 assembly
`whdload/ocs_backend.s` provides selection and once-only initialization. The C2
installer consumes it; the selector runs in the guest before dispatch. Normal
OCS and CD32 outputs remain unchanged. This is not a release or a claim that
production source ownership, allocation rollback or view transitions are complete.
Those remain C4, followed by general publication integration in C5.

#### Selection and memory contract

| Request / verified inputs | Selected backend |
|---|---|
| Auto, measured C2 PAL 14.19 MHz 68020 with true Fast storage | CPU longword |
| Auto, 68000/68010 or any unknown CPU/clock/memory profile | Native blitter |
| Explicit native | Native blitter |
| Explicit CPU, 68000/68010, required Fast storage available | CPU word |
| Explicit CPU, 68020/030/040/060, required Fast storage available | CPU longword |
| Any request without the required owned Fast storage / readiness, invalid CPU or option | Native blitter |

The forced CPU path is an override, not a performance recommendation: native won
on the measured 68000. Both CPU entries still produce four OCS planes. CPU family
never selects AGA output. Forced longword operation on other accelerators is a
functional option, not a measured speed claim or broad live compatibility gate.

`ocs_backend_choose` takes D0.L option (0 auto, 1 native, 2 CPU), D1.L CPU class
(0/10/20/30/40/60), D2.L profile (1 for the measured C2 020/Fast profile, otherwise
unknown), and D3.L readiness (exactly 7). Readiness certifies owned true-Fast
source/code storage, retired native QBlit, and valid Chip destination with the
native fallback still intact. It returns D0=0 native, 1 word or 2 longword;
other registers are preserved, CCR clobbered. This certificate is a caller
contract, not an allocator or a general-purpose pointer validator.

The bounded harness identifies the profile from its fixed C2 machine contract:
PAL OCS, 512 KiB Chip, 4 MiB Zorro-II Fast, calibrated native 14.18758 MHz 020
clock, instruction cache on, exact CPU/memory/blitter, no MMU/JIT/immediate blits.
It also checks live Exec AttnFlags and the reservation's physical bank before
installation. **AttnFlags alone cannot identify the clock or memory performance.**
An unknown real accelerator must supply profile 0 and defaults native until a
measured classification exists; there is no invented general MHz detector.
`--profile unknown` exercises that policy independently of the host CPU model.

Physical true-Fast placement is required, not just MEMF_FAST. The actual slow
expansion run still uses native even under an explicit CPU request. The existing
slave-owned diagnostic reservation is verified before choosing: `--unavailable`
models its required Fast part being unavailable and selects native before any
source pointer is changed. No production AllocMem failure or free path is claimed;
C4 must supply the ownership certificate and handle partial setup/rollback.

#### Installation, cache and dispatch

The entry remains `O:3291e` (file `3294a`). Native fallback restores the displaced
MOVEM and call to retirement `O:32990`, then resumes `O:32924` (file `32950`);
it does not call the CPU completion path or pretend a native request completed.
CPU selection binds the tested word/longword entry and preserves the native
field wait and completion body at `O:32e06` (file `32e32`). A mismatch between
the guest choice and the installer's source arrangement traps in this diagnostic.
The existing C1 invalid-geometry trap remains diagnostic: a future transition
cannot silently feed a relocated Fast source to a native blitter fallback.

`ocs_backend_init` takes A0 pointing to zeroed owned eight-byte state and A1 to
a FlushCache callback. It selects, flushes, then commits the backend and `OCS3`
magic. Repeated calls return the frozen selection without another flush or a
backend change. The callback is the original slave trampoline at `S:0ee8`
(file `0f08`), which tail-calls resload_FlushCache via `S:0f24` (file `0f44`).
No SetCPU, CACR write or cache-policy override is added. Unit execution checks
flush-before-commit ordering; every live gate has identical pre/post CPU/cache
audits (CACR 0 on 000, 1 on 020). Later C4 installation must use this flush
contract when integrating the production patches, before handing over execution.

The CPU source move still includes primary rows, compositor shadow rows, and
both copy-command pointer columns. Original Chip allocations and the allocation
registry remain intact. This is deliberately the bounded C2 ownership seam, not
an implementation of C4's lifecycle or minimum-RAM budget.

#### Accepted evidence

`tmp/p13c3-unit/report.json` records 3,240 executed selector cases and 36
initialization/repeat checks on 68000/020/040 CPU models. The decision table
covers invalid inputs, unknown profiles, readiness failure, 68010 word and
68060 longword selection, while running only base-ISA instructions. The 68010
and 68060 choices are ISA/component tests, not live machines. All non-result
registers and stack boundaries pass; code remains immutable. Wrong longword
selection, missing flush and unwanted reselection mutations all reject.

`tmp/p13c3-live-gate/report.json` records seven 250-field windows and **305**
independent completed-image pixel checks. Automatic and forced 020/Fast flight
runs match all starting/ending game hunks, all Chip RAM, and every submitted
chunky image exactly. Other windows cover default 000/native, forced 000/word,
unknown 020/native, unavailable Fast storage/native, and actual slow expansion
020/native. Native queue activity versus CPU completion, display DMA/publication,
source placement, frozen selector state, code and allocation guards all pass.
A copied result with uninitialized live selector state is rejected. The C2 host
observer is unchanged; no new timing instrument or performance claim is introduced.
All project emulator sessions completed and used scoped cleanup.

Fresh builds `tmp/p13c3-native` and `tmp/p13c3-release` retain SHA-256
`eec155c946e8a247e2c4811fc2279d476c330f2d1b5797cc0defb35918913913`
and `fdd92fbbda8689e3ec3ab2353d5baa866859469a684026841fd71527e0a6de8d`.
Stop before C4. [Commands](development.md#p13c3-selection-and-fallback).
