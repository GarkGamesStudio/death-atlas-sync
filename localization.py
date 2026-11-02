"""WoW locale catalogs selected from Windows display-language preferences."""
import ctypes,json,locale,os,sys,re,subprocess
from pathlib import Path

LOCALES=('enUS','esES','esMX','deDE','frFR','itIT','ptBR','ruRU','koKR','zhCN','zhTW')
BASE=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/'locales'

def normalize(name):
 value=str(name).replace('_','-').lower()
 if value in ('engb','ptpt'):return 'enUS' if value=='engb' else 'ptBR'
 if value in {code.lower():code for code in LOCALES}:return {code.lower():code for code in LOCALES}[value]
 if value.startswith('zh'):
  if 'hans' in value.split('-')[1:]:return 'zhCN'
  return 'zhTW' if any(x in value.split('-')[1:] for x in ('hant','tw','hk','mo')) else 'zhCN'
 prefix=value.split('-')[0]
 if prefix=='es':return 'esES' if value in ('es','es-es') else 'esMX'
 return {'en':'enUS','de':'deDE','fr':'frFR','it':'itIT','pt':'ptBR','ru':'ruRU','ko':'koKR'}.get(prefix)

def windows_languages():
 result=[]
 if os.name=='nt':
  try:
   from ctypes import wintypes
   fn=ctypes.windll.kernel32.GetUserPreferredUILanguages
   fn.argtypes=(wintypes.DWORD,ctypes.POINTER(wintypes.ULONG),wintypes.LPWSTR,ctypes.POINTER(wintypes.ULONG));fn.restype=wintypes.BOOL
   count=wintypes.ULONG();size=wintypes.ULONG()
   if fn(8,ctypes.byref(count),None,ctypes.byref(size)) and 0<size.value<=32768:
    buffer=ctypes.create_unicode_buffer(size.value)
    if fn(8,ctypes.byref(count),buffer,ctypes.byref(size)):result.extend(x for x in buffer[:size.value].split('\0') if x)
  except (OSError,AttributeError,ValueError):pass
  if not result:
   try:
    tag=locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage())
    if tag:result.append(tag)
   except (OSError,AttributeError):pass
 if not result:
  if sys.platform=='darwin':
   try:
    output=subprocess.run(['defaults','read','-g','AppleLanguages'],capture_output=True,text=True,timeout=3,check=True).stdout
    result.extend(re.findall(r'\b[a-z]{2}(?:-[A-Za-z0-9]+)*\b',output))
   except (OSError,subprocess.SubprocessError):pass
  elif sys.platform.startswith('linux'):
   result.extend(x for x in os.environ.get('LANGUAGE','').split(':') if x)
   result.extend(os.environ.get(k,'').split('.')[0] for k in ('LC_ALL','LC_MESSAGES','LANG') if os.environ.get(k))
 if not result:
  try:result.append(locale.getlocale()[0] or 'en-US')
  except (ValueError,TypeError):pass
 return result

def select_language(preferred):
 return next((code for item in preferred if (code:=normalize(item))), 'enUS')

def read_catalog(code):return json.loads((BASE/(code+'.json')).read_text(encoding='utf-8'))
ENGLISH=read_catalog('enUS')
LANGUAGE=select_language(windows_languages())
CATALOG=read_catalog(LANGUAGE)

def set_language(code):
 """Test/source override. Normal application always follows Windows preferences."""
 global LANGUAGE,CATALOG
 LANGUAGE=code if code in LOCALES else 'enUS';CATALOG=read_catalog(LANGUAGE)

def tr(key,**values):return CATALOG.get(key,ENGLISH[key]).format(**values)
def font_family():
 if sys.platform=='darwin':return 'Helvetica'
 if sys.platform.startswith('linux'):return 'DejaVu Sans'
 return {'koKR':'Malgun Gothic','zhCN':'Microsoft YaHei UI','zhTW':'Microsoft JhengHei UI'}.get(LANGUAGE,'Segoe UI')
