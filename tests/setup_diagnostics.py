"""Offline regression tests for read-only setup, diagnostic privacy and preflight."""
import sys,tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError,URLError
import ssl
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import engine
class SetupTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent,prefix="integration-setup-");self.root=Path(self.tmp.name);self.addon=self.root/'Interface'/'AddOns'/'DeathAtlas';self.addon.mkdir(parents=True);(self.addon/'DeathAtlas.toc').write_text('fixture')
  self.saved=self.root/'DeathAtlas.lua';self.profile={'saved':str(self.saved),'addon':str(self.addon)};self.write()
  self.wow=patch.object(engine.data,'wow_running',return_value=False);self.wow.start()
 def tearDown(self):self.wow.stop();self.tmp.cleanup()
 def write(self,sharing='true',schema=1):self.saved.write_text('DeathAtlasDB={schema='+str(schema)+',install="fixture-setup",settings={sharing='+sharing+'},records={}}')
 def code(self,expected):
  with self.assertRaises(engine.CheckError) as ctx:engine.local_check(self.profile)
  self.assertEqual(ctx.exception.code,expected)
 def test_local_valid_empty(self):self.assertEqual(engine.local_check(self.profile),({'schema':1,'sharing':True,'records':[]},'fixture-setup'))
 def test_sharing(self):self.write('false');self.code('SHARING_OFF')
 def test_schema(self):self.write(schema=2);self.code('SCHEMA')
 def test_corrupt_preserved(self):
  self.saved.write_text('DeathAtlasDB = execute_secret()');before=self.saved.read_bytes();self.code('SAVE_INVALID');self.assertEqual(self.saved.read_bytes(),before)
 def test_missing_save(self):self.saved.unlink();self.code('SAVE_MISSING')
 def test_missing_addon(self):(self.addon/'DeathAtlas.toc').unlink();self.code('ADDON_MISSING')
 def test_wow_open(self):
  with patch.object(engine.data,'wow_running',return_value=True):self.code('WOW_OPEN')
 def test_oversize(self):
  with patch.object(engine.data,'MAX_BYTES',4):self.code('FILE_TOO_LARGE')
 def test_changing_save(self):
  original=engine.identity
  def changing(path):
   value=original(path)
   with self.saved.open('a') as stream:stream.write(' ')
   return value
  with patch.object(engine,'identity',side_effect=changing):self.code('FILE_CHANGING')
 def test_read_only_health(self):
  before={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()};state={'consent':False,'enabled':False,'profiles':{}};copy=json.dumps(state)
  with patch.object(engine,'api',return_value={'policy':engine.POLICY,'enrollment':True}) as api:
   report=engine.diagnose(self.profile,state);api.assert_called_once_with(engine.DEFAULT_SERVICE,'/v1/health')
  self.assertIn('[LOCAL_OK]',report);self.assertIn('[EMPTY]',report);self.assertIn('[CONSENT]',report);self.assertIn('[SERVICE_OK]',report);self.assertEqual(json.dumps(state),copy)
  self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()});self.assertNotIn(str(self.root),report);self.assertNotIn('fixture-setup',report)
 def test_closed_service(self):
  with patch.object(engine,'api',return_value={'policy':engine.POLICY,'enrollment':False}):self.assertIn('[SERVICE_CLOSED]',engine.diagnose(None,{}))
 def test_policy(self):
  with patch.object(engine,'api',return_value={'policy':'future'}):self.assertIn('[POLICY]',engine.diagnose(None,{}))
 def test_http_safe(self):
  for code in [401,403,404,409,413,429,503,500]:
   message=engine.describe_error(HTTPError('https://example.invalid/secret',code,'private-body',{},None));self.assertIn('[HTTP_'+str(code)+']',message);self.assertNotIn('private-body',message);self.assertNotIn('/secret',message)
 def test_network(self):
  for error,code in [(URLError('private-host'), 'NETWORK'),(URLError(ssl.SSLError('secret')), 'TLS'),(URLError(TimeoutError()),'TIMEOUT'),(ValueError('secret'),'DATA_INVALID'),(RuntimeError('secret'),'UNEXPECTED')]:
   report=engine.describe_error(error);self.assertIn('['+code+']',report);self.assertNotIn('secret',report);self.assertNotIn('private-host',report)
 def test_preflight_blocks_transport(self):
  self.write('false')
  with patch.object(engine,'api') as api,patch.object(engine.Settings,'write') as write:
   with self.assertRaises(engine.CheckError):engine.sync_profile(self.profile,{'consent':True},engine.Settings(self.root/'unused'))
   api.assert_not_called();write.assert_not_called()
if __name__=='__main__':unittest.main(verbosity=2)

