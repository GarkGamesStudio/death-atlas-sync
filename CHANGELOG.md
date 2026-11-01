# 0.3.8 — compact setup and tray

- Player download contains only the EXE. Source and notices are distributed separately; license texts are also embedded in the EXE.
- Small folder dialog with Detect, Choose folder and OK. Account choice appears only when necessary.
- OK performs the actual initial sync before confirming background operation. Failure keeps setup available and shows an error.
- Tray menu reduced to Configure, About and Close.
- About links to the public GitHub source/license and privacy information.
- A tray icon failure prevents setup from claiming success or silently hiding the application.
- Existing DPAPI settings, consent policy, hidden process checks and WoW-closed file safeguards are preserved.
