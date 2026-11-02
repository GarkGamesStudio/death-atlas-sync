"""Native Linux Tk recovery flows under Xvfb. Synthetic settings; no upload or game profile."""
import sys,os,unittest,time
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import linux_credentials as c

@unittest.skipUnless(sys.platform.startswith('linux') and os.environ.get('DISPLAY'),'Requires native Linux desktop display')
class Desktop(unittest.TestCase):
 def setUp(self):
  import tkinter as tk
  self.root=tk.Tk();self.root.withdraw()
  self.store=Mock();self.store.read.return_value={'schema':1,'profiles':{},'enabled':False}
  self.check=patch.object(c,'check',return_value=None);self.check.start();self.addCleanup(self.check.stop)
  self.addCleanup(self.destroy)
 def destroy(self):
  try:self.root.destroy()
  except Exception:pass
 def settle(self,predicate):
  deadline=time.monotonic()+4
  while not predicate() and time.monotonic()<deadline:self.root.update();time.sleep(.01)
  self.assertTrue(predicate())
 def test_ready_settings_open_actual_setup_without_second_read_or_upload(self):
  from linux_desktop import Setup
  from app import App
  opened=[]
  with patch.object(App,'rescan'),patch.object(App,'loop'):
   def ready(state):opened.append(App(self.root,self.store,'https://example.invalid',state=state))
   view=Setup(self.root,self.store,ready);self.settle(lambda:bool(opened))
   self.store.read.assert_called_once();self.store.write.assert_not_called();self.assertIs(opened[0].state,self.store.read.return_value);opened[0].close()
 def test_existing_config_failure_stays_open_and_does_not_replace_settings(self):
  from linux_desktop import Setup
  from localization import tr
  ready=Mock();self.store.read.side_effect=ValueError('private data');view=Setup(self.root,self.store,ready)
  self.settle(lambda:view.status.get()==tr('linux_config'));ready.assert_not_called();self.store.write.assert_not_called()
 def test_help_keeps_package_example_visible_and_read_only(self):
  from linux_desktop import Setup
  from localization import tr
  import gc
  with patch.object(c,'instructions',return_value=('Test distro','example command')):
   view=Setup(self.root);self.settle(lambda:view.status.get()==tr('linux_ready'));gc.collect()
   self.assertEqual(view.command.get(),'example command')
   entries=[child for child in view.details.winfo_children() if child.winfo_class()=='TEntry']
   self.assertEqual(len(entries),1);self.assertEqual(str(entries[0]['state']),'readonly')
 def test_cancelled_unlock_can_retry_without_starting_sync(self):
  from linux_desktop import Setup
  from localization import tr
  c.check.side_effect=c.CredentialError('locked');ready=Mock();view=Setup(self.root,self.store,ready)
  self.settle(lambda:view.status.get()==tr('linux_locked'));self.store.read.assert_not_called();self.assertEqual(str(view.unlock['state']),'normal')
  c.check.side_effect=None;view.unlock.invoke();self.settle(lambda:ready.called)
  c.check.assert_called_with(unlock=True);self.store.write.assert_not_called()

if __name__=='__main__':unittest.main()
