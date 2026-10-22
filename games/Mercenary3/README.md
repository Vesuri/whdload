# Mercenary 3

Workspace for investigating **Mercenary III: The Dion Crisis** (Novagen), using
WHDLoad install version 1.2. Project setup only; analysis has not started.

The supplied full install and official installer are downloaded and extracted in
ignored `tmp/`. Archive and extracted-file hashes are pinned in `manifest/`.
No game or installer contents are tracked.

Run `make check` to verify the local inputs. See [current work](docs/open-work.md)
and [development](docs/development.md).

The official installer includes `src/Mercenary3.slave.asm` and
`src/Mercenary3.islave.asm`. Their presence is confirmed; their contents and
relationship to the shipped slave have not been investigated.
