# Open work

Set up from StingRay's V1.01 slave. The build is equivalent to the shipped slave (another
`kick13.s`, [development.md](development.md#the-build)). It boots v1.53 and v1.50 to the
first hole on the a1200-030 without `CACHE`.

## Release

No improvement yet. A first release needs a dated `$VER` and info text in the slave, and a
ReadMe entry above StingRay's.

## Caches and fast memory

The goal: the game running from Zorro III fast memory with the caches on, on the a1200-030
with Zorro III RAM (`EXTRA_ARGS='--fast_memory=0 --zorro_iii_memory=32768'`,
`WHD_ARGS='CACHE CUSTOM1=1'`). With `CACHE` the first hole draws no landscape: the
renderer's self-modifying code ([internals.md](internals.md#the-games-cache-handling))
runs stale. Code in the four `MEMF_CHIP` hunks of `golf` and in `title`'s hunk 3 runs from
chip memory.
