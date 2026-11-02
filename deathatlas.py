"""Death Atlas: opt-in export, SQLite daily aggregation, HTTP API and snapshot bridge.
Python 3.10+, standard library only. Never executes SavedVariables or remote Lua.
"""
import argparse
import csv
import hashlib
import hmac
import io
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import closing
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

LIMIT=5000
MAX_BYTES=8*1024*1024
FIELDS='id t client region realm map x y level class faction cause evidence spell environment context'.split()
OPTIONAL={'instance':0,'instanceName':''}
CAUSES={'unknown','pvp','pve','environment'}
EVIDENCE={'unknown','lethal','last_damage','death_recap','manual'}
CONTEXTS={'outdoor','dungeon','raid','battleground','arena','scenario','unknown'}

def context(raw):
    return {'none':'outdoor','party':'dungeon','raid':'raid','pvp':'battleground',
            'arena':'arena','scenario':'scenario'}.get(raw,'unknown')

def integer(v,lo,hi):
    return type(v) is int and lo<=v<=hi

def number(v,lo,hi):
    return type(v) in (int,float) and math.isfinite(v) and lo<=v<=hi

def text(v,n):
    return isinstance(v,str) and len(v.encode('utf-8'))<=n and not any(ord(c)<32 or ord(c)==127 for c in v)

def record(raw):
    if not isinstance(raw,dict) or set(raw)-set(FIELDS)-set(OPTIONAL) or not set(FIELDS)<=set(raw):
        raise ValueError('Unexpected record fields')
    r=dict(OPTIONAL,**raw)
    checks=[text(r['id'],100) and re.fullmatch(r'[A-Za-z0-9-]+',r['id']),
       integer(r['t'],1,4102444800), r['client'] in ('retail','forever'),integer(r['region'],0,10),
       text(r['realm'],100),integer(r['map'],0,100000),number(r['x'],0,1),number(r['y'],0,1),
       integer(r['level'],0,200),text(r['class'],20),text(r['faction'],20),
       r['cause'] in CAUSES,r['evidence'] in EVIDENCE,integer(r['spell'],0,10000000),
       integer(r['instance'],0,100000),text(r['instanceName'],150),text(r['environment'],30),text(r['context'],30)]
    if not all(checks) or (r['cause']=='unknown')!=(r['evidence']=='unknown'):
        raise ValueError('Invalid death record')
    if r['map']==0 and (r['x']!=0 or r['y']!=0):
        raise ValueError('Unlocated record must have zero coordinates')
    return r

def payload(data):
    if not isinstance(data,dict) or data.get('schema')!=1 or data.get('sharing') is not True:
        raise ValueError('Sharing permission is required; schema must be 1')
    rows=data.get('records')
    if not isinstance(rows,list) or len(rows)>LIMIT:
        raise ValueError('Too many records')
    result=[record(r) for r in rows]
    if len({r['id'] for r in result})!=len(result):
        raise ValueError('Duplicate IDs in upload')
    return {'schema':1,'sharing':True,'records':result}

