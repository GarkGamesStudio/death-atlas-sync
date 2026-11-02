"""Standard Windows folder distribution. No self-extraction, obfuscation, or AV configuration."""
from pathlib import Path
import hashlib,json,os,platform,subprocess,sys,zipfile
root=Path(__file__).resolve().parents[1];os.chdir(root);sys.path.insert(0,str(root))
assert sys.platform=='win32'
from engine import VERSION
out=root/'release';out.mkdir(exist_ok=True)
subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--noupx','--windowed','--name','DeathAtlasSync','--icon','assets/DeathAtlas.ico','--hidden-import','pystray._win32','--add-data','assets;assets','--add-data','locales;locales','--add-data','LICENSE.txt;.','--add-data','THIRD_PARTY;THIRD_PARTY','app.py'],check=True)
folder=root/'dist/DeathAtlasSync';binary=folder/'DeathAtlasSync.exe'
subprocess.run([str(binary),'--self-test-output',str(out/'native-self-test.json')],check=True,timeout=60)
smoke=json.loads((out/'native-self-test.json').read_text());assert smoke['version']==VERSION and smoke['tk'] and smoke['dpapi'] and smoke['embeddedLicense'] and smoke['localeCount']==11
assert (folder/'_internal/python312.dll').is_file() and (folder/'_internal/assets/Icon64.png').is_file()
readme=f'''Death Atlas Sync {VERSION} — Windows x64 portable folder
By Garkoth / Gark Games

Extract ALL files, then open DeathAtlasSync.exe. Keep the _internal folder next to the EXE. You do not need Python. Put the complete folder in a permanent location before enabling Start with Windows. Moving the EXE alone will break the app.

This is a standard folder distribution with visible runtime files, not the previous self-extracting one-file EXE. It is not digitally signed. The earlier 0.4.0 EXE was detected by Microsoft Defender as Program:Win32/Contebrew.A!ml and submitted to Microsoft for review. That review is pending; no claim of a confirmed false positive or universal antivirus compatibility is made. Do not disable antivirus, add exclusions or restore blocked files to run Sync.

Upgrade: close the old Sync from its tray, keep your existing protected settings, extract this complete folder, open the EXE and review setup. If you use Start with Windows, click OK to update its path. Windows DPAPI settings and connection keys keep the same location and schema. No history or settings reset is required.

Sync works with WoW closed and requires explicit sharing permission. It does not ask for a game password. Official Forever validation remains pending. New uploads join the next successful daily edition at 06:00 UTC.

Español: Extrae TODO el ZIP y abre DeathAtlasSync.exe. Conserva la carpeta _internal al lado del EXE; no muevas solo el ejecutable. No necesitas instalar Python. Cierra el Sync anterior y conserva tu configuración. Si usas Inicio con Windows, pulsa OK en la nueva versión para actualizar la ruta. El EXE no tiene firma digital. La detección de la versión anterior está en revisión; no desactives el antivirus ni añadas exclusiones. Falta validar el cliente oficial de Forever.

Privacy: https://garkgames.com/death-atlas/privacy/
Source / licence: https://github.com/GarkGamesStudio/death-atlas-sync
Issues: https://github.com/GarkGamesStudio/death-atlas-sync/issues/new/choose
'''
(folder/'README.txt').write_text(readme,encoding='utf-8')
target=out/f'DeathAtlasSync-{VERSION}-Windows-x64-Portable.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
 for path in sorted(folder.rglob('*')):
  if path.is_file():z.write(path,path.relative_to(folder).as_posix())
with zipfile.ZipFile(target) as z:assert z.testzip() is None
sha=hashlib.sha256(target.read_bytes()).hexdigest();(out/(target.name+'.sha256')).write_text(sha+'  '+target.name+'\n')
report={'archive':target.name,'bytes':target.stat().st_size,'sha256':sha,'exeSha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'exeBytes':binary.stat().st_size,'sourceCommit':os.environ.get('GITHUB_SHA','local'),'runnerOS':platform.platform(),'architecture':platform.machine(),'distribution':'standard-folder-no-self-extraction','nativeTkAndDPAPISmoke':True,'officialForeverTested':False,'antivirusScan':'separate pre-publication check required','selfTest':smoke}
(out/'BUILD-REPORT.json').write_text(json.dumps(report,indent=2)+'\n');(out/'README.txt').write_text(readme,encoding='utf-8');print(json.dumps(report,indent=2))
