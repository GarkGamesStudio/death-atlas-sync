# macOS and Linux setup and update notifications — 0.4.4

The native 0.4.4 builds bring addon-only setup, bounded discovery and daily update notices to macOS Intel, macOS Apple Silicon and Linux x64. Configure before your first WoW login, without deaths or history; Sync waits for the first addon save. Open About for a newer-version download link. No automatic download or installation is performed. Preserve existing encrypted settings and the system keyring when upgrading. Windows 0.4.4 stays available separately.

**Not tested with WoW or the official Forever client.** Native CI tests the first-install flow, account selection, updates, eleven language layouts, privacy contracts and the actual packaged Tk/credential-store startup. macOS is not Developer ID signed or notarized. Linux keeps its visible window and keyring recovery/help; X11/XWayland and an unlocked Secret Service keyring remain required. No automatic startup is included on macOS/Linux.

# Windows setup and update notifications — 0.4.4

Windows setup now accepts an installed Death Atlas addon before the first game login. No account save or death history is required to click OK. Sync stays in the background waiting for the first addon save; enable the addon and Sharing in `/da`, then close WoW. Detection proves the addon is installed, not that it is enabled in the game. Once a unique account save appears, Sync selects it without reading history until WoW is closed. If multiple accounts appear, use Configure and Detect to choose one. Missing addons have explicit installation guidance. Detect also checks common portable game folders at one bounded directory level, including custom folder names.

Once configured and enabled, Sync checks public version metadata at `https://garkgames.com/death-atlas/sync-updates.json` at most once every 24 hours. This request contains no history, installation path, account identifier or Sync key. A newer version produces a tray notification and a download button in About. The button opens the fixed website download page; Sync never downloads or executes a new program automatically. An update-check failure does not block synchronization. Published macOS/Linux binaries retain their previous behavior until rebuilt.

Extract the entire Windows ZIP and keep `_internal` beside the EXE. Close the previous Sync before upgrading, preserve existing settings and click OK if you use Start with Windows, to update its path. Native CI, local antivirus scan results and package checksums are recorded on each release; unsigned software cannot guarantee acceptance by all antivirus products.

# Windows portable folder — 0.4.3

