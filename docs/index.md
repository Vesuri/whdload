# Find guidance for your task

Read the game's own `AGENTS.md` and `docs/open-work.md` first; they take precedence for
that game. Then pick the row below and read only the sections you need. Method and
Amiga knowledge shared with other projects is AmigaXDev's: start at
`~/.local/share/amiga/docs/index.md`.

| Task | Read |
|---|---|
| Find your way around; a game's files, `game.conf`, hooks | [Layout](layout.md) |
| Run a game, on any machine; drive it through the gdb stub; try an archive without a game directory | [Running](running.md) |
| Build, VERIFY builds, patch conventions, byte identity | [Building](building.md) |
| Package and publish a release | [Releasing](releasing.md) |
| Credit, bring a game in, follow upstream changes | [Upstream](upstream.md) |
| Start a new game | `make new GAME=<Game>`, then [Layout](layout.md) and [Upstream](upstream.md) |
| Improve a slave: profiling, game time, patches | AmigaXDev `docs/playbooks/new-game-playbook.md` (JOTD and StingRay variants beside it) |

## Where knowledge goes

- About one game only: that game's `docs/`.
- True of every game in this repository (the layout, the scripts, release rules): `docs/`.
- True of Amiga or WHDLoad work in general: AmigaXDev, as a generic rule without naming
  the game (its own rules), then `make share` there.
