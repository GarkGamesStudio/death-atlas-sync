"""Bounded, read-only installation discovery. Never scans entire drives or reads game saves."""
import ctypes
import json
import os
import sys
from pathlib import Path

CLIENTS=('_forever_','_retail_','_camelot_')
NAMES=('World of Warcraft','WoW','WoW Forever','Forever')

def unique(paths):
 result=[];seen=set()
 for raw in paths:
  if not raw:continue
  path=Path(os.path.expandvars(str(raw).strip('"')))
  key=os.path.normcase(os.path.abspath(path))
  if key not in seen:seen.add(key);result.append(path)
 return result

def fixed_drives():
 if os.name!='nt':return []
 mask=ctypes.windll.kernel32.GetLogicalDrives()
 return [Path(chr(65+i)+':/') for i in range(26) if mask & (1<<i) and ctypes.windll.kernel32.GetDriveTypeW(chr(65+i)+':\\')==3]

def registry_roots():
 if os.name!='nt':return []
 import winreg
 result=[]
 for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
  for view in (winreg.KEY_WOW64_32KEY,winreg.KEY_WOW64_64KEY):
   for product in ('World of Warcraft','World of Warcraft Forever','WoW Forever'):
    try:
     with winreg.OpenKey(hive,'SOFTWARE\\Blizzard Entertainment\\'+product,0,winreg.KEY_READ|view) as key:
      for name in ('InstallPath','InstallLocation'):
       try:result.append(winreg.QueryValueEx(key,name)[0])
       except OSError:pass
    except OSError:pass
   try:
    with winreg.OpenKey(hive,r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',0,winreg.KEY_READ|view) as parent:
     for i in range(min(winreg.QueryInfoKey(parent)[0],4096)):
      try:
       with winreg.OpenKey(parent,winreg.EnumKey(parent,i)) as key:
        name=winreg.QueryValueEx(key,'DisplayName')[0].lower()
        if 'world of warcraft' in name or 'wow forever' in name:
         result.append(winreg.QueryValueEx(key,'InstallLocation')[0])
      except (OSError,AttributeError):pass
   except OSError:pass
 return [v for v in result if isinstance(v,str) and v]

def battle_net_roots():
 """Only installation keys from local launcher JSON; no credentials are collected."""
 result=[]
 for env in ('APPDATA','LOCALAPPDATA','PROGRAMDATA'):
  base=os.environ.get(env)
  if not base:continue
  for name in ('Battle.net.config','Battle.net.config.json'):
   path=Path(base)/'Battle.net'/name
   try:
    if path.stat().st_size>2*1024*1024:continue
    tree=json.loads(path.read_text(encoding='utf-8-sig'))
   except (OSError,ValueError,UnicodeError):continue
   def visit(value,depth=0):
    if depth>10:return
    if isinstance(value,dict):
     for key,item in value.items():
      if key.lower() in ('installpath','installlocation','lastinstalldir','lastinstallpath') and isinstance(item,str):result.append(item)
      elif isinstance(item,(dict,list)):visit(item,depth+1)
    elif isinstance(value,list):
     for item in value[:256]:visit(item,depth+1)
   visit(tree)
 return result

def automatic_roots(preferred=()):
 roots=list(preferred)+registry_roots()+battle_net_roots()
 for key in ('ProgramFiles(x86)','ProgramFiles'):
  base=os.environ.get(key)
  if base:
   roots.extend(Path(base)/name for name in NAMES)
 for drive in fixed_drives():
  for container in ('','Games','Blizzard','Program Files','Program Files (x86)'):
   roots.extend(drive/container/name for name in NAMES)
 # Portable installations can keep Sync beside the game, including local test labs.
 origin=Path(sys.executable if getattr(sys,'frozen',False) else __file__).resolve().parent
 for parent in [origin]+list(origin.parents)[:4]:
  roots.append(parent)
  roots.extend(parent/name for name in NAMES+('client',))
 return unique(roots)

def client_roots(root):
 root=Path(root)
 if root.suffix.lower()=='.exe':root=root.parent
 roots=[root]+[root/name for name in CLIENTS]
 if root.name in CLIENTS:roots.extend(root.parent/name for name in CLIENTS)
 return unique(roots)

def detect(root):
 result=[]
 for client in client_roots(root):
  addon=client/'Interface'/'AddOns'/'DeathAtlas'
  try:
   if not (addon/'DeathAtlas.toc').is_file():continue
   accounts=client/'WTF'/'Account'
   if not accounts.is_dir():continue
   for account in sorted(accounts.iterdir()):
    saved=account/'SavedVariables'/'DeathAtlas.lua'
    if saved.is_file():result.append({'saved':str(saved.resolve()),'addon':str(addon.resolve())})
  except OSError:continue
 return result

def discover(preferred=()):
 profiles=[];seen=set()
 for root in automatic_roots(preferred):
  for profile in detect(root):
   key=os.path.normcase(profile['saved'])
   if key not in seen:seen.add(key);profiles.append(profile)
 return profiles
