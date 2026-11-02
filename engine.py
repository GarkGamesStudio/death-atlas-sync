"""Death Atlas Sync: no-account transport; no in-game memory/network access."""
import base64,ctypes,hashlib,json,os,re,secrets,subprocess,sys,time,threading
from pathlib import Path
from urllib.parse import urlsplit,urlencode
from urllib.error import HTTPError
from urllib.request import Request,build_opener
import deathatlas as data
DEFAULT_SERVICE='https://garkgames.com/api/deathatlas'
POLICY='2026-11-01'
VERSION='0.4.1'
class SyncError(ValueError):pass

def consented(state):
 return state.get('consent') is True and state.get('consentPolicy')==POLICY

def refresh_slot(now=None):
 """Retry daily editions every 30 minutes while WoW is closed, even without new saves."""
 return int(time.time() if now is None else now)//1800


def endpoint(url):
 p=urlsplit(url)
 if p.username or p.password or p.query or p.fragment or p.scheme not in ('https','http') or not p.hostname:raise SyncError('Dirección de servicio inválida')
 if p.scheme=='http' and p.hostname not in ('127.0.0.1','localhost','::1'):raise SyncError('El servicio remoto requiere HTTPS')
 return url.rstrip('/')

def api(base,route,payload=None,token=None):
 base=endpoint(base);headers={'Accept':'application/json','User-Agent':'DeathAtlasSync/'+VERSION}
 if token:headers['X-DeathAtlas-Key']=token
 if payload is not None:headers['Content-Type']='application/json'
 req=Request(base+route,data=json.dumps(payload).encode() if payload is not None else None,headers=headers)
 with build_opener(data.NoRedirect).open(req,timeout=30) as response:raw=response.read(data.MAX_BYTES+1)
 if len(raw)>data.MAX_BYTES:raise SyncError('Respuesta demasiado grande')
 return json.loads(raw)

class Blob(ctypes.Structure):
 _fields_=[('cbData',ctypes.c_ulong),('pbData',ctypes.POINTER(ctypes.c_ubyte))]
def protect(raw,unprotect=False):
 if os.name!='nt':
  from platform_support import protect as native_protect
  return native_protect(raw,unprotect)
 buffer=ctypes.create_string_buffer(raw);source=Blob(len(raw),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)));dest=Blob()
 function=ctypes.windll.crypt32.CryptUnprotectData if unprotect else ctypes.windll.crypt32.CryptProtectData
 if not function(ctypes.byref(source),None,None,None,None,1,ctypes.byref(dest)):raise SyncError('No se pudieron proteger las credenciales de Windows')
 try:return ctypes.string_at(dest.pbData,dest.cbData)
 finally:ctypes.windll.kernel32.LocalFree(dest.pbData)

class Settings:
 def __init__(self,path):self.path=Path(path);self.lock=threading.RLock()
 def read(self):
  if not self.path.exists():return {'schema':1,'profiles':{},'enabled':False}
  raw=self.path.read_bytes()
  if len(raw)>8*1024*1024:raise SyncError('Configuración demasiado grande')
  value=json.loads(protect(raw,True))
  if value.get('schema')!=1 or not isinstance(value.get('profiles'),dict):raise SyncError('Configuración no compatible; no se reemplazó')
  return value
 def write(self,value):
  with self.lock:
   encoded=protect(json.dumps(value,ensure_ascii=False).encode())
   if len(encoded)>8*1024*1024:raise SyncError('Demasiadas cuentas en la configuración; no se reemplazó el archivo')
   self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
   tmp=self.path.with_suffix('.tmp')
   descriptor=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
   with os.fdopen(descriptor,'wb') as output:output.write(encoded)
   os.replace(tmp,self.path)


from discovery import detect, automatic_roots, discover

def identity(saved):
 raw=Path(saved).read_bytes()
 if len(raw)>data.MAX_BYTES:raise SyncError('Archivo demasiado grande')
 db=data.SavedParser(raw.decode('utf-8-sig')).parse().get('DeathAtlasDB',{})
 install=db.get('install')
 if not isinstance(install,str) or not re.fullmatch('[A-Za-z0-9-]{1,40}',install):raise SyncError('No se encontró una instalación válida')
 return install

class CheckError(SyncError):
 def __init__(self,code,message):self.code=code;super().__init__(message)

