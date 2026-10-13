# Known internals

## Phase 1 gate: CD32 static identification complete

The identification sections record static evidence from verified extraction,
hunk/relocation parsing, slave patch lists and 68020 disassembly. Their time-source
and display-path descriptions remain hypotheses except for the explicitly scoped
runtime confirmations in the phase 2 and phase 3 sections below. The OCS executable
has not been analysed.

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

The VERIFY-only equal-size `reconstruct.py --ceiling` fixtures are built and
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

Phase 5 analysis is complete; **the rate decision remains with the user**.
No phase 6 renderer or release timing change has been made. The user's clarified
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

### Rate-decision gate

**Recommended practical ship-motion candidate: about 15 native updates/s**, with
an approximate **15–17/s** range supported by the short displacement comparison.
The measured 020 ship portion executes about 16.4 updates/s while producing about
8.2 pictures/s and a similar projected travel speed to the PC sample. In the
unmodified two-update-per-draw loop, 15 updates/s means about **7.5 drawn frames/s**,
not a 15 FPS cap. Better rendering must eventually show intermediate motion
without doubling the distance travelled per second.

For asteroids the PC reference is faster, approximately **20–25 visible advances/s**.
Treat this as a separate visual target. A one-to-one PC/Amiga native-step mapping
has **not** been established for the differently populated asteroid trajectories;
calling 22 native updates/s a proved intended rate would overstate the evidence.
The video also does not establish a universal historical design rate.

The decision is therefore concrete: retain a common approximately 15-update/s
working target, or use separate motion targets with the PC displacement/cadence
examples above. **Prefer matching motion per subject over a blanket publication
cap**, and preserve the native music/text deadlines in either case. The user
chooses at this gate; no rate is installed by phase 5. Flight calibration remains
phase 7. These limitations do not reopen the phase 4 profiling matrix.

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
or a release package. Stop before phase 11.

### Ownership and correction policy

The common world exit snapshots all 64 native position/velocity slots, types,
models, lifetimes, angular steps and the ten ship actions. Rendering uses
`position + trunc(velocity * fraction / field_rate)`, with fraction taken from
the scheduler's residual debt and clamped to one world interval. Signed quotient
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
Hard-turn positional correction can remain visible; prediction is bounded to
one tick and never alters collision or other authoritative results.

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
No visual-quality claim comes from a debugger-greyed display. Combined renderer,
full campaign and hardware play-testing remain release coverage; they are not a
reason to expand this phase into a new performance matrix.
