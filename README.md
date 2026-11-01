# Death Atlas Sync 0.3.9

Optional Windows x64 companion for Death Atlas, by Garkoth.

## One file for players

The player download is a single `DeathAtlasSync.exe`. It includes the Python runtime and required dependencies; no Python installation or adjacent source files are needed. The ZIP player download also contains only that executable. This repository is the separate source distribution. License texts and bundled third-party notices are accessible from About → Included licenses inside the executable.

## How it works

1. Install the Death Atlas addon, enter WoW once, enable sharing in /da if needed, then close WoW.
2. Run the EXE. A small window asks for your WoW folder. Use Detect or Choose folder. When multiple accounts are found, choose one.
3. Read the data notice and click OK. This explicitly authorizes uploading the available death history, including earlier records, and downloading Global data.
4. Sync checks the connection and performs an initial synchronization. On success it hides the setup window and thanks you, confirming that it is running in the Windows tray. On failure it shows the error and leaves setup available.
5. The tray menu contains only Configure, About and Close. Configure reopens the same folder window. About explains the application and links to this repository, privacy information and bundled licenses. Close stops the program.

Keep Sync running while you play. It waits for all WoW clients to close before processing saves or replacing the addon cache. Global editions are published daily at 06:00 UTC, rather than in real time. Restart WoW to load a newly downloaded cache.

The app remembers your selected account and existing credentials, protected by current-user Windows DPAPI. The optional **Start automatically with Windows** checkbox is off for a new setup and preserves an existing preference. Click OK to apply it after a successful sync. Check it to start in the tray at your next Windows sign-in; uncheck it and click OK to remove Sync's startup entry. Keep the EXE in a permanent folder. No administrator rights are required. The binary is not digitally signed.

The interface follows the first supported language in the current user's [Windows UI language preferences](https://learn.microsoft.com/en-us/windows/win32/api/winnls/nf-winnls-getuserpreferreduilanguages), rather than the clock/date region. It includes the same eleven catalogs as the addon: enUS, esES, esMX, deDE, frFR, itIT, ptBR, ruRU, koKR, zhCN and zhTW. en-GB uses English, pt-PT uses Portuguese, and Chinese script/region determines simplified or traditional Chinese. Unsupported preferences fall back to the next supported Windows preference, then English. No extra language picker was added to the compact setup.

Catalogs in `locales/*.json` include setup, the tray menu, About, consent, notifications and user-visible diagnostics. Original saved data, region and realm names, protocol values, license legal texts and native Windows controls are not translated or rewritten. All eleven catalogs have matching keys and format placeholders. Automated Tk layout checks passed; the translations have not undergone native-speaker review in every language.

Startup uses only this application's value under the current user's [Windows Run key](https://learn.microsoft.com/en-us/windows/win32/setupapi/run-and-runonce-registry-keys). It does not create a service, scheduled task or administrator-level startup entry. Closing the program stops the current session; it does not uninstall a startup preference you previously enabled.

## Data and limitations

Sync never asks for a WoW or Battle.net password, reads game memory, executes saved/downloaded Lua, or modifies SavedVariables. It validates bounded JSON and writes CommunityData.lua while WoW is closed, retaining the previous cache. Local history is limited to 5,000 records; uploads use batches of at most 25. The addon cache contains up to 30 days / 10,000 cells / 8 MiB, with a narrower realm fallback if necessary.

Existing historical contributions and minimal receipts have no automatic expiry under policy 2026-10-31. Closing the application stops this running process but does not erase earlier contributions. This minimal UI does not provide a server-side erasure action. See [data and privacy](https://garkgames.com/death-atlas/privacy/).

Reports are player-provided, not Blizzard-certified. The owner confirmed the addon/Global round trip in a local Forever lab. Official Forever compatibility and broad language coverage are not claimed verified. Public service enrollment remains closed while release operations are completed; an unknown installation may receive a clear service error even with a correct folder. Publishing the source repository does not open enrollment or publish executable downloads on the website.

## Source, license and tests

Own code: MIT, see [LICENSE](LICENSE.txt). Preserve `THIRD_PARTY` notices and the separately licensed bundled source. This license does not grant rights to Blizzard assets or imply Blizzard endorsement.

Python 3.12 on Windows. No dependency install is needed for most source tests:

```text
python tests/discovery_tests.py
python tests/process_visibility.py
python tests/policy_tests.py
python tests/compact_setup.py
python tests/languages.py
python tests/startup.py
python tests/localized_windows.py
```

`compact_setup.py` uses real Tk widgets with synthetic settings and mocked transport/tray. It tests the success/error distinction, explicit consent, account choice and GitHub link without contacting production. `native_tray.py` additionally needs the dependencies in requirements-build.txt and briefly creates/removes a real tray icon without real profile or network changes. Run native tests only in an interactive Windows session.

## Reproducible build instructions

```text
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --onefile --windowed --hidden-import pystray._win32 --add-data "THIRD_PARTY:THIRD_PARTY" --add-data "LICENSE.txt:." --add-data "locales:locales" --name DeathAtlasSync app.py
```

Run from the repository root. Output: `dist/DeathAtlasSync.exe`. The versioned requirements pin the build dependencies; this is not a bit-for-bit reproducibility guarantee or a code-signing claim. The EXE self-test `--self-test-output <path>` checks Tk, DPAPI and embedded licenses without connecting or changing settings.
