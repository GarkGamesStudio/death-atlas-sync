# 0.4.0 Beta — authenticated contribution removal

- About includes an explicitly confirmed request to remove the selected installation's shared contributions. Uses the existing protected key; no key is sent by email.
- Stops uploads before the request, preserves retry credentials, and prevents a later setup click from silently resuming an installation that requested removal.
- Next successful daily edition removes contributions. Local history is preserved. Other downloaded copies cannot be recalled.
- New confirmation and diagnostic strings in all eleven languages. Data policy 2026-11-01 requires reviewing consent again.
- Four engine tests, fourteen real Tk setup tests and 37 synthetic HTTP/D1/R2/DPAPI assertions passed. Official Forever release validation remains pending.

# 0.3.10 — selected Death Atlas icon

- Selected C parchment-map/skull-pin emblem in EXE resources, windows, About and Windows tray.
- Assets embedded in the single EXE; source artwork notices retained in the repository.
- Existing languages, optional Windows startup, consent and sync/data behavior preserved.

# 0.3.9 — Windows startup and automatic language

- Optional Start automatically with Windows checkbox, off for new installations; preserves earlier opt-in and supports removing it.
- Setup and About, three-item tray menu, consent text, notifications and diagnostics translated into the same eleven catalogs as the addon.
- Uses Windows preferred UI languages, with region/script matching and English fallback. No network translation service or additional language selector.
- All locale resources and licenses remain embedded in the single player EXE.
- Real Tk layouts checked in every locale; startup registration tested with a fake registry, without changing the owner's real Windows startup settings.

# 0.3.8 — compact setup and tray

- Player download contains only the EXE. Source and notices are distributed separately; license texts are also embedded in the EXE.
- Small folder dialog with Detect, Choose folder and OK. Account choice appears only when necessary.
- OK performs the actual initial sync before confirming background operation. Failure keeps setup available and shows an error.
- Tray menu reduced to Configure, About and Close.
- About links to the public GitHub source/license and privacy information.
- A tray icon failure prevents setup from claiming success or silently hiding the application.
- Existing DPAPI settings, consent policy, hidden process checks and WoW-closed file safeguards are preserved.
