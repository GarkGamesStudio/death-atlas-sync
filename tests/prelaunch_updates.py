"""Synthetic first-install transitions and public update metadata. No network or real game data."""
import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import discovery,engine,updates

class Prelaunch(unittest.TestCase):
 def setUp(self):
  base=Path(__file__).resolve().parents[1]/'.test-fixtures';base.mkdir(exist_ok=True)
  self.tmp=tempfile.TemporaryDirectory(dir=base);self.root=Path(self.tmp.name)/'_forever_'
  self.addon=self.root/'Interface/AddOns/DeathAtlas';self.addon.mkdir(parents=True)
  (self.addon/'DeathAtlas.toc').touch();self.profile=discovery.detect(self.root)[0]
 def tearDown(self):self.tmp.cleanup()
 def save(self,account):
  saved=self.root/'WTF/Account'/account/'SavedVariables/DeathAtlas.lua';saved.parent.mkdir(parents=True);saved.touch();return saved
 def test_pending_without_accounts_reads_no_history(self):
  with patch.object(Path,'read_bytes',side_effect=AssertionError('No reads')):
   self.assertIsNone(engine.ready_profile(self.profile)['saved'])
 def test_first_save_selects_unique_account_without_reading_it(self):
  saved=self.save('FIRST')
  with patch.object(Path,'read_text',side_effect=AssertionError('No history reads')):
   resolved=engine.ready_profile(self.profile)
  self.assertEqual(resolved['saved'],str(saved.resolve()))
 def test_multiple_accounts_require_explicit_selection(self):
  self.save('FIRST');self.save('SECOND')
  with self.assertRaises(engine.CheckError) as error:engine.ready_profile(self.profile)
  self.assertEqual(error.exception.code,'ACCOUNT_CHOICE')
 def test_removed_addon_is_never_synchronized(self):
  (self.addon/'DeathAtlas.toc').unlink()
  with self.assertRaises(engine.CheckError):engine.ready_profile(self.profile)
 def test_no_save_cannot_be_used_as_current_directory(self):
  with patch.object(engine.data,'wow_running',return_value=False):
   with self.assertRaises(engine.CheckError) as error:engine.local_check(self.profile)
  self.assertEqual(error.exception.code,'SAVE_MISSING')
 def test_pending_has_no_erasure_key(self):
  with self.assertRaises(engine.CheckError) as error:engine.request_erasure(self.profile,{},None)
  self.assertEqual(error.exception.code,'NO_KEY')

class UpdateChecks(unittest.TestCase):
 def manifest(self,v='0.4.5'):return {'schema':1,'platforms':{updates.platform_key():{'version':v,'url':'https://evil.invalid/run.exe'}}}
 def test_only_newer_version_and_fixed_download_page(self):
  self.assertEqual(updates.available(self.manifest(),'0.4.4'),{'version':'0.4.5','url':updates.DOWNLOADS})
  self.assertIsNone(updates.available(self.manifest('0.4.4'),'0.4.4'))
  self.assertIsNone(updates.available(self.manifest('0.4.3'),'0.4.4'))
 def test_check_once_per_day_no_credentials_or_history(self):
  state={};calls=[]
  fetch=lambda:(calls.append(True) or self.manifest())
  self.assertTrue(updates.check(state,'0.4.4',100000,fetch)[1])
  state['updates']['notified']='0.4.5'
  self.assertFalse(updates.check(state,'0.4.4',100010,fetch)[1])
  self.assertTrue(updates.check(state,'0.4.4',186400,fetch)[1])
  self.assertEqual(len(calls),2);self.assertEqual(state['updates']['notified'],'0.4.5')
 def test_failure_is_nonfatal_and_rate_limited(self):
  state={}
  def fail():raise OSError('offline')
  self.assertEqual(updates.check(state,'0.4.4',100000,fail),(None,True))
  self.assertEqual(updates.check(state,'0.4.4',100100,fail),(None,False))
 def test_invalid_remote_versions_rejected(self):
  for value in ('0.4.5.exe','1','99999.1.1',None):
   with self.assertRaises(ValueError):updates.available(self.manifest(value),'0.4.4')

if __name__=='__main__':unittest.main()
