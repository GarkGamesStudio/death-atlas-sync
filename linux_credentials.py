"""Linux desktop credential checks. Never installs packages or reads passwords into the UI."""
from pathlib import Path
from contextlib import closing
import os

class CredentialError(RuntimeError):
 def __init__(self,code):self.code=code;super().__init__(code)

def collection(unlock=False):
 import secretstorage as ss
 from secretstorage import exceptions as ex
 try:bus=ss.dbus_init()
 except Exception:raise CredentialError('session') from None
 try:
  if not ss.check_service_availability(bus):raise CredentialError('missing')
  try:result=ss.get_collection_by_alias(bus,'default')
  except ex.ItemNotFoundException:raise CredentialError('collection') from None
  if result.is_locked():
   if not unlock:raise CredentialError('locked')
   # The system displays its own password prompt. Never ask for the password here.
   if result.unlock(timeout=60) or result.is_locked():raise CredentialError('locked')
  return result
 except Exception as error:
  bus.close()
  if isinstance(error,CredentialError):raise
  if isinstance(error,(TimeoutError,ex.PromptDismissedException,ex.LockedException)):raise CredentialError('locked') from None
  if isinstance(error,ex.SecretServiceNotAvailableException):raise CredentialError('missing') from None
  raise CredentialError('store') from None

def check(unlock=False):
 value=collection(unlock)
 with closing(value.connection):pass

def backend():
 from keyring.backends.SecretService import Keyring
 class DesktopKeyring(Keyring):
  def get_preferred_collection(self):return collection()
  def unlock(self,item):
   # Background reads must not wait indefinitely for a desktop password prompt.
   if item.is_locked():raise CredentialError('locked')
  def get_password(self,*args,**kwargs):
   try:return super().get_password(*args,**kwargs)
   except CredentialError:raise
   except Exception:raise CredentialError('store') from None
  def set_password(self,*args,**kwargs):
   try:return super().set_password(*args,**kwargs)
   except CredentialError:raise
   except Exception:raise CredentialError('store') from None
 return DesktopKeyring()

def instructions(path=Path('/etc/os-release')):
 """Only fixed command examples; never execute shell commands or interpolate OS data."""
 try:
  fields=dict(line.split('=',1) for line in path.read_text().splitlines() if '=' in line)
  ids=set((fields.get('ID','')+' '+fields.get('ID_LIKE','')).replace('"','').replace("'",'').split())
 except (OSError,ValueError):ids=set()
 if ids & {'debian','ubuntu','linuxmint'}:return 'Debian / Ubuntu / Mint', 'sudo apt install gnome-keyring seahorse'
 if ids & {'fedora','rhel','centos'}:return 'Fedora', 'sudo dnf install gnome-keyring seahorse'
 if ids & {'arch','manjaro','endeavouros'}:return 'Arch / Manjaro', 'sudo pacman -S gnome-keyring seahorse'
 if ids & {'opensuse','opensuse-tumbleweed','opensuse-leap','suse'}:return 'openSUSE', 'sudo zypper install gnome-keyring seahorse'
 return 'Linux', ''
