"""Synthetic credentials only. No real config, network or game files."""
import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import engine
class Store:
 def __init__(self):self.writes=[]
 def write(self,state):self.writes.append(copy.deepcopy(state))
class Erasure(unittest.TestCase):
 def setUp(self):
  self.key=engine.DEFAULT_SERVICE+'|fixture';self.cred={'registered':True,'token':'synthetic','policy':engine.POLICY}
  self.state={'profiles':{self.key:self.cred},'consent':True,'consentPolicy':engine.POLICY,'enabled':True};self.store=Store();self.profile={'saved':'fixture','addon':'fixture'}
 def test_request_pauses_before_network_retains_key_and_is_retryable(self):
  def api(base,route,payload,token):
   self.assertFalse(self.state['enabled']);self.assertFalse(self.state['consent']);self.assertTrue(self.cred['erasureRequested']);self.assertEqual(route,'/v1/erase');self.assertEqual(payload,{'confirm':True});self.assertEqual(token,'synthetic');return {'erasure':'queued'}
  with patch.object(engine,'identity',return_value='fixture'),patch.object(engine,'api',side_effect=api):
   for _ in range(2):self.assertEqual(engine.request_erasure(self.profile,self.state,self.store)['erasure'],'queued')
  self.assertTrue(self.cred['revoked']);self.assertEqual(self.cred['token'],'synthetic')
 def test_timeout_keeps_uploads_stopped_and_future_sync_blocked(self):
  with patch.object(engine,'identity',return_value='fixture'),patch.object(engine,'api',side_effect=TimeoutError):
   with self.assertRaises(TimeoutError):engine.request_erasure(self.profile,self.state,self.store)
  self.state.update(consent=True,consentPolicy=engine.POLICY)
  with patch.object(engine.data,'wow_running',return_value=False),patch.object(engine,'local_check',return_value=({'records':[]},'fixture')),patch.object(engine,'api') as api:
   with self.assertRaises(engine.CheckError) as exc:engine.sync_profile(self.profile,self.state,self.store)
   self.assertEqual(exc.exception.code,'ERASURE');api.assert_not_called()
 def test_unknown_key_never_registers_or_creates_one(self):
  self.state['profiles']={}
  with patch.object(engine,'identity',return_value='fixture'),patch.object(engine,'api') as api:
   with self.assertRaises(engine.CheckError) as exc:engine.request_erasure(self.profile,self.state,self.store)
   self.assertEqual(exc.exception.code,'NO_KEY');api.assert_not_called()
  self.assertEqual(self.store.writes,[])
 def test_other_profile_not_deleted(self):
  self.state['profiles']['other']={'token':'other-synthetic'}
  with patch.object(engine,'identity',return_value='fixture'),patch.object(engine,'api',return_value={'erasure':'completed'}):engine.request_erasure(self.profile,self.state,self.store)
  self.assertEqual(self.state['profiles']['other'],{'token':'other-synthetic'})
if __name__=='__main__':unittest.main()
