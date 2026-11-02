"""Real Tk widgets, mocked transport/tray, synthetic profiles; no real settings writes."""
import copy,gc,sys,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app

class Store:
 def __init__(self):self.writes=[]
 def read(self):return {'schema':1,'profiles':{},'enabled':False}
 def write(self,value):self.writes.append(copy.deepcopy(value))
class Icon:
 def stop(self):pass
 def notify(self,*args):pass
def tray(ui):ui.icon=Icon();ui.tray_ready.set()
PROFILES=[{'addon':str(Path('fixture-'+name)/'Interface'/'AddOns'/'DeathAtlas'),'saved':str(Path('fixture-'+name)/'WTF'/'Account'/'TEST'/'SavedVariables'/'DeathAtlas.lua')} for name in ('forever','retail')]

class CompactSetup(unittest.TestCase):
 def setUp(self):
  self.patchers=[patch.object(app.App,'tray',tray),patch.object(app.App,'loop'),patch.object(app.engine,'discover',return_value=[]),patch.object(app.messagebox,'showinfo'),patch.object(app.messagebox,'showerror')]
  self.mocks=[p.start() for p in self.patchers]
  self.root=app.tk.Tk();self.root.withdraw();self.store=Store();self.ui=app.App(self.root,self.store,app.engine.DEFAULT_SERVICE)
  self.ui.scan_generation+=1;self.ui.scanning=False
 def tearDown(self):
  if not self.ui.quit.is_set():self.ui.close()
  for p in reversed(self.patchers):p.stop()
  # Release destroyed Tcl interpreters on their owning GUI thread before another
  # test starts a worker (whose allocations may otherwise trigger cyclic GC).
  self.ui=None;self.root=None;self.mocks=[];self.patchers=[];gc.collect()
 def wait(self):
  deadline=time.monotonic()+3
  while self.ui.busy and time.monotonic()<deadline:self.root.update();time.sleep(.01)
  self.assertFalse(self.ui.busy)
 def test_initial_detection_does_not_authorize_upload(self):
  self.ui.set_candidates(PROFILES[:1]);self.assertEqual(self.store.writes,[]);self.assertTrue(self.ui.paused.is_set());self.assertFalse(self.ui.account_row.winfo_manager())
 def test_prelaunch_setup_accepts_addon_without_history_or_network(self):
  pending=dict(PROFILES[0],saved=None);self.ui.set_candidates([pending])
  with patch.object(app.engine,'sync_profile',side_effect=AssertionError('No upload before save')) as sync:
   self.ui.start();self.wait();sync.assert_not_called()
  self.assertTrue(self.ui.state['enabled']);self.assertFalse(self.ui.paused.is_set())
  self.assertIsNone(self.ui.state['selected']['saved']);self.assertEqual(self.ui.last_status,app.tr('pending_save'))
  self.assertEqual(self.mocks[3].call_args.args[1],app.tr('pending_success'))
 def test_multiple_accounts_require_choice(self):
  self.ui.set_candidates(PROFILES);self.ui.folder.set('')
  self.ui.start();self.assertTrue(self.mocks[4].called);self.assertEqual(self.store.writes,[])
 def test_success_really_syncs_before_hiding_and_thanking(self):
  self.ui.set_candidates(PROFILES[:1])
  def sync(profile,state,store,service,stopped):
   self.assertTrue(state['consent']);self.assertFalse(state['enabled']);self.assertTrue(self.ui.paused.is_set());self.assertFalse(self.mocks[3].called)
   return {'sent':1,'cached':True}
  with patch.object(app.engine,'sync_profile',side_effect=sync) as transport:
   self.ui.start();self.wait();self.assertEqual(transport.call_count,1)
  self.assertTrue(self.store.writes[-1]['enabled']);self.assertFalse(self.ui.paused.is_set());self.assertEqual(self.root.state(),'withdrawn');self.assertEqual(app.tr('success'),self.mocks[3].call_args.args[1])
 def test_error_keeps_configuration_and_does_not_claim_success(self):
  self.ui.set_candidates(PROFILES[:1])
  with patch.object(app.engine,'sync_profile',side_effect=app.engine.SyncError('Fixture connection failure')),patch.object(self.ui,'configure') as show:
   self.ui.start();self.wait();self.assertTrue(show.called)
  self.assertTrue(self.ui.paused.is_set());self.assertFalse(self.ui.state['enabled']);self.assertTrue(self.mocks[4].called);self.assertFalse(self.mocks[3].called)
 def test_tray_failure_prevents_upload(self):
  self.ui.set_candidates(PROFILES[:1]);self.ui.icon=None
  with patch.object(app.engine,'sync_profile') as transport,patch.object(self.ui,'configure'):
   self.ui.start();self.wait();transport.assert_not_called()
  self.assertEqual(self.store.writes,[]);self.assertTrue(self.mocks[4].called)
 def test_new_folder_cannot_connect_old_profile(self):
  self.ui.set_candidates(PROFILES[:1]);self.ui.folder.set('new-location')
  with patch.object(app.engine,'detect',return_value=[]),patch.object(app.engine,'sync_profile') as transport:
   self.ui.start();transport.assert_not_called()
  self.assertEqual(self.store.writes,[])
 def test_about_has_github_link_and_embedded_licenses(self):
  self.ui.about();windows=[w for w in self.root.winfo_children() if isinstance(w,app.tk.Toplevel)]
  buttons=[w for w in windows[-1].winfo_children()[0].winfo_children() if isinstance(w,app.ttk.Button)]
  with patch.object(app.webbrowser,'open') as opened:
   next(w for w in buttons if 'GitHub' in w.cget('text')).invoke();opened.assert_called_once_with(app.SOURCE_URL)
  self.ui.licenses();self.assertEqual(len([w for w in self.root.winfo_children() if isinstance(w,app.tk.Toplevel)]),2)
 def test_window_size_and_tray_menu(self):
  self.ui.set_candidates(PROFILES);self.root.deiconify();self.root.update()
  self.assertGreaterEqual(int(self.root.geometry().split('x')[1].split('+')[0]),self.ui.panel.winfo_reqheight())
  self.assertEqual(app.tray_labels(),tuple(app.tr(key) for key in ('configure','about','close')))

 def test_erasure_cancel_performs_no_operation(self):
  self.ui.state['selected']=PROFILES[0]
  with patch.object(app.messagebox,'askyesno',return_value=False),patch.object(app.engine,'request_erasure') as request:
   self.ui.erase_shared_data();request.assert_not_called()
  self.assertEqual(self.store.writes,[])
 def test_erasure_requires_confirmation_and_stops_background_loop(self):
  self.ui.state['selected']=PROFILES[0];self.ui.paused.clear()
  with patch.object(app.messagebox,'askyesno',return_value=True),patch.object(app.engine,'request_erasure',return_value={'erasure':'queued'}) as request:
   self.ui.erase_shared_data();self.wait();request.assert_called_once()
  self.assertTrue(self.ui.paused.is_set());self.assertEqual(self.ui.last_status,app.tr('erasure_queued'))

 def test_startup_default_off_and_no_registry_write(self):
  self.assertFalse(self.ui.autostart.get());self.ui.set_candidates(PROFILES[:1])
  with patch.object(app.engine,'sync_profile',return_value={}),patch.object(app.engine,'startup') as startup:
   self.ui.start();self.wait();startup.assert_not_called()
  self.assertFalse(self.store.writes[-1]['startup'])
 def test_startup_opt_in_is_saved_after_success(self):
  self.ui.set_candidates(PROFILES[:1]);self.ui.autostart.set(True)
  with patch.object(app.engine,'sync_profile',return_value={}),patch.object(app.engine,'startup') as startup:
   self.ui.start();self.wait();startup.assert_called_once_with(True)
  self.assertTrue(self.store.writes[-1]['startup'])
 def test_existing_startup_can_be_disabled(self):
  self.ui.state['startup']=True;self.ui.autostart.set(False);self.ui.set_candidates(PROFILES[:1])
  with patch.object(app.engine,'sync_profile',return_value={}),patch.object(app.engine,'startup') as startup:
   self.ui.start();self.wait();startup.assert_called_once_with(False)
  self.assertFalse(self.store.writes[-1]['startup'])
 def test_startup_error_does_not_claim_success(self):
  self.ui.set_candidates(PROFILES[:1]);self.ui.autostart.set(True)
  with patch.object(app.engine,'sync_profile',return_value={}),patch.object(app.engine,'startup',side_effect=PermissionError),patch.object(self.ui,'configure'):
   self.ui.start();self.wait()
  self.assertFalse(self.ui.state['enabled']);self.assertTrue(self.ui.paused.is_set());self.assertIn('[STARTUP]',self.mocks[4].call_args.args[1]);self.assertFalse(self.mocks[3].called)

if __name__=='__main__':unittest.main()
