# Known internals

No binary or runtime analysis has been performed.

| Input | Identification |
|---|---|
| OCS full install | WingCommander_v1.0_1657.lha, user-supplied disk version |
| CD32 full install | WingCommander_v1.0_CD32.lha, user-supplied CD32 version |
| Original installer | WingCommander.lha, Psygore v1.0 |

The [official install page](https://whdload.de/games/WingCommander.html) names
`WingCommanderECS.slave` for the disk version and `WingCommanderCD32.slave` for
CD32. The user's OCS label is retained for that input. Source is unavailable per
the user; reconstruction is deferred.

Executable layout, slave implementation, patch offsets, game-time model,
performance bottlenecks and specific defects remain uninvestigated. No diagnosis
or performance claim is implied by this scaffold.
