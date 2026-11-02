# 0.4.4 — Setup before first login

- Configure Windows Sync with the addon installed, without saved history or deaths; wait for the first addon save and sharing permission rather than rejecting setup.
- Detect addon-only installations, extra Forever folder names and custom names in bounded common game/download folders. Resolve the first unique account automatically; require an explicit choice if several appear.
- Explain missing addon requirements and pending first-save status in all eleven languages. Detecting installation does not prove the addon is enabled in-game.
- Check public website version metadata once every 24 hours. Notify about newer versions and offer a fixed download-page link in About. No automatic download or execution; no history, local paths or Sync keys in update requests.
- Preserve settings, sharing checks, WoW process guards and the standard Windows portable folder. Existing macOS/Linux binaries are unchanged.

# 0.4.3 — Windows portable folder

- Ship the standard EXE plus visible runtime folder, without one-file self-extraction or UPX compression. Keep the whole folder when installing or moving it.
- Preserve the existing Windows DPAPI settings and consent contract; update the optional startup path by clicking OK in setup.
- Add native Windows CI checks and publish exact-package checksums, build results and the limited Defender scan report.
- Correct the background-success text across eleven locales. Existing macOS/Linux packages are unchanged.
- Keep the original 0.4.0 detection under Microsoft review; do not claim it is a confirmed false positive or suggest antivirus exclusions.

# 0.4.2 — Linux desktop recovery

- Check secure storage before setup; show specific, translated recovery guidance instead of closing on keyring problems.
- Add explicit system unlock with cancellation/timeout and retry; background operations do not trigger an indefinite password prompt.
- Provide read-only package-manager examples based on the distribution. Never install packages, change desktop security, delete a keyring or reset existing settings automatically.
- Add native Linux GUI tests for retry, inaccessible settings and the transition to real setup; keep the not-tested-with-WoW disclosure.
- Published Windows 0.4.0 and macOS 0.4.1 binaries are unchanged.

# 0.4.1 — macOS / Linux preview

- Native Keychain / Secret Service protected encryption, private settings paths and process locks.
- Native macOS and Wine/Linux process-name guards and bounded folder detection.
- Foreground Linux mode, macOS tray fallback and eleven-language platform notices.
- Native CI builds and executable smoke tests; no official Forever or in-game testing claimed.
- Windows 0.4.0 download preserved. Startup integration remains Windows-only.

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