Use the [Windows 0.4.3 release](https://github.com/GarkGamesStudio/death-atlas-sync/releases/tag/v0.4.3) or [website downloads](https://garkgames.com/death-atlas/about/#downloads). **Extract the entire ZIP and keep `_internal` beside `DeathAtlasSync.exe`.** No Python installation is needed. Close the older Sync before upgrading and keep its existing protected settings. If you use Start with Windows, click OK in the new setup to update its path.

The standard folder distribution replaces the earlier self-extracting one-file EXE. Native Windows CI tests the real tray, eleven interface languages, consent, settings, optional startup and packaged Tk/DPAPI. The exact package was additionally scanned with Defender signatures 1.463.84.0 on 2026-11-02, with real-time protection enabled: no detections in that scan. Local packaged startup also passed. Reports and checksums are attached to the release. These checks do not guarantee other antivirus products or future definitions. The app is unsigned; official Forever validation remains pending.

Microsoft detected the old 0.4.0 EXE as Program:Win32/Contebrew.A!ml. Review is pending; no confirmed false-positive claim is made. Do not disable protection, add exclusions, or restore a blocked file to run Sync. macOS 0.4.1 and Linux 0.4.2 packages are unchanged.

# Linux desktop update — 0.4.2

Linux now checks its secure storage before opening setup and provides a recovery screen instead of closing with a generic error. **Linux help** is available from setup, with translated messages in all eleven languages. **Unlock with the system** opens the system's own prompt, with a 60-second limit; Sync never receives the keyring password. Cancel and retry are supported. Missing services, missing default keyrings and inaccessible existing settings have separate guidance.

Package-manager examples are shown for Debian/Ubuntu/Mint, Fedora, Arch/Manjaro and openSUSE. Users install/configure providers themselves; Sync never runs installation commands, changes desktop settings, deletes keyrings or falls back to plaintext. Existing settings and encryption keys are preserved. Linux keeps its window open or minimized; automatic startup remains unavailable.

The published macOS 0.4.1 and Windows 0.4.0 packages are unchanged. **Linux is still not tested with WoW or official Forever.** Native CI exercises recovery, retry, cancellation, real Tk startup and the real credential store using fixtures only.

# macOS and Linux preview — 0.4.1

Download the native packages, checksums and build reports from [the macOS / Linux preview release](https://github.com/GarkGamesStudio/death-atlas-sync/releases/tag/v0.4.1-posix), or use [the website downloads](https://garkgames.com/death-atlas/about/#downloads).

New native builds for macOS Intel, macOS Apple Silicon and Linux x64. **Not tested with WoW or the official Forever service.** CI builds and launches the real packaged program and checks Tk and the native credential store; this is not an in-game or desktop usability test.

Windows users should use the 0.4.3 standard folder described above. The original 0.4.0 self-extracting EXE is under Microsoft review.

macOS: encrypted settings use macOS Keychain. The application is not Developer ID signed or notarized. Linux: encrypted settings require an unlocked Secret Service keyring, glibc >=2.35 and X11/XWayland. Linux keeps a visible, minimizable window; closing it stops sync. No automatic startup is included on macOS/Linux. macOS uses its menu-bar icon when available and otherwise keeps the window visible. Manual folder selection supports custom Wine/Lutris/Steam layouts if bounded detection misses them.

Native build workflow: .github/workflows/build-posix.yml. Each OS builds its own archive; there is no Windows-to-macOS cross compilation. tools/build_posix.py collects dependency licence notices and emits per-archive SHA-256 and BUILD-REPORT.json. No player history, production credentials or upload endpoint is used in these tests.

Privacy and erasure operations use the same service contract as Windows. No plaintext credential fallback is allowed. If the native keyring is missing/locked or process detection fails, synchronization stops before reading/writing the game cache. Keep the operating system protections enabled.

---

# Death Atlas Sync 0.4.0

Optional Windows x64 companion for Death Atlas, by Garkoth.

## Selected icon

Uses the original parchment map and red skull-pin emblem selected by Garkoth. Shared by the EXE resource, Windows title bars, About window and tray. The matching addon icon is included in Death Atlas 0.6.6. Assets are generated project artwork, not extracted Blizzard artwork, and are provided under the project MIT license.

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

Historical contributions have no automatic expiry under policy 2026-11-01. Closing Sync does not erase them. About → Remove shared data confirms an authenticated removal request for the selected installation. Uploads stop even if the response is lost. Retry the same action to check completion; keep your saved connection key. Removal appears in the next successful daily edition at 06:00 UTC. Local history is untouched; copies downloaded by others cannot be recalled. See [data and privacy](https://garkgames.com/death-atlas/privacy/) for old server copies and recovery limits.

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
python -m PyInstaller --noconfirm --onefile --windowed --hidden-import pystray._win32 --add-data "THIRD_PARTY:THIRD_PARTY" --add-data "LICENSE.txt:." --add-data "locales:locales" --add-data "assets:assets" --icon "assets/DeathAtlas.ico" --name DeathAtlasSync app.py
```

Run from the repository root. Output: `dist/DeathAtlasSync.exe`. The versioned requirements pin the build dependencies; this is not a bit-for-bit reproducibility guarantee or a code-signing claim. The EXE self-test `--self-test-output <path>` checks Tk, DPAPI and embedded licenses without connecting or changing settings.

## Retirar tus aportes

En Acerca de, Eliminar datos compartidos solicita el retiro de la instalación seleccionada. Requiere confirmación y su clave DPAPI guardada; no se envían claves por correo. Detiene los envíos incluso si la respuesta se pierde. Repetir el botón consulta/reintenta de forma segura. El servicio retira los aportes en la siguiente edición diaria exitosa a las 06:00 UTC. No borra SavedVariables ni el historial local. Las copias descargadas por otros usuarios no pueden retirarse. No borres tu configuración antes de completar el trámite. Consulta la política web para la conservación de copias antiguas.
