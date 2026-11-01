"""Temporary installation fixtures; never reads real histories or Windows settings."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import discovery
from app import App

def install(root,account='TEST'):
 addon=root/'Interface'/'AddOns'/'DeathAtlas';addon.mkdir(parents=True,exist_ok=True)
 (addon/'DeathAtlas.toc').write_text('fixture')
 saved=root/'WTF'/'Account'/account/'SavedVariables'/'DeathAtlas.lua';saved.parent.mkdir(parents=True,exist_ok=True)
 saved.write_text('NOT EXECUTABLE LUA')
 return {'saved':str(saved.resolve()),'addon':str(addon.resolve())}

class DiscoveryTests(unittest.TestCase):
 def setUp(self):
  base=Path(__file__).resolve().parents[1]/'.test-fixtures';base.mkdir(parents=True,exist_ok=True)
  self.tmp=tempfile.TemporaryDirectory(dir=base);self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def test_forever_and_retail_found_from_parent(self):
  forever=install(self.root/'_forever_');retail=install(self.root/'_retail_')
  self.assertEqual(discovery.detect(self.root),[forever,retail])
 def test_client_executable_path(self):
  profile=install(self.root/'_forever_')
  self.assertIn(profile,discovery.detect(self.root/'_forever_'/'WoW.exe'))
 def test_multiple_accounts(self):
  install(self.root,'SECOND');install(self.root,'FIRST')
  self.assertEqual(len(discovery.detect(self.root)),2)
 def test_missing_addon_or_history_is_not_syncable(self):
  self.assertEqual(discovery.detect(self.root),[])
  addon=self.root/'Interface'/'AddOns'/'DeathAtlas';addon.mkdir(parents=True);(addon/'DeathAtlas.toc').touch()
  self.assertEqual(discovery.detect(self.root),[])
 def test_duplicates_and_sibling_clients(self):
  p=install(self.root/'_forever_');q=install(self.root/'_retail_')
  with patch.object(discovery,'automatic_roots',return_value=[self.root,self.root/'_forever_']):
   self.assertEqual(discovery.discover(),[p,q])
 def test_launcher_config_reads_only_location_fields(self):
  config=self.root/'Battle.net'/'Battle.net.config';config.parent.mkdir()
  config.write_text(json.dumps({'Games':{'wow':{'LastInstallPath':str(self.root/'Game')}},'secret':'do-not-collect'}))
  with patch.dict(os.environ,{'APPDATA':str(self.root),'LOCALAPPDATA':str(self.root),'PROGRAMDATA':str(self.root)}):
   self.assertEqual(discovery.unique(discovery.battle_net_roots()),[self.root/'Game'])
 def test_broken_launcher_config(self):
  config=self.root/'Battle.net'/'Battle.net.config';config.parent.mkdir();config.write_text('invalid')
  with patch.dict(os.environ,{'APPDATA':str(self.root),'LOCALAPPDATA':str(self.root),'PROGRAMDATA':str(self.root)}):self.assertEqual(discovery.battle_net_roots(),[])
 def test_other_fixed_drive_candidates(self):
  with patch.object(discovery,'registry_roots',return_value=[]),patch.object(discovery,'battle_net_roots',return_value=[]),patch.object(discovery,'fixed_drives',return_value=[self.root]):
   self.assertIn(self.root/'Games'/'WoW Forever',discovery.automatic_roots())
 def test_history_content_is_never_read(self):
  p=install(self.root)
  with patch.object(Path,'read_text',side_effect=AssertionError('Must not parse history')):
   self.assertEqual(discovery.detect(self.root),[p])
 def test_permission_failure_skips_one_install(self):
  install(self.root)
  with patch.object(Path,'iterdir',side_effect=PermissionError):self.assertEqual(discovery.detect(self.root),[])
 def test_path_case_duplicates_on_windows(self):
  if os.name=='nt':self.assertEqual(len(discovery.unique([self.root,str(self.root).upper()])),1)
 def test_manual_selection_survives_rescan(self):
  class Value:
   def set(self,value):self.value=value
  class Combo(dict):
   index=-1
   def current(self,index=None):
    if index is not None:self.index=index
    return self.index
  p=install(self.root/'_forever_');q=install(self.root/'_retail_')
  app=object.__new__(App);app.combo=Combo();app.selection=Value();app.status=Value();app.folder=Value()
  App.set_candidates(app,[p,q],q);self.assertEqual(app.combo.current(),1)
 def test_ambiguous_results_require_choice(self):
  class Selection:
   def __init__(self,combo):self.combo=combo
   def set(self,value):self.combo.index=-1
  class Value:
   def set(self,value):pass
  class Combo(dict):
   index=-1
   def current(self,index=None):
    if index is not None:self.index=index
    return self.index
  p=install(self.root/'_forever_');q=install(self.root/'_retail_')
  app=object.__new__(App);app.combo=Combo();app.selection=Selection(app.combo);app.status=Value();app.folder=Value()
  App.set_candidates(app,[p,q]);self.assertEqual(app.combo.current(),-1)
  App.set_candidates(app,[p]);self.assertEqual(app.combo.current(),0)

if __name__=='__main__':unittest.main()
