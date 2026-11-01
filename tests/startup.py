"""Verify HKCU Run command quoting and removal with a fake registry only."""
import sys,types,unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import engine
class Startup(unittest.TestCase):
 def test_current_user_startup_quotes_spaced_executable(self):
  reg=types.SimpleNamespace(HKEY_CURRENT_USER=1,REG_SZ=1,CreateKey=MagicMock(),SetValueEx=MagicMock(),DeleteValue=MagicMock())
  with patch.dict(sys.modules,{'winreg':reg}),patch.object(engine.sys,'frozen',True,create=True):
   engine.startup(True,r'C:\Program Files\Death Atlas\Sync.exe')
  reg.CreateKey.assert_called_once_with(1,r'Software\Microsoft\Windows\CurrentVersion\Run')
  self.assertEqual(reg.SetValueEx.call_args.args[1],'DeathAtlasSync');self.assertEqual(reg.SetValueEx.call_args.args[-1],'"C:\\Program Files\\Death Atlas\\Sync.exe" --background')
 def test_disable_removes_only_the_sync_value(self):
  reg=types.SimpleNamespace(HKEY_CURRENT_USER=1,REG_SZ=1,CreateKey=MagicMock(),SetValueEx=MagicMock(),DeleteValue=MagicMock())
  with patch.dict(sys.modules,{'winreg':reg}):engine.startup(False)
  self.assertEqual(reg.DeleteValue.call_args.args[-1],'DeathAtlasSync');reg.SetValueEx.assert_not_called()
 def test_source_cannot_enable_startup(self):
  with patch.object(engine.sys,'frozen',False,create=True):
   with self.assertRaises(engine.SyncError):engine.startup(True)
if __name__=='__main__':unittest.main()