def local_check(profile):
 """Read-only preflight, shared by setup and synchronization. Never evaluates Lua."""
 if data.wow_running():raise CheckError('WOW_OPEN','Cierra todos los clientes de WoW para leer un guardado estable.')
 saved=Path(profile['saved'])
 if not (Path(profile['addon'])/'DeathAtlas.toc').is_file():raise CheckError('ADDON_MISSING','No se encuentra DeathAtlas.toc. Instala el addon o vuelve a elegir la carpeta.')
 try:
  before=saved.stat()
  if before.st_size>data.MAX_BYTES:raise CheckError('FILE_TOO_LARGE','El guardado supera el límite seguro. Se conserva sin modificar; requiere revisión.')
  db=data.SavedParser(saved.read_text(encoding='utf-8-sig')).parse().get('DeathAtlasDB')
  if not isinstance(db,dict) or db.get('schema')!=1:raise CheckError('SCHEMA','Guardado de una versión no compatible. Actualiza Sync; no borres tu historial.')
  settings=db.get('settings',{})
  if not isinstance(settings,dict) or settings.get('sharing') is not True:raise CheckError('SHARING_OFF','En WoW abre /da, activa Compartir y cierra el juego para guardar el permiso.')
  payload=data.read_input(saved);install=identity(saved);after=saved.stat()
  if (before.st_mtime_ns,before.st_size)!=(after.st_mtime_ns,after.st_size):raise CheckError('FILE_CHANGING','El guardado está cambiando. Espera a que WoW termine de cerrarse y reintenta.')
  return payload,install
 except CheckError:raise
 except FileNotFoundError:raise CheckError('SAVE_MISSING','No se encuentra el guardado. Entra con Death Atlas activo, cierra WoW y vuelve a detectar la cuenta.') from None
 except PermissionError:raise CheckError('FILE_ACCESS','Windows no permite leer el guardado. Revisa la carpeta y sus permisos.') from None
 except (ValueError,UnicodeError,TypeError,AttributeError):raise CheckError('SAVE_INVALID','El guardado está incompleto o contiene datos no compatibles. Se conserva sin modificar; requiere revisión.') from None

def describe_error(exc):
 from localization import tr
 from urllib.error import URLError
 import socket,ssl
 code='UNEXPECTED';key='error_unexpected'
 if isinstance(exc,CheckError):
  code=exc.code
  key={'ERASURE':'erasure_blocked','NO_KEY':'erasure_no_key','WOW_OPEN':'waiting','ADDON_MISSING':'error_file','FILE_TOO_LARGE':'error_size','SCHEMA':'error_invalid','SHARING_OFF':'error_sharing','FILE_CHANGING':'error_changed','SAVE_MISSING':'error_file','FILE_ACCESS':'error_access','SAVE_INVALID':'error_invalid','TRAY':'tray_failed','STARTUP':'startup_failed'}.get(code,'error_invalid')
 elif isinstance(exc,HTTPError):
  code='HTTP_'+str(exc.code);key={401:'error_auth',403:'error_auth',404:'error_noapi',409:'error_auth',413:'error_size',429:'error_rate',503:'error_service'}.get(exc.code,'error_service')
 else:
  reason=exc.reason if isinstance(exc,URLError) else exc
  if isinstance(reason,ssl.SSLError):code,key='TLS','error_tls'
  elif isinstance(reason,(TimeoutError,socket.timeout)):code,key='TIMEOUT','error_timeout'
  elif isinstance(exc,URLError):code,key='NETWORK','error_network'
  elif isinstance(exc,PermissionError):code,key='FILE_ACCESS','error_access'
  elif isinstance(exc,FileNotFoundError):code,key='FILE_MISSING','error_file'
  elif isinstance(exc,SyncError):
   code='SYNC'
   key={
    'Esperando a que cierres WoW':'waiting','Cierra WoW antes de desconectar':'waiting',
    'Sincronización pausada':'error_paused','WoW se abrió o la sincronización se pausó; caché pendiente':'error_paused',
    'Revisa la política de datos y guarda de nuevo el permiso de compartir':'error_policy','La política cambió; actualiza Sync y revisa el consentimiento':'error_policy',
    'La conexión fue revocada; contacta al operador para recuperarla':'error_revoked',
    'La edición cambió durante la descarga; se conserva la caché anterior y se reintentará':'error_mixed',
    'Inicio automático disponible en Windows':'error_runtime','El inicio automático requiere la aplicación EXE empaquetada':'error_runtime',
    'Las credenciales requieren Windows DPAPI':'error_runtime','No se pudieron proteger las credenciales de Windows':'error_saveconfig',
    'Configuración demasiado grande':'error_saveconfig','Configuración no compatible; no se reemplazó':'error_saveconfig','Demasiadas cuentas en la configuración; no se reemplazó el archivo':'error_saveconfig',
    'Respuesta demasiado grande':'error_size','Archivo demasiado grande':'error_size',
   }.get(str(exc),'error_invalid')
  elif isinstance(exc,ValueError):code,key='DATA_INVALID','error_invalid'
 return '['+code+'] '+tr(key)

