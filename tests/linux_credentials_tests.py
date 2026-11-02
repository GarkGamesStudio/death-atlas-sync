"""Linux keyring recovery boundaries; synthetic services only, no player files or network."""
import sys,types,unittest,tempfile
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import linux_credentials as c

class Credentials(unittest.TestCase):
 def setUp(self):
  ex=types.SimpleNamespace(**{name:type(name,(Exception,),{}) for name in ('ItemNotFoundException','PromptDismissedException','LockedException','SecretServiceNotAvailableException')})
  self.bus=Mock();self.item=Mock();self.item.connection=self.bus;self.item.is_locked.return_value=False
  self.ss=types.SimpleNamespace(exceptions=ex,dbus_init=Mock(return_value=self.bus),check_service_availability=Mock(return_value=True),get_collection_by_alias=Mock(return_value=self.item))
  self.patch=patch.dict(sys.modules,{'secretstorage':self.ss,'secretstorage.exceptions':ex});self.patch.start();self.addCleanup(self.patch.stop)
 def expect(self,code,callback):
  with self.assertRaises(c.CredentialError) as result:callback()
  self.assertEqual(result.exception.code,code);self.assertNotIn('private',str(result.exception))
 def test_ready_closes_bus_without_secret_read_or_write(self):
  c.check();self.bus.close.assert_called_once();self.item.unlock.assert_not_called();self.item.get_secret.assert_not_called();self.item.create_item.assert_not_called()
 def test_unavailable_session_and_service_have_distinct_safe_errors(self):
  self.ss.dbus_init.side_effect=RuntimeError('private-details');self.expect('session',c.check)
  self.ss.dbus_init.side_effect=None;self.ss.check_service_availability.return_value=False;self.expect('missing',c.check);self.bus.close.assert_called_once()
 def test_missing_collection_is_not_created_silently(self):
  self.ss.get_collection_by_alias.side_effect=self.ss.exceptions.ItemNotFoundException();self.expect('collection',c.check);self.bus.close.assert_called_once()
 def test_locked_check_never_opens_a_prompt(self):
  self.item.is_locked.return_value=True;self.expect('locked',c.check);self.item.unlock.assert_not_called();self.bus.close.assert_called_once()
 def test_explicit_unlock_is_bounded_and_can_be_cancelled(self):
  self.item.is_locked.side_effect=[True,False];self.item.unlock.return_value=False;c.check(unlock=True);self.item.unlock.assert_called_once_with(timeout=60)
  self.item.is_locked.side_effect=None;self.item.is_locked.return_value=True;self.item.unlock.return_value=True;self.expect('locked',lambda:c.check(unlock=True))
 def test_unlock_timeout_is_recoverable_and_closes_connection(self):
  self.item.is_locked.return_value=True;self.item.unlock.side_effect=TimeoutError('private-details');self.expect('locked',lambda:c.check(unlock=True));self.bus.close.assert_called_once()
 def test_distro_examples_cannot_execute_or_interpolate_untrusted_data(self):
  base=Path(__file__).resolve().parents[1]/'.test-fixtures';base.mkdir(exist_ok=True)
  with tempfile.TemporaryDirectory(dir=base) as folder:
   p=Path(folder)/'os-release'
   for value,command in [('ID=ubuntu','sudo apt install gnome-keyring seahorse'),('ID=manjaro','sudo pacman -S gnome-keyring seahorse'),('ID=fedora','sudo dnf install gnome-keyring seahorse'),('ID=opensuse-tumbleweed','sudo zypper install gnome-keyring seahorse'),('ID=\"$(private)\"','')]:
    p.write_text(value);self.assertEqual(c.instructions(p)[1],command)
 def test_every_error_is_translated_without_private_details(self):
  import engine,localization
  with patch.object(engine.sys,'platform','linux'):
   for locale in localization.LOCALES:
    localization.set_language(locale)
    for code in ('session','missing','locked','collection','store','key','config'):
     message=engine.describe_error(c.CredentialError(code));self.assertIn('[KEYRING_',message);self.assertIn(localization.tr('linux_'+code),message)
  localization.set_language('enUS')

if __name__=='__main__':unittest.main()
