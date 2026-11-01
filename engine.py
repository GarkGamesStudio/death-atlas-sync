"""Death Atlas Sync: no-account transport; no in-game memory/network access."""
import base64,ctypes,hashlib,json,os,re,secrets,subprocess,sys,time,threading
from pathlib import Path
from urllib.parse import urlsplit,urlencode
from urllib.error import HTTPError
from urllib.request import Request,build_opener
import deathatlas as data
DEFAULT_SERVICE='https://garkgames.com/api/deathatlas'
POLICY='2026-10-31'
VERSION='0.3.8'
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
 if os.name!='nt':raise SyncError('Las credenciales requieren Windows DPAPI')
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
   self.path.parent.mkdir(parents=True,exist_ok=True)
   tmp=self.path.with_suffix('.tmp');tmp.write_bytes(encoded);os.replace(tmp,self.path)


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
 """Safe diagnostics: never include response bodies, credentials or local paths."""
 from urllib.error import URLError
 import socket,ssl
 if isinstance(exc,CheckError):return '['+exc.code+'] '+str(exc)
 if isinstance(exc,HTTPError):
  messages={401:'Conexión no autorizada o revocada. Requiere revisión del operador.',403:'El servidor rechazó la instalación o sus permisos.',404:'La API no está disponible en esta dirección. Comprueba que el servicio ya esté publicado.',409:'Conflicto de instalación o registro. No borres la configuración; requiere revisión.',413:'La consulta o el envío supera el límite del servicio.',429:'Límite temporal. Sync volverá a intentarlo automáticamente.',503:'Servicio no disponible o altas cerradas. Reintenta cuando Gark Games lo active.'}
  return '[HTTP_'+str(exc.code)+'] '+messages.get(exc.code,'El servicio rechazó la solicitud. Se reintentará sin borrar el historial.')
 reason=exc.reason if isinstance(exc,URLError) else exc
 if isinstance(reason,ssl.SSLError):return '[TLS] No se pudo verificar la conexión segura. Revisa la fecha de Windows y la conexión; no desactives HTTPS.'
 if isinstance(reason,(TimeoutError,socket.timeout)):return '[TIMEOUT] El servidor tardó demasiado. Se reintentará automáticamente.'
 if isinstance(exc,URLError):return '[NETWORK] No se pudo conectar. Revisa Internet; también puede estar inactivo el servicio.'
 if isinstance(exc,PermissionError):return '[FILE_ACCESS] No se pudo acceder a un archivo. Revisa los permisos de la carpeta elegida.'
 if isinstance(exc,FileNotFoundError):return '[FILE_MISSING] Falta un archivo. Vuelve a detectar la instalación y la cuenta.'
 if isinstance(exc,SyncError):return '[SYNC] '+str(exc)
 if isinstance(exc,ValueError):return '[DATA_INVALID] La respuesta o los datos no son compatibles. Actualiza Sync o solicita revisión; se conserva el guardado.'
 return '[UNEXPECTED] No se pudo completar la operación. Reintenta; si persiste, comunica este código y la versión de Sync.'

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
  api(service,'/v1/revoke',{},credentials['token']);credentials['revoked']=True;credentials['token']='';store.write(state)
 state['enabled']=False;state['consent']=False;store.write(state)

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
