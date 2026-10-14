# Wing Commander

Standalone WHDLoad improvement project for the OCS disk and CD32 versions.
Current status: P13A1–P13A4, P13B1–P13B3, P13C1–P13C6 and P13D1–P13D4 are complete.
D1 verifies OCS timing owners and 10 Hz units with native CPU checks; its input
queue/edge ABI differs from CD32. D2 integrates the opt-in 10 Hz flight clock with retained catch-up debt and
world-owned side effects. D3 adds field input and bounded renderer prediction;
D4 adds the title/asteroid intro clock with native credit deadlines. E1 is next;
A500 asteroid-world overload, sustained-fire overload and low display throughput
remain measured E1 gaps.
Normal OCS and CD32 slaves remain byte-identical. C2 recommends
native blitter on the measured 68000 and no-Fast 68020 profiles; CPU/Fast longword
conversion wins the measured 14 MHz 68020/Fast profile. These are scoped emulator
results, not a universal threshold.
C4 provides a separate OCS candidate with creation-time source allocation,
native registry cleanup, safe fallback and checked display teardown. C5 queues
completed images for OCS blanking-time publication and drains ownership before
conversion, direct planar writes and View teardown. C6 adds opt-in changed-block
CPU conversion with separate destination histories and scratch-loan invalidation; it wins the measured 020/Fast intro but loses to
the A500 blitter. The default candidate remains unchanged. The shared
Chip workspace stays in its combined allocation to support native fallback.
Exec MEMF_FAST also labels slow expansion RAM; identify the physical bank.
The OCS guest recorder remains CPU-tested, not live-hooked; correctness runs use
the host observer. Automatic production selection stays native without a clock
certificate; explicit CPU selection requires verified Fast storage. The tested
launcher floor is 512 KiB Chip plus 4 MiB Fast; smaller tested configurations fail.
Required baseline for later work: Amiga 500 with Fast RAM. Share verified CD32
mechanisms with 68000-safe paths. Retain native blitter C2P wherever matched
CPU/memory measurements favour it; CPU type alone is not a crossover measurement.
CD32 E1/phase 12 remain paused. See `docs/ocs-plan.md` for the ordered work.
The CD32 intro 10 Hz timing and first-interval projectile fixes are complete;
phase 11b D1–D5 are complete on current models. A2 calibration remains separate.
OCS live evidence is limited to the documented emulator gate; no OCS hardware
performance or broader compatibility claim follows from it.
Derived material stays in `tmp/`.
Psygore authored the original v1.0 slaves; source code is unavailable.

## Rules

- Never commit game, Kickstart, Workbench or WHDLoad bytes, or anything made from
  them: unpacked data, disassemblies, traces, dumps, screenshots, input recordings
  and built slaves stay in ignored `tmp/`.
- Never `pkill fs-uae` or `pkill gdb`. Use the shared `fsuae_common.sh` and only
  stop this project's processes, checking ownership before killing a PID.
- Commits: author and committer `Vesa Halttunen <vesuri@jormas.com>`, unsigned,
  `core.hooksPath=/dev/null`, no Co-Authored-By or other trailers; one coherent
  change per commit.
- Addresses in documentation are code-hunk or file offsets, not runtime addresses.
- No performance claims without measurements from the appropriate instrument.
- No local paths in the repository: no home directories, usernames or paths into
  other projects. Name projects by name. Shared files use overridable variables
  from `amiga/env.sh`; `~/.local` and `~/.local/share/amiga` are the conventions.
  Scratch output belongs in `tmp/`, never in a system temporary directory.
- Pin downloaded inputs by SHA-256 in `manifest/`; verify before extracting or
  using them. Never overwrite changed local inputs or game trees.
- Setup never deletes: preserve differing files under `.replaced/` before any
  explicitly requested replacement. Never overwrite shared files edited in place.
- Kickstart and Workbench sources must be supplied by the user (`TOSEC=`,
  `AMIGA_OS=`); never record mirror addresses for them.
- Scripts must run under macOS `/bin/bash` 3.2. Quote paths containing spaces.
- History belongs in git; update current-state documentation in place.
- Keep the two game variants separate; do not assume their code or timing matches.
- Agent instructions belong in `AGENTS.md`; `CLAUDE.md` only imports it.

## Read first

| Document | Purpose |
|---|---|
| `docs/open-work.md` | Current scope and deferred work |
| `docs/development.md` | Inputs, setup and shared environment |
| `docs/internals.md` | Verified knowledge and unknowns |
| AmigaXDev `docs/playbooks/new-game-playbook.md` | WHDLoad workflow and validation |
| AmigaXDev `docs/environment.md` | Shared tools and variables |
| AmigaXDev `docs/reference/measurement-method.md` | Measurement discipline |
| AmigaXDev `docs/reference/validation-harness.md` | Correctness checks |
