"""Offline policy tests; fixtures only, no real profile or network."""
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import engine
checks=0
def check(value):
 global checks
 assert value
 checks+=1
class Store:
 def write(self,state):pass
payload={'schema':1,'sharing':True,'records':[{'id':'test-1','client':'forever','region':3,'realm':'fixture'}]}
profile={'saved':'fixture','addon':'fixture'}
check(not engine.consented({'consent':True}))
check(not engine.consented({'consent':True,'consentPolicy':'2026-10-29'}))
check(engine.consented({'consent':True,'consentPolicy':engine.POLICY}))
check(not engine.consented({'consent':False,'consentPolicy':engine.POLICY}))
check(engine.refresh_slot(1793426399)!=engine.refresh_slot(1793426400))
check(engine.refresh_slot(1793426400)==engine.refresh_slot(1793426401))
with patch.object(engine.data,'wow_running',return_value=False),patch.object(engine,'local_check',return_value=(payload,'test')):
 with patch.object(engine,'api') as api:
  try:engine.sync_profile(profile,{'consent':True},Store())
  except engine.SyncError:check(True)
  else:raise AssertionError('Old consent must stop before network')
  check(not api.called)
 state={'consent':True,'consentPolicy':engine.POLICY,'profiles':{engine.DEFAULT_SERVICE+'|test':{'registered':True,'policy':'2026-10-29','token':'fixture','uploaded':{}}}}
 calls=[]
 def api(base,route,payload=None,token=None):
  calls.append((route,payload))
  if route=='/v1/health':return {'policy':engine.POLICY,'maxBatch':25}
  if route=='/v1/register':return {'registered':True}
  if route=='/v1/upload':return {'added':1}
  raise engine.SyncError('fixture stop before cache write')
 with patch.object(engine,'api',side_effect=api):
  try:engine.sync_profile(profile,state,Store())
  except engine.SyncError:pass
 check(calls[1][0]=='/v1/register')
 check(calls[1][1]['policy']==engine.POLICY)
 check(state['profiles'][engine.DEFAULT_SERVICE+'|test']['policy']==engine.POLICY)
 rows=[*payload['records'],{'id':'test-2','client':'retail','region':3,'realm':'fixture'}]
 counter=[0]
 def snapshots(base,route,payload=None,token=None):
  if route=='/v1/health':return {'policy':engine.POLICY,'maxBatch':25}
  if route=='/v1/register':return {'registered':True}
  if route=='/v1/upload':return {'added':1}
  counter[0]+=1
  return {'schema':5,'grid':0,'generated':1793426400+counter[0]*86400,'cells':[]}
 with patch.object(engine,'local_check',return_value=({'records':rows},'test')),patch.object(engine,'api',side_effect=snapshots),patch.object(engine.data,'valid_snapshot',side_effect=lambda x:x),patch.object(engine.data,'atomic_write') as write:
  try:engine.sync_profile(profile,{'consent':True,'consentPolicy':engine.POLICY,'profiles':{}},Store())
  except engine.SyncError as exc:check('edición' in str(exc))
  else:raise AssertionError('Mixed editions accepted')
  check(not write.called)
print('PASS',checks,'policy, refresh and mixed-edition checks')