class SavedParser:
    """Parse a small data-only Lua subset, not Lua expressions or executable code."""
    def __init__(self,s):
        self.s=s; self.i=0; self.nodes=0
    def space(self):
        while self.i<len(self.s):
            if self.s[self.i].isspace(): self.i+=1
            elif self.s.startswith('--',self.i):
                end=self.s.find('\n',self.i)
                self.i=len(self.s) if end<0 else end+1
            else: break
    def literal(self,s):
        self.space()
        if not self.s.startswith(s,self.i): raise ValueError('Unsupported SavedVariables syntax')
        self.i+=len(s)
    def string(self):
        quote=self.s[self.i]; self.i+=1; out=bytearray()
        while self.i<len(self.s):
            c=self.s[self.i]; self.i+=1
            if c==quote: return out.decode('utf-8')
            if c!='\\': out.extend(c.encode('utf-8')); continue
            if self.i>=len(self.s): raise ValueError('Incomplete string')
            c=self.s[self.i]; self.i+=1
            if c.isdigit():
                digits=c
                while len(digits)<3 and self.i<len(self.s) and self.s[self.i].isdigit():
                    digits+=self.s[self.i]; self.i+=1
                if int(digits)>255: raise ValueError('Bad escape')
                out.append(int(digits))
            elif c in {'n','r','t','a','b','f','v','\\','"',"'"}:
                out.extend({'n':'\n','r':'\r','t':'\t','a':'\a','b':'\b','f':'\f','v':'\v'}.get(c,c).encode('utf-8'))
            elif c=='\n': out.extend(b'\n')
            else: raise ValueError('Unsupported string escape')
        raise ValueError('Unterminated string')
    def value(self,depth=0):
        self.space(); self.nodes+=1
        if depth>12 or self.nodes>450000: raise ValueError('SavedVariables limits exceeded')
        if self.i>=len(self.s): raise ValueError('Incomplete value')
        c=self.s[self.i]
        if c in '\"\'': return self.string()
        if c=='{':
            self.i+=1; result={}; index=1
            while True:
                self.space()
                if self.s.startswith('}',self.i): self.i+=1; return result
                if self.s.startswith('[',self.i):
                    self.i+=1; key=self.value(depth+1); self.literal(']'); self.literal('=')
                else:
                    m=re.match(r'([A-Za-z_][A-Za-z_0-9]*)\s*=',self.s[self.i:])
                    if m: key=m[1]; self.i+=m.end()
                    else: key=index; index+=1
                if type(key) not in (int,str) or key in result: raise ValueError('Invalid or duplicate key')
                result[key]=self.value(depth+1)
                self.space()
                if self.i<len(self.s) and self.s[self.i] in ',;': self.i+=1
                elif not self.s.startswith('}',self.i): raise ValueError('Expected separator')
        m=re.match(r'-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?',self.s[self.i:])
        if m:
            self.i+=m.end(); v=float(m[0])
            if not math.isfinite(v): raise ValueError('Invalid number')
            return int(v) if v.is_integer() else v
        for token,value in [('true',True),('false',False),('nil',None)]:
            if self.s.startswith(token,self.i): self.i+=len(token); return value
        raise ValueError('Executable or unsupported Lua is not accepted')
    def parse(self):
        result={}
        while True:
            self.space()
            if self.i==len(self.s): return result
            m=re.match(r'(DeathAtlas(?:DB|Backup|Recovery))\s*=',self.s[self.i:])
            if not m or m[1] in result: raise ValueError('Unexpected SavedVariables assignment')
            self.i+=m.end(); result[m[1]]=self.value()

def read_input(path):
    data=Path(path).read_bytes()
    if len(data)>MAX_BYTES: raise ValueError('Input file too large')
    content=data.decode('utf-8-sig')
    if content.lstrip().startswith('{'):
        return payload(json.loads(content))
    if content.startswith('DEATHATLAS\t1\n') or content.startswith('DEATHATLAS\t1\r\n'):
        reader=csv.DictReader(io.StringIO(content.split('\n',1)[1]),delimiter='\t')
        if reader.fieldnames not in (FIELDS,FIELDS+list(OPTIONAL)): raise ValueError('Unexpected export columns')
        rows=[]
        for row in reader:
            if len(rows)>=LIMIT or None in row or any(v is None for v in row.values()): raise ValueError('Invalid export rows')
            row={k:unquote(v,encoding='utf-8',errors='strict') for k,v in row.items()}
            for k in ('t','region','map','level','spell'): row[k]=int(row[k])
            for k in ('x','y'): row[k]=float(row[k])
            if 'instance' in row: row['instance']=int(row['instance'])
            rows.append(row)
        return payload({'schema':1,'sharing':True,'records':rows})
    saved=SavedParser(content).parse().get('DeathAtlasDB')
    if not isinstance(saved,dict) or saved.get('schema')!=1: raise ValueError('Unsupported saved schema')
    settings=saved.get('settings',{})
    records=saved.get('records')
    if not isinstance(records,dict) or set(records)!=set(range(1,len(records)+1)): raise ValueError('Invalid saved array')
    return payload({'schema':1,'sharing':settings.get('sharing'),
       'records':[{**{k:r.get(k) for k in FIELDS},**{k:r[k] for k in OPTIONAL if k in r}} for _,r in sorted(records.items())]})

