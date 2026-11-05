# B acceptance

B1–B4 complete. Production waits committed as 1d3250b; cache audit and VERIFY
observer committed separately. All evidence stays in ignored tmp/b/.

Run from the game directory after sourcing ../../common/env.sh:

```
make slave verify
python3 tools/test_blitter.py
python3 tools/test_verify_frame.py
python3 tools/test_verify_policy.py
python3 tools/audit_cache_b.py
python3 tools/accept_b.py
```

Acceptance: 180 assembled blitter cases, 128 frame cases, SetCPU scratch-register
ABI preservation, 267 direct write sites / 138 destinations with no unmapped
writes or instruction overlap. Nine cycle-exact graphics samples and twelve
cache-functional samples match all 40,000 displayed bitplane bytes and 64 palette
bytes exactly. Combined SHA256:
a9311420b9ab9f0c24b76cd38f165faf76405b5d343dc0ffd94602aaae580fc1.

Example cache-functional run (use a fresh output directory):

```
B_MMU=1 B_REGS=1 B_TICKS=300,310,320 \
 B_EXTRA='--uae_immediate_blits=true' MACHINE=a1200-040 \
 GUNSHIP_FSUAE="$AMIGA_SHARE/fs-uae-arm/fs-uae" \
 SLAVE="$PWD/tmp/build/verify/Gunship.Slave" \
 WHD_ARGS='CUSTOM2=1' \
 python3 tools/compare_graphics_b.py tmp/b/cache-040-new
```

Final runs: cache-020-cpu-buffer (a1200-fast, empty B_EXTRA),
cache-040-cpu-buffer, cache-060-cpu-buffer (a1200-060),
cache-040-off-cpu-buffer (CUSTOM2=1 NOCACHE). Cache policy 0x3b3d; off zero.
Observe the CPU checkpoint: RAM tick was one behind at 060 CPU tick 300.
Select front buffer using D0 upper word XOR 1 and immutable BitMap array.

Legacy cycle-exact runs graphics-020/040/060 cover ticks 100/110/120.
Smoke runs smoke-000, smoke-060 and combat-060 each cover 500 VBLs.
ntsc-060-live-pilot verifies flight and 14 live patches, using PAL live-pilot
roster only in disposable runtime; original NTSC roster has no live pilots.
pristine-check.json verifies all 226 PAL/installer/NTSC original files unchanged.

Limitations: German original unavailable (fixture dispatch tested). Full-MMU
asynchronous-blitter emulator cockpit corruption reproduces with pre-B and
NOCACHE; immediate blits isolate cache checks, not timing/performance. No hardware
certification or full-mission/game-time equivalence claim. User's T-74 issue is
deferred. See tracked CACHE_AUDIT.md and PERFORMANCE_PLAN.md for release followups.
