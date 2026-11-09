# Original visual bug fixes (2026-10-22)

The distant-rider flicker, mirror flicker and large vertical hill jumps are
fixed independently of CUSTOM2. This follows the user's explicit authorization
to fix the original defects after the H1/H2 investigations. The 3.0b version/date
remain unchanged. No additional option, frame history or presentation delay is
introduced.

## Visibility

`visual_actor_visibility` replaces the decision block at `$89e2c`. It subtracts
full 16.16 positions before testing visibility. Forward riders are eligible at
0 <= distance < 30 segments; rear riders at -16 <= distance < 0. The existing
player-speed comparison still suppresses a close-behind rider when the player
is at least as fast, now only for -1 < distance < 0. A steady separation cannot
oscillate across a threshold merely because camera/rider segment boundaries
occur at different times.

The old cutoff blended distances 30..31 and -2..-1 according to segment phase.
The new fixed limits choose the nearer edge of each transition band. The native
integer **index difference** is retained in D0 for forward projection; replacing
that index with a rounded relative distance would misalign the road lookup.
The original rider position is restored in D2 before the existing native or
enhanced lean hook. Mirror projection, sprite selection and cleanup remain
native. Explicit helper references support relocated and unrelocated images;
all added instructions are 68000-compatible.

## Height projection and simulation isolation

After the native read/advance/wrap at `$89794..$897a0`, A1 points at the next track
interval. The hook at `$897a6` reads its height byte without advancing A1. The
fractional offset and subsequent road-point accumulation now refer to the same
interval. All consumers see the corrected height/road-Y/occlusion arrays: road,
riders, scenery and sprite clipping. Integer projection/bobbing remain; this
removes the reference discontinuity, not ordinary one-pixel raster steps.

The hook is installed **after** copying the reduced simulation geometry, so
that helper retains native instructions. The earlier investigation conservatively
identified collision-table reuse as an adoption risk. A closer consumer audit
shows why the existing reuse optimization can remain:

- `$8b29a..$8b37c` uses horizontal/depth values to accept world objects and produce
  their collision distance and scale. The height/occlusion comparison at `$8b33a`
  does not branch; subsequent moves replace its flags. Corrected vertical values
  only change draw Y and clipping height, not record acceptance or width.
- `$8c7f2..$8c8ac` consumes distance, scale, type, side/lateral metadata and original
  sprite dimensions. It never reads the projected Y or clipping-height fields.
- `$8a5fc..$8a714` likewise rejects scenery by depth and horizontal division, not
  projected height. `$8c48e..$8c582` uses scenery world positions and sprite sizes.
- Geometry reuse changes only the render-derived height/occlusion values at the
  next collision preparation; its horizontal/depth inputs are unchanged.

Full-race hash/event comparison below validates this reasoning with collisions,
crashes and restart. It does not assert every possible native variable-delta
trajectory is identical: changing rendering workload can change its cadence,
and the native rider traversal derives pose only for eligible forward riders.
The accelerated simulation retains authoritative pose ownership.

## Unwaited blits (3.0b of 09.11.2026)

A player reported glitches in the intro and on the bike selection screen on a
68040 machine (8.11.2026, CUSTOM2 setting not known). Several routines start a
blit and return while it runs; the caller then draws into the blit's area with
the CPU, or reprograms the blitter. The emulator's timing hides this, but a CPU
that runs from cache or Fast RAM can overtake the blitter on real hardware. The
two intro clears were found during D3 (`memory-performance.md`) and fixed there
only for CUSTOM2.

The blitter-sync observer (`development.md`) found the sites. It logs CPU access to
a blit's area, and CPU writes to the blitter registers, between the blit's BLTSIZE
write and the next DMACONR read that finds the blitter idle. It works by code order,
so the emulator's timing doesn't matter. Each site now waits for the blitter
(`visual_blit_wait`) and keeps the native registers and CCR:

| Module | Offsets | Routine | Followed by |
|---|---|---|---|
| `INTRO.AMI` | `$1f88`, `$1fb4` | screen clears (exits) | picture and credits decoding |
| `INTRO.AMI` | `$1ff0` | one-line scroll | the next line's text |
| `TITLE.AMI` | `$c008` | screen clear (exit) | title drawing |
| `TITLE.AMI` | `$c1d0` | screen copy | title drawing |
| `TITLE.AMI` | `$ad24`..`$ad74` | five-plane copy | each plane's blit reprogramming the last |
| `TITLE.AMI` | `$c956`, `$ca98` | bob blits (exits) | the next bob |
| `lomain.ami` | `$47aa` | full-screen copy | loader screens |
| main hunk | `$2f6b2` | full-screen clear (exit) | menu and shop text |
| main hunk | `$2f75e` | partial clear (exit) | menu and shop text |
| main hunk | `$2f7c4` | full-screen copy | CPU writes to its source and destination in the menus and bike shop |

