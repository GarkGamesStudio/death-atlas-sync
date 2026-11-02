"""Public version metadata only. Never downloads or executes an update."""
import json, platform, re, sys, time
from urllib.request import Request, build_opener
import deathatlas as data

MANIFEST='https://garkgames.com/death-atlas/sync-updates.json'
DOWNLOADS='https://garkgames.com/death-atlas/about/#downloads'

def version(value):
 if not isinstance(value,str) or not re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,4}',value):raise ValueError('Invalid version')
 return tuple(map(int,value.split('.')))

def platform_key():
 if sys.platform=='win32':return 'windows-x64'
 if sys.platform=='darwin':return 'macos-arm64' if platform.machine().lower() in ('arm64','aarch64') else 'macos-x64'
 return 'linux-x64' if platform.machine().lower() in ('amd64','x86_64') else 'unsupported'

def available(manifest,current,key=None):
 if not isinstance(manifest,dict) or manifest.get('schema')!=1:raise ValueError('Invalid manifest')
 item=manifest['platforms'].get(key or platform_key())
 if item is None:return None
 latest=item['version'];version(latest)
 # The only action offered is our fixed download page, never an arbitrary remote URL.
 return {'version':latest,'url':DOWNLOADS} if version(latest)>version(current) else None

def check(state,current,now=None,fetch=None):
 """At most one attempt per 24 hours, including failures; synchronization stays independent."""
 now=int(time.time() if now is None else now)
 previous=state.get('updates',{})
 if previous.get('available') and version(previous['available']['version'])<=version(current):
  previous['available']=None
  state['updates']=previous
  return None,True
 if 0<=now-previous.get('checked',0)<86400:return previous.get('available'),False
 status={'checked':now,'available':previous.get('available'),'notified':previous.get('notified')}
 try:
  if fetch is None:
   request=Request(MANIFEST,headers={'Accept':'application/json','User-Agent':'DeathAtlasSync/'+current})
   with build_opener(data.NoRedirect,*data.https_handlers()).open(request,timeout=10) as response:raw=response.read(16385)
   if len(raw)>16384:raise ValueError('Manifest too large')
   manifest=json.loads(raw)
  else:manifest=fetch()
  status['available']=available(manifest,current)
 except Exception:
  pass # An update service outage must never interrupt history/map synchronization.
 state['updates']=status
 return status['available'],True