def diagnose(profile,state,service=DEFAULT_SERVICE):
 """Explicit setup check: local read plus public health GET only. No registration/upload/write."""
 lines=['Death Atlas Sync '+VERSION,'Comprobación sin registrar, subir datos ni modificar archivos.']
 if profile:
  try:
   payload,_=local_check(profile);lines.append('[LOCAL_OK] Guardado compatible: '+str(len(payload['records']))+' muertes listas.')
   if not payload['records']:lines.append('[EMPTY] El historial está vacío. No se podrá elegir el cliente de la caché hasta registrar una muerte.')
  except Exception as exc:lines.append(describe_error(exc))
 else:lines.append('[SETUP] Elige la carpeta de WoW y una cuenta detectada. Si no aparece, entra con el addon activo y cierra WoW.')
 lines.append('[CONSENT_OK] Permiso de Sync guardado.' if consented(state) else '[CONSENT] Falta guardar el permiso de Sync para empezar a enviar.')
 lines.append('[PAUSED] Envíos pausados.' if not state.get('enabled') else '[ENABLED] Sincronización activada.')
 try:
  info=api(service,'/v1/health')
  if not isinstance(info,dict) or info.get('policy')!=POLICY:lines.append('[POLICY] Política no compatible. Actualiza Sync antes de conectar.')
  elif info.get('enrollment') is not True:lines.append('[SERVICE_CLOSED] API accesible; nuevas conexiones cerradas. Una conexión ya registrada puede seguir funcionando.')
  else:lines.append('[SERVICE_OK] API accesible y altas abiertas. Esta prueba no verifica una carga real.')
 except Exception as exc:lines.append(describe_error(exc))
 return '\n'.join(lines)