The main-hunk copy at `$2f7c4`, followed by the shop's CPU drawing, is the likely
cause of the bike-shop report. The patches go into the native modules before the
Enhanced copies are made (title, intro and main), so the copies have them too.
None of the copies' validated operands, relocations or relative stubs lie inside
the patched bytes. The jumps were checked in the Enhanced main copy.

Checks (release build, ignored `tmp/blitaudit/`):

- With CUSTOM2=0 on `a1200-fast`, the observer is clean from boot through the
  title, intro, menus, a race's results and the bike shop (`tools/shop_route.py`),
  except for the three race-start sites in `open-work.md`.
- A race is reached on the custom A500 and on `a1200-040` with CUSTOM2=0 and 1,
  and on `a1200-fast` with CUSTOM2=1.
- The intro is pixel-identical to 3.0b's on `a1200-040` at the maximum emulated CPU
  speed. The emulator doesn't reproduce the glitch, so this isn't evidence that
  the fix removes it on real hardware. That still needs a player's confirmation.
- Race rates (`tools/check_a.py --normal`, one run each, 3.0b vs this build):

  | Machine | CUSTOM2=0 | CUSTOM2=1 |
  |---|---|---|
  | A500 (`a500-1m`) | 8.5 / 8.5 | 8.5 / 8.5 |
  | `a1200-fast` | 12.5 / 12.5 | 18.6 / 18.6 |
  | 68040 25 MHz | 22.4 / 22.7 | 49.6 / 49.6 |

  There is no regression. The 040 CUSTOM2=0 difference comes from a single run
  and is not claimed as a gain.

## Validation

Normal slave: 39,228 bytes, SHA-256
`55f24917ce843bddef178283acc006c09183173b5adf4998bb8c4d3cb51a6a05`. All evidence is retained in the ignored local
`tools/` harness (evidence in the ignored `tmp/`); no original game assets are committed.

- `visibility-on-fix-straight` / `off-fix-straight`: 970 / 515 render samples.
  The previously alternating pair of far riders stays omitted throughout the
  30..31-segment trouble band: 44 / 22 checked actor samples, six draw records
  throughout, rather than alternating six/eight.
- `visibility-on-fix2` / `off-fix2`: 5,000 / 2,552 render samples including overtakes.
  The reproduced mirror rider remains drawn for all 109 / 37 checked samples in
  the -2..-1 band during the first overtake. Later crashes are not mistaken for
  visibility failures.
- `h1-on-fix` / `h1-off-fix`: 3,392 / 1,545 consecutive render snapshots through
  field 3800. An integer model exactly matches all 32 height and projected road
  Y entries in every snapshot, and player Y in all 2,993 / 1,428 snapshots where
  that player draw record exists. Crash/run animation can omit that record.
  The runs include 101 / 37 airborne snapshots, 9 / 10 track-table versions and
  both 255→256 and 511→512 wraps. The prior isolated boundary sweep reduced the
  largest reference jump from 17 to 2 pixels; the running code now matches that
  evaluated correction rather than merely predicting it offline.
- `visual-final-finish-fixed` / `visual-final-finish-vary`: both match the previous
  release's `g-final-finish-fixed` for all **16,230** simulation hashes, **72** sound
  events, terminal actor/control ranges, finish field **16042**, exit field
  **16231**, and a clean new-race reset. Forced geometry reuse is exercised.
- `visual-matrix`: normal builds pass 68000 Chip/Slow, Chip-only 020, Fast 020,
  040 and 060. The same 500-field throughput scenario retains **8.5, 12.5, 18.6,
  49.6 and 49.6 fps**, respectively. No timer, input queue or display handoff was
  changed. `visual-extra-000-fast` also passes at the previous 9.4 fps, exercising
  the relocated native-simulation path. The ordinary game screenshot has aligned
  road, rider and scenery.

- `visual-dcache2-040-mmu` / `visual-dcache2-060-mmu`: emulator data caches and
  MMU enabled; game reaches the race and the policy probe verifies all 256
  supervisor and user BaseMem pages as write-through, Fast code/stack copyback.
  An initial probe lacked its MMU sidecar and was rerun with that diagnostic
  compiled in; it was not a game failure.

The first private visibility build placed the hook beyond the signed patch-list
reach and failed to boot; the final helper is adjacent to the main patch list.
Those failed captures are retained separately and are not counted as validation.
Physical cache/coherency testing remains the existing D1d future item.
