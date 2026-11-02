"""Portable boundaries: encryption, native-store refusal, paths and process guard."""
import sys,unittest,types,tempfile,os
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import platform_support as p

class Platforms(unittest.TestCase):
 def test_bundled_tls_verification(self):
  import ssl
  context=p.tls_context();self.assertTrue(context.check_hostname);self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED);self.assertGreater(context.cert_store_stats()['x509_ca'],0)
 def test_encryption_roundtrip_and_no_plaintext(self):
  values={};backend=Mock();backend.get_password.side_effect=lambda s,k:values.get((s,k));backend.set_password.side_effect=lambda s,k,v:values.__setitem__((s,k),v)
  with patch.object(p,'native_keyring',return_value=backend):
   data=p.protect(b'synthetic-key-not-a-real-user');self.assertNotIn(b'synthetic-key',data);self.assertEqual(p.protect(data,True),b'synthetic-key-not-a-real-user')
 def test_missing_or_locked_keyring_does_not_replace_key(self):
  backend=Mock();backend.get_password.return_value=None
  with patch.object(p,'native_keyring',return_value=backend):
   with self.assertRaises(RuntimeError):p.protect(b'old ciphertext',True)
  backend.set_password.assert_not_called()
  with patch.object(p,'native_keyring',side_effect=RuntimeError('locked')):
   with self.assertRaises(RuntimeError):p.protect(b'secret')
 def test_bad_ciphertext_is_rejected(self):
  from cryptography.fernet import Fernet,InvalidToken
  backend=Mock();backend.get_password.return_value=Fernet.generate_key().decode()
  with patch.object(p,'native_keyring',return_value=backend):
   with self.assertRaises(InvalidToken):p.protect(b'modified',True)
 def test_desktop_paths(self):
  with patch.object(p.sys,'platform','darwin'):self.assertIn('Library/Application Support',p.settings_path().as_posix())
  with patch.object(p.sys,'platform','linux'),patch.dict(os.environ,{'XDG_CONFIG_HOME':'/tmp/fixture-config'}):self.assertEqual(p.settings_path().as_posix(),'/tmp/fixture-config/garkgames/death-atlas-sync/settings.enc')
 def test_game_guard_native_and_wine(self):
  module=types.SimpleNamespace(NoSuchProcess=type('Gone',(Exception,),{}),process_iter=Mock())
  with patch.dict(sys.modules,{'psutil':module}):
   for name in ['World of Warcraft','WoW.exe','WoWForever.exe']:
    module.process_iter.return_value=[types.SimpleNamespace(info={'name':name})];self.assertTrue(p.game_running())
   module.process_iter.return_value=[types.SimpleNamespace(info={'name':'other-app'})];self.assertFalse(p.game_running())
   module.process_iter.side_effect=OSError('enumeration failed')
   with self.assertRaises(OSError):p.game_running()
 def test_no_plaintext_backend_selection(self):
  with patch.object(p.sys,'platform','unsupported'):
   with self.assertRaises(RuntimeError):p.native_keyring()
 def test_single_instance_lock(self):
  if os.name=='nt':self.skipTest('POSIX flock is exercised on native CI runners')
  with tempfile.TemporaryDirectory() as folder,patch.object(p,'settings_path',return_value=Path(folder)/'settings.enc'):
   first=p.acquire_instance();self.assertIsNotNone(first);self.assertIsNone(p.acquire_instance());first.close();second=p.acquire_instance();self.assertIsNotNone(second);second.close()

if __name__=='__main__':unittest.main()
