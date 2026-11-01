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