def connect(path):
    db=sqlite3.connect(path,timeout=10)
    db.execute('CREATE TABLE IF NOT EXISTS deaths (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
    return db

def ingest(path,data,now=None):
    data=payload(data); now=int(time.time()) if now is None else now
    rows=data['records']
    if any(r['t']>now+300 or r['t']<now-5*366*86400 for r in rows): raise ValueError('Timestamp outside accepted range')
    with closing(connect(path)) as db, db:
        added=updated=0
        for r in rows:
            existing=db.execute('SELECT body FROM deaths WHERE id=?',(r['id'],)).fetchone()
            body=json.dumps(r,sort_keys=True,ensure_ascii=False,separators=(',',':'))
            if existing:
                old=record(json.loads(existing[0]))
                if old==r: continue
                mutable={'cause','evidence','spell','environment'}
                if any(old[k]!=r[k] for k in FIELDS+list(OPTIONAL) if k not in mutable): raise ValueError('Conflicting event ID; transaction cancelled')
                db.execute('UPDATE deaths SET body=? WHERE id=?',(body,r['id'])); updated+=1
            else:
                db.execute('INSERT INTO deaths VALUES (?,?)',(r['id'],body)); added+=1
    return {'added':added,'updated':updated,'received':len(rows)}

def snapshot(path,days=30,client=None,realm=None,region=None,now=None,precision=None):
    now=int(time.time()) if now is None else now
    if not integer(days,1,90): raise ValueError('Days must be 1..90')
    today=now//86400; counts=Counter()
    if precision not in (None,'exact'): raise ValueError('Invalid precision')
    exact=precision=='exact'
    with closing(connect(path)) as db:
        for (body,) in db.execute('SELECT body FROM deaths'):
            r=json.loads(body); day=r['t']//86400
            if not today-days+1<=day<=today: continue
            if client and r['client']!=client or realm is not None and r['realm']!=realm or region is not None and r['region']!=region: continue
            cause=r['cause'] if r['cause'] in ('pvp','pve') else 'unknown'
            evidence=r['evidence'] if cause!='unknown' else 'unknown'
            band=(r['level']-1)//10+1 if 1<=r['level']<=200 else 0
            key=(r['client'],r['region'],r['realm'],r['map'],day,cause,evidence,context(r['context']),band,r['class'],r['faction'],r.get('instance',0),r.get('instanceName',''),r['x'] if exact else min(19,int(r['x']*20)),r['y'] if exact else min(19,int(r['y']*20)))
            counts[key]+=1
    if len(counts)>10000: raise ValueError('Snapshot too large; filter by client, realm, region or fewer days')
    keys=['client','region','realm','map','day','cause','evidence','context','levelBand','class','faction','instance','instanceName','x','y']
    cells=[dict(zip(keys,k),count=n) for k,n in sorted(counts.items())]
    return {'schema':5 if exact else 4,'grid':0 if exact else 20,'generated':now,'cells':cells}

def valid_snapshot(s):
    if not isinstance(s,dict) or s.get('schema') not in (1,2,3,4,5) or s.get('grid')!=(0 if s.get('schema')==5 else 20) or not integer(s.get('generated'),1,4102444800): raise ValueError('Invalid snapshot')
    cells=s.get('cells')
    if not isinstance(cells,list) or len(cells)>10000: raise ValueError('Invalid snapshot cells')
    result=[]
    for original in cells:
        if not isinstance(original,dict): raise ValueError('Invalid snapshot fields')
        c=dict(original)
        if s['schema']==1:
            if 'context' in c: raise ValueError('Unexpected legacy context')
            c['context']='unknown'
        if s['schema']<3:
            if 'levelBand' in c: raise ValueError('Unexpected legacy level bracket')
            c['levelBand']=0
        if s['schema']<4: c.update({'class':'','faction':'','instance':0,'instanceName':''})
        if set(c)!=set('client region realm map day cause evidence context levelBand class faction instance instanceName x y count'.split()): raise ValueError('Invalid snapshot fields')
        if not (c['client'] in ('retail','forever') and integer(c['region'],0,10) and text(c['realm'],100)
          and integer(c['map'],0,100000) and integer(c['day'],1,50000) and c['cause'] in CAUSES and c['context'] in CONTEXTS
          and c['evidence'] in EVIDENCE and (c['cause']=='unknown')==(c['evidence']=='unknown')
          and integer(c['levelBand'],0,20) and text(c['class'],20) and text(c['faction'],20) and integer(c['instance'],0,100000) and text(c['instanceName'],150)
          and (number(c['x'],0,1) if s['schema']==5 else integer(c['x'],0,19)) and (number(c['y'],0,1) if s['schema']==5 else integer(c['y'],0,19)) and integer(c['count'],1,10**9)):
            raise ValueError('Invalid snapshot value')
        if c['map']==0 and (c['x']!=0 or c['y']!=0): raise ValueError('Unlocated cell must have zero coordinates')
        result.append(c)
    return dict(s,schema=5 if s['schema']==5 else 4,cells=result)

def lua_string(s):
    # Lua 5.1 accepts UTF-8 bytes; fixed-width decimal control escapes cannot swallow following digits.
    return '"'+''.join('\\'+c if c in '\\"' else '\\%03d'%ord(c) if ord(c)<32 or ord(c)==127 else c for c in s)+'"'

def lua_snapshot(s):
    s=valid_snapshot(s)
    lines=['-- Generated from validated aggregate JSON; no downloaded code.','local _, A = ...',
           f'A.bundledSnapshot = {{schema={s["schema"]},grid={s["grid"]},generated={s["generated"]},cells={{']
    for c in s['cells']:
        parts=[k+'='+ (lua_string(v) if isinstance(v,str) else str(v)) for k,v in c.items()]
        lines.append('{'+','.join(parts)+'},')
    return '\n'.join(lines+['}}',''])

def atomic_write(path,content):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',newline='\n',dir=path.parent,delete=False) as f:
        tmp=Path(f.name); f.write(content)
    try: os.replace(tmp,path)
    finally:
        if tmp.exists(): tmp.unlink()

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

def request(url,data=None):
    parsed=urlsplit(url)
    if parsed.username or parsed.password or parsed.fragment or parsed.scheme not in ('https','http'): raise ValueError('Invalid service URL')
    if parsed.scheme=='http' and parsed.hostname not in ('localhost','127.0.0.1','::1'): raise ValueError('Remote service must use HTTPS')
    headers={'Accept':'application/json'}
    token=os.environ.get('DEATHATLAS_TOKEN')
    if token:
        headers['Authorization']='Bearer '+token
        headers['X-DeathAtlas-Key']=token
    sites_token=os.environ.get('OAI_SITES_TOKEN')
    sites_origin=os.environ.get('OAI_SITES_ORIGIN')
    if sites_token and sites_origin and parsed.scheme+'://'+parsed.netloc==sites_origin.rstrip('/'):
        headers['OAI-Sites-Authorization']='Bearer '+sites_token
    if data is not None: headers['Content-Type']='application/json'
    req=Request(url,data=json.dumps(data).encode() if data is not None else None,headers=headers)
    with build_opener(NoRedirect).open(req,timeout=30) as response:
        raw=response.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES: raise ValueError('Response too large')
    return json.loads(raw)

def wow_running():
    if os.name!='nt':
        from platform_support import game_running
        return game_running()
    # A windowed executable must also suppress its child process console.
    output=subprocess.run(['tasklist','/FO','CSV','/NH'],capture_output=True,text=True,check=True,
                          creationflags=subprocess.CREATE_NO_WINDOW).stdout
    names={'wow.exe','wowb.exe','wowt.exe','wowclassic.exe','wowclassicb.exe','wowforever.exe'}
    return any(row and row[0].lower() in names for row in csv.reader(io.StringIO(output)))

def sync(saved,url,addon_dir):
    if wow_running(): raise ValueError('Close every WoW client before syncing')
    path=Path(saved); before=path.stat()
    data=read_input(path)
    after=path.stat()
    if (before.st_mtime_ns,before.st_size)!=(after.st_mtime_ns,after.st_size): raise ValueError('Saved file changed; retry after WoW closes')
    if not (Path(addon_dir)/'DeathAtlas.toc').is_file(): raise ValueError('Choose the DeathAtlas addon directory')
    # One client/realm scope per sync; files from different accounts/clients should be synced separately.
    scopes={(r['client'],r['region'],r['realm']) for r in data['records']}
    if len(scopes)!=1: raise ValueError('A sync needs one client/region/realm; use offline snapshot filters for mixed histories')
    client,region,realm=next(iter(scopes))
    receipt={'added':0,'updated':0,'received':0}
    for start in range(0,len(data['records']),500):
        result=request(url.rstrip('/')+'/v1/upload',dict(data,records=data['records'][start:start+500]))
        for k in receipt: receipt[k]+=result.get(k,0)
    s=valid_snapshot(request(url.rstrip('/')+'/v1/snapshot?'+urlencode({'client':client,'region':region,'realm':realm,'days':30,'precision':'exact'})))
    if wow_running(): raise ValueError('WoW was opened; snapshot not written. Close it and retry.')
    output=Path(addon_dir)/'CommunityData.lua'
    if output.exists(): atomic_write(output.with_suffix('.lua.bak'),output.read_text(encoding='utf-8'))
    atomic_write(output,lua_snapshot(s))
    return receipt

def watch(saved,url,addon_dir,interval=60):
    last=None
    while True:
        try:
            if not wow_running():
                path=Path(saved)
                signature=(path.stat().st_mtime_ns,path.stat().st_size,int(time.time())//86400)
                if signature!=last:
                    result=sync(saved,url,addon_dir)
                    last=signature
                    print('Synced:',result,flush=True)
        except (OSError,ValueError,TypeError,KeyError) as e:
            print('Sync deferred:',type(e).__name__,flush=True)
        time.sleep(interval)

def make_server(database,host='127.0.0.1',port=8765):
    token=os.environ.get('DEATHATLAS_TOKEN','')
    if host not in ('127.0.0.1','localhost','::1') and len(token)<24:
        raise ValueError('Non-loopback binding requires DEATHATLAS_TOKEN of at least 24 characters and an HTTPS reverse proxy')
    connect(database).close()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass # Do not log payloads, IP addresses or credentials.
        def reply(self,status,obj):
            raw=json.dumps(obj,ensure_ascii=False).encode()
            self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(raw))); self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(raw)
        def do_POST(self):
            if self.path!='/v1/upload': self.reply(404,{'error':'Not found'}); return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if size<=0 or size>MAX_BYTES: raise ValueError('Invalid body size')
                if self.headers.get('Content-Type','').split(';')[0]!='application/json': raise ValueError('Expected application/json')
                self.connection.settimeout(15)
                raw=self.rfile.read(size)
                if len(raw)!=size: raise ValueError('Incomplete request')
                if token and not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+token): self.reply(401,{'error':'Unauthorized'}); return
                result=ingest(database,json.loads(raw)); self.reply(200,result)
            except (ValueError,TypeError,KeyError,TimeoutError,json.JSONDecodeError): self.reply(400,{'error':'Invalid upload'})
            except sqlite3.Error: self.reply(503,{'error':'Storage unavailable'})
        def do_GET(self):
            parsed=urlsplit(self.path)
            if parsed.path!='/v1/snapshot': self.reply(404,{'error':'Not found'}); return
            try:
                q=parse_qs(parsed.query)
                if set(q)-{'days','client','realm','region','precision'} or any(len(v)!=1 for v in q.values()): raise ValueError('Invalid filters')
                opts={k:v[0] for k,v in q.items()}
                opts['days']=int(opts.get('days',30))
                if 'region' in opts: opts['region']=int(opts['region'])
                if 'client' in opts and opts['client'] not in ('retail','forever'): raise ValueError('Invalid client')
                self.reply(200,snapshot(database,**opts))
            except (ValueError,TypeError,KeyError): self.reply(400,{'error':'Invalid filters or snapshot too large'})
            except sqlite3.Error: self.reply(503,{'error':'Storage unavailable'})
    server=ThreadingHTTPServer((host,port),Handler)
    server.daemon_threads=True
    return server

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    ex=sub.add_parser('export'); ex.add_argument('--input',required=True); ex.add_argument('--output',required=True)
    ing=sub.add_parser('ingest'); ing.add_argument('--input',required=True); ing.add_argument('--database',required=True)
    sn=sub.add_parser('snapshot'); sn.add_argument('--precision',choices=['exact']); sn.add_argument('--database',required=True); sn.add_argument('--output',required=True)
    sn.add_argument('--lua'); sn.add_argument('--days',type=int,default=30); sn.add_argument('--client',choices=['retail','forever']); sn.add_argument('--realm'); sn.add_argument('--region',type=int)
    se=sub.add_parser('serve'); se.add_argument('--database',required=True); se.add_argument('--host',default='127.0.0.1'); se.add_argument('--port',type=int,default=8765)
    sy=sub.add_parser('sync'); sy.add_argument('--saved',required=True); sy.add_argument('--url',required=True); sy.add_argument('--addon-dir',required=True)
    wa=sub.add_parser('watch'); wa.add_argument('--saved',required=True); wa.add_argument('--url',required=True); wa.add_argument('--addon-dir',required=True)
    im=sub.add_parser('import-snapshot'); im.add_argument('--input',required=True); im.add_argument('--addon-dir',required=True)
    a=p.parse_args()
    try:
        if a.command=='import-snapshot':
            if wow_running(): raise ValueError('Close every WoW client before importing')
            output=Path(a.addon_dir)/'CommunityData.lua'
            if not (Path(a.addon_dir)/'DeathAtlas.toc').is_file(): raise ValueError('Choose the DeathAtlas addon directory')
            raw=Path(a.input).read_bytes()
            if len(raw)>MAX_BYTES: raise ValueError('Input file too large')
            data=valid_snapshot(json.loads(raw))
            if output.exists(): atomic_write(output.with_suffix('.lua.bak'),output.read_text(encoding='utf-8'))
            atomic_write(output,lua_snapshot(data)); print('Validated snapshot imported.')
        elif a.command=='export': atomic_write(a.output,json.dumps(read_input(a.input),ensure_ascii=False,indent=2)); print('Export written; inspect before sharing.')
        elif a.command=='ingest': print(json.dumps(ingest(a.database,read_input(a.input))))
        elif a.command=='snapshot':
            data=snapshot(a.database,a.days,a.client,a.realm,a.region,precision=a.precision)
            atomic_write(a.output,json.dumps(data,ensure_ascii=False,indent=2))
            if a.lua:
                if wow_running(): raise ValueError('Close WoW before writing a Lua snapshot')
                atomic_write(a.lua,lua_snapshot(data))
            print('Aggregate snapshot written:',len(data['cells']),'cells')
        elif a.command=='sync': print(json.dumps(sync(a.saved,a.url,a.addon_dir)))
        elif a.command=='watch':
            try: watch(a.saved,a.url,a.addon_dir)
            except KeyboardInterrupt: pass
        elif a.command=='serve':
            server=make_server(a.database,a.host,a.port)
            print('Death Atlas API listening; uploads require opt-in. Ctrl+C stops it.')
            try: server.serve_forever()
            except KeyboardInterrupt: pass
            finally: server.server_close()
    except (ValueError,TypeError,KeyError,OSError) as e:
        p.exit(1,'Error: '+str(e)+'\n')

if __name__=='__main__': main()
