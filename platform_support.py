"""Native POSIX integration. No plaintext credential fallback, shell or game-memory access."""
import os,sys,threading
from pathlib import Path

_key_lock=threading.Lock()
SERVICE='com.garkgames.deathatlassync'
ACCOUNT='settings-encryption-v1'

def tls_context():
 # A standalone Mac does not have the build runner's Python/OpenSSL CA path.
 # Bundle Mozilla roots; keep certificate and hostname verification mandatory.
 import ssl,certifi
 return ssl.create_default_context(cafile=certifi.where())

def settings_path():
 if sys.platform=='win32':return Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'GarkGames/DeathAtlasSync/settings.dpapi'
 if sys.platform=='darwin':return Path.home()/'Library/Application Support/GarkGames/DeathAtlasSync/settings.enc'
 return Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'garkgames/death-atlas-sync/settings.enc'

def native_keyring():
 # Select the actual OS store explicitly: third-party plaintext/fallback backends are never used.
 if sys.platform=='darwin':
  from keyring.backends.macOS import Keyring
 elif sys.platform.startswith('linux'):
  from keyring.backends.SecretService import Keyring
 else:raise RuntimeError('Unsupported credential store')
 return Keyring()

def protect(raw,unprotect=False):
 from cryptography.fernet import Fernet
 with _key_lock:
  backend=native_keyring();key=backend.get_password(SERVICE,ACCOUNT)
  if key is None:
   if unprotect:raise RuntimeError('Native credential key unavailable; existing settings were preserved')
   key=Fernet.generate_key().decode('ascii');backend.set_password(SERVICE,ACCOUNT,key)
   if backend.get_password(SERVICE,ACCOUNT)!=key:raise RuntimeError('Native credential storage verification failed')
  cipher=Fernet(key.encode('ascii'))
 return cipher.decrypt(raw) if unprotect else cipher.encrypt(raw)

def game_running():
 import psutil
 names={'wow.exe','wowb.exe','wowt.exe','wowclassic.exe','wowclassicb.exe','wowforever.exe','world of warcraft','world of warcraft beta','world of warcraft classic','world of warcraft forever'}
 # Only process names are read; no arguments, environment, memory, or game credentials.
 for proc in psutil.process_iter(['name']):
  try:
   name=proc.info.get('name')
   if name and name.casefold() in names:return True
  except psutil.NoSuchProcess:continue
 return False

def acquire_instance():
 import fcntl
 path=settings_path().parent;path.mkdir(parents=True,exist_ok=True,mode=0o700)
 handle=os.fdopen(os.open(path/'instance.lock',os.O_CREAT|os.O_RDWR,0o600),'a')
 try:fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
 except OSError:handle.close();return None
 return handle
