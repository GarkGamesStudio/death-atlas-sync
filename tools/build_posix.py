"""Build on the target OS; produce real archives and a machine-readable build report."""
from pathlib import Path
import hashlib,json,os,platform,subprocess,sys,tarfile,zipfile,shutil
import importlib.metadata as metadata
from PIL import Image
root=Path(__file__).resolve().parents[1];os.chdir(root)
assert sys.platform in ('darwin','linux')
licenses=root/'THIRD_PARTY/POSIX-LICENSES';licenses.mkdir(parents=True,exist_ok=True)
for dist in metadata.distributions():
 for file in dist.files or []:
  if any(word in str(file).lower() for word in ('license','copying','notice')) and '.dist-info/' in str(file):
   path=Path(dist.locate_file(file))
   if path.is_file() and path.stat().st_size<1000000:
    target=licenses/dist.metadata['Name']/str(file);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(path.read_bytes())
args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--name','DeathAtlasSync','--add-data','assets:assets','--add-data','locales:locales','--add-data','LICENSE.txt:.','--add-data','THIRD_PARTY:THIRD_PARTY','--collect-submodules','keyring.backends','--copy-metadata','keyring','--copy-metadata','cryptography']
if sys.platform=='darwin':
 Image.open('assets/DeathAtlas.ico').save('assets/DeathAtlas.icns',format='ICNS')
 args+=['--windowed','--onedir','--icon','assets/DeathAtlas.icns','--osx-bundle-identifier','com.garkgames.deathatlassync']
else:args+=['--onefile']
subprocess.run(args+['app.py'],check=True)
out=root/'release';out.mkdir(exist_ok=True)
machine=platform.machine();suffix='macOS-'+('arm64' if machine=='arm64' else 'x64') if sys.platform=='darwin' else 'Linux-x64'
name='DeathAtlasSync-0.4.1-'+suffix
readme='''Death Atlas Sync 0.4.1 — macOS / Linux preview

NOT TESTED WITH WOW. Built on native CI runners with automated checks; this does not establish compatibility with the official Forever client.

macOS: extract the ZIP and place DeathAtlasSync.app in Applications. Choose your WoW folder and review the sharing permission. The app is not Developer ID signed or notarized; macOS may block it. No Apple security settings are changed by this app.
Linux x64: extract the tar.gz, then run ./DeathAtlasSync. Requires glibc 2.35 or newer, an X11/XWayland display, and an unlocked Secret Service keyring (such as GNOME Keyring). Keep its window open or minimized; closing it stops Sync. Desktop tray integration and automatic startup are not included for Linux. Automatic startup is also not included on macOS.

Credentials: macOS Keychain / Linux Secret Service protect the encryption key. Settings are encrypted on disk. There is no plaintext fallback; a locked or missing keyring stops synchronization.
Sync only works with WoW closed. If detection misses your Wine/Lutris/Steam installation, choose the folder containing Interface and WTF manually. No game password is required. Never share settings.enc or connection keys.

Español: NO PROBADO CON WOW. Esta compilación pasó comprobaciones automáticas, pero no valida el cliente oficial de Forever. Elige tu carpeta de WoW y revisa el permiso. Cierra WoW antes de sincronizar. En Linux deja la ventana abierta o minimizada; necesita X11/XWayland y un llavero Secret Service desbloqueado. No se incluye inicio automático en macOS/Linux. La app de Mac no tiene firma Developer ID ni notarización.

Privacy: https://garkgames.com/death-atlas/privacy/
Source, licence and issues: https://github.com/GarkGamesStudio/death-atlas-sync
'''
(out/'README.txt').write_text(readme,encoding='utf-8')
# Self-test exercises actual Tk and the native credential store; no game profile or network is used.
binary=root/'dist/DeathAtlasSync.app/Contents/MacOS/DeathAtlasSync' if sys.platform=='darwin' else root/'dist/DeathAtlasSync'
subprocess.run([str(binary),'--self-test-output',str(out/'native-self-test.json')],check=True,timeout=90)
smoke=json.loads((out/'native-self-test.json').read_text());assert smoke['tk'] and smoke['dpapi'] and smoke['embeddedLicense'] and smoke['localeCount']==11
if sys.platform=='darwin':
 target=out/(name+'.zip')
 # ditto preserves application symlinks, executable bits and the native bundle layout.
 subprocess.run(['ditto','-c','-k','--sequesterRsrc','--keepParent','dist/DeathAtlasSync.app',str(target)],check=True)
 # Keep the instructions next to the app in the distribution.
 with zipfile.ZipFile(target,'a',zipfile.ZIP_DEFLATED) as z:z.write(out/'README.txt','README.txt')
else:
 target=out/(name+'.tar.gz')
 with tarfile.open(target,'w:gz') as z:
  z.add(binary,arcname='DeathAtlasSync');z.add(out/'README.txt',arcname='README.txt')
sha=hashlib.sha256(target.read_bytes()).hexdigest();(out/(target.name+'.sha256')).write_text(sha+'  '+target.name+'\n')
report={'archive':target.name,'sha256':sha,'bytes':target.stat().st_size,'platform':sys.platform,'architecture':machine,'runnerOS':platform.platform(),'sourceCommit':os.environ.get('GITHUB_SHA','local'),'nativeTkAndCredentialStoreSmoke':True,'withWoWTested':False,'officialForeverTested':False,'selfTest':smoke}
(out/'BUILD-REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