def sync_profile(profile,state,store,service=DEFAULT_SERVICE,stopped=lambda:False):
 if stopped():raise SyncError('Sincronización pausada')
 if data.wow_running():raise SyncError('Esperando a que cierres WoW')
 payload,install=local_check(profile)
 if not consented(state):raise SyncError('Revisa la política de datos y guarda de nuevo el permiso de compartir')
 service=endpoint(service);key=service+'|'+install
 credentials=state.setdefault('profiles',{}).get(key)
 if credentials and credentials.get('erasureRequested'):raise CheckError('ERASURE','Erasure requested')
 if credentials and credentials.get('revoked'):raise SyncError('La conexión fue revocada; contacta al operador para recuperarla')
 if not credentials:
  credentials={'token':secrets.token_hex(32),'policy':POLICY,'uploaded':{},'registered':False}
  state['profiles'][key]=credentials;store.write(state) # Persist before registration, so a lost response can be retried with the same key.
 info=api(service,'/v1/health')
 if info.get('policy')!=POLICY:raise SyncError('La política cambió; actualiza Sync y revisa el consentimiento')
 if not credentials.get('registered') or credentials.get('policy')!=POLICY:
  api(service,'/v1/register',{'install':install,'secret':credentials['token'],'consent':True,'policy':POLICY})
  credentials['registered']=True;credentials['policy']=POLICY;store.write(state)
 token=credentials['token'];batch=min(25,int(info.get('maxBatch',25)))
 if batch<1:raise SyncError('Límite del servidor inválido')
 uploaded=credentials.setdefault('uploaded',{});pending=[]
 for record in payload['records']:
  digest=hashlib.sha256(json.dumps(record,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
  if uploaded.get(record['id'])!=digest:pending.append((record,digest))
 sent=0
 for start in range(0,len(pending),batch):
  if stopped():raise SyncError('Sincronización pausada')
  group=pending[start:start+batch]
  api(service,'/v1/upload',{'schema':1,'sharing':True,'records':[r for r,_ in group]},token)
  for r,digest in group:uploaded[r['id']]=digest
  sent+=len(group);store.write(state)
 if stopped():raise SyncError('Sincronización pausada')
 # Prefer a client-wide cache so region/realm filters can browse beyond the player's own realm.
 scopes={(r['client'],r['region'],r['realm']) for r in payload['records']}
 clients=sorted({r['client'] for r in payload['records']});snapshots=[];limited=False
 try:
  for client in clients:snapshots.append(data.valid_snapshot(api(service,'/v1/snapshot?'+urlencode({'client':client,'days':30,'precision':'exact'}))))
 except HTTPError as exc:
  if exc.code!=413:raise
  limited=True;snapshots=[]
  for client,region,realm in sorted(scopes):
   snapshots.append(data.valid_snapshot(api(service,'/v1/snapshot?'+urlencode({'client':client,'region':region,'realm':realm,'days':30,'precision':'exact'}))))
 credentials['coverage']='own-realms-fallback' if limited else 'all-regions-for-client'
 if snapshots:
  if len({s['schema'] for s in snapshots})!=1:raise SyncError('Incompatible snapshot formats')
  if len({s['generated'] for s in snapshots})!=1:raise SyncError('La edición cambió durante la descarga; se conserva la caché anterior y se reintentará')
  snapshot={'schema':snapshots[0]['schema'],'grid':snapshots[0]['grid'],'generated':min(s['generated'] for s in snapshots),'cells':[c for s in snapshots for c in s['cells']]}
  data.valid_snapshot(snapshot)
  if stopped() or data.wow_running():raise SyncError('WoW se abrió o la sincronización se pausó; caché pendiente')
  output=Path(profile['addon'])/'CommunityData.lua'
  if output.exists():data.atomic_write(output.with_suffix('.lua.bak'),output.read_text(encoding='utf-8'))
  data.atomic_write(output,data.lua_snapshot(snapshot))
 # Keep hashes only for the current bounded local history.
 ids={r['id'] for r in payload['records']};credentials['uploaded']={k:v for k,v in uploaded.items() if k in ids}
 credentials['lastSync']=int(time.time());store.write(state)
 return {'sent':sent,'cached':bool(snapshots),'limited':limited,'lastSync':credentials['lastSync']}

def revoke(profile,state,store,service=DEFAULT_SERVICE):
 if data.wow_running():raise SyncError('Cierra WoW antes de desconectar')
 key=endpoint(service)+'|'+identity(profile['saved']);credentials=state.get('profiles',{}).get(key)
 if credentials and credentials.get('registered') and not credentials.get('revoked'):
  api(service,'/v1/revoke',{},credentials['token']);credentials['revoked']=True;store.write(state)
 state['enabled']=False;state['consent']=False;store.write(state)

def request_erasure(profile,state,store,service=DEFAULT_SERVICE):
 """Explicit user action; retains the DPAPI key for idempotent retry/status on a revoked device."""
 key=endpoint(service)+'|'+identity(profile['saved'])
 credentials=state.get('profiles',{}).get(key)
 if not credentials or not credentials.get('registered') or not credentials.get('token'):
  raise CheckError('NO_KEY','No registered key')
 # Stop future uploads even if the request times out after the server accepts it.
 state['enabled']=False;state['consent']=False;credentials['erasureRequested']=True;store.write(state)
 result=api(service,'/v1/erase',{'confirm':True},credentials['token'])
 if not isinstance(result,dict) or result.get('erasure') not in ('queued','completed'):
  raise SyncError('Invalid erasure response')
 credentials['erasureStatus']=result['erasure'];credentials['revoked']=True;store.write(state)
 return result

def startup(enabled,exe=None):
 if os.name!='nt':raise SyncError('Inicio automático disponible en Windows')
 import winreg
 command=subprocess.list2cmdline([str(exe or sys.executable),'--background'])
 if enabled and not getattr(sys,'frozen',False):raise SyncError('El inicio automático requiere la aplicación EXE empaquetada')
 with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
  if enabled:winreg.SetValueEx(key,'DeathAtlasSync',0,winreg.REG_SZ,command)
  else:
   try:winreg.DeleteValue(key,'DeathAtlasSync')
   except FileNotFoundError:pass
