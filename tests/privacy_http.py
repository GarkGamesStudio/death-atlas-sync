"""Real HTTP/D1/R2 + Windows DPAPI, synthetic profiles only. Port8796 disposable state."""
import sys,tempfile,time,json,secrets,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import engine
BASE='http://127.0.0.1:8796/api/deathatlas'
checks=0
def check(value,label=''):
 global checks
 assert value,label
 checks+=1
def lua(v):
 if isinstance(v,str):return engine.data.lua_string(v)
 if isinstance(v,bool):return 'true' if v else 'false'
 if isinstance(v,dict):return '{'+','.join('['+lua(k)+']='+lua(x) for k,x in v.items())+'}'
 if isinstance(v,list):return '{'+','.join(lua(x) for x in v)+'}'
 return str(v)
def publish(stamp):
 with urllib.request.urlopen('http://127.0.0.1:8796/__testpublish?time='+str(stamp*1000),timeout=30) as r:check(r.status==200,'publication')
now=int(time.time());edition=(now-21600)//86400*86400+21600
install='sync034-'+secrets.token_hex(5)
rows=[dict(id=install+'-'+str(i+1),t=edition-(40 if i==0 else 1)*86400,client='forever',region=3,realm=install,map=1411,x=.4137+i*.001,y=.6921,level=60,**{'class':'MAGE'},faction='Horde',cause='pve',evidence='last_damage',spell=0,environment='',context='none') for i in range(3)]
with tempfile.TemporaryDirectory(prefix='sync034-fixture-') as tmp,patch.object(engine.data,'wow_running',return_value=False):
 p=Path(tmp);addon=p/'Interface'/'AddOns'/'DeathAtlas';addon.mkdir(parents=True)
 (addon/'DeathAtlas.toc').write_text('fixture');(addon/'CommunityData.lua').write_text('-- old fixture')
 saved=p/'DeathAtlas.lua';db={'schema':1,'install':install,'seq':3,'settings':{'sharing':True},'records':rows}
 def save():saved.write_text('DeathAtlasDB = '+lua(db),encoding='utf-8')
 save();profile={'saved':str(saved),'addon':str(addon)};store=engine.Settings(p/'settings.dpapi')
 state={'schema':1,'profiles':{},'consent':True,'consentPolicy':engine.POLICY,'enabled':True}
 def sync():return engine.sync_profile(profile,state,store,BASE)
 try:sync()
 except urllib.error.HTTPError as e:check(e.code==503,'uploads received, first edition pending')
 else:raise AssertionError('Use fresh disposable test state')
 cred=state['profiles'][BASE+'|'+install]
 check(len(cred['uploaded'])==3);check(cred['token'].encode() not in store.path.read_bytes(),'DPAPI protects token')
 check(store.read()['profiles'][BASE+'|'+install]['token']==cred['token'])
 publish(edition);r=sync();check(r['sent']==0,'retry sends no duplicate uploads');check(r['cached'])
 cached=(addon/'CommunityData.lua').read_text();check('schema=5' in cached and '.4137' not in cached,'30-day cache excludes historical point')
 check((addon/'CommunityData.lua.bak').read_text()=='-- old fixture','cache backup')
 scope='?precision=exact&realm='+install
 snap=lambda:engine.api(BASE,'/v1/snapshot'+scope)
 all_=lambda:engine.api(BASE,'/v1/snapshot'+scope+'&days=all')
 check(sum(c['count'] for c in snap()['cells'])==2)
 check(sum(c['count'] for c in all_()['cells'])==3)
 rows.append(dict(rows[1],id=install+'-4',x=.5));db['seq']=4;save();check(sync()['sent']==1)
 check(sum(c['count'] for c in snap()['cells'])==2,'late upload not immediately public')
 publish(edition);check(sum(c['count'] for c in snap()['cells'])==2,'same edition frozen')
 publish(edition+86400);check(sync()['sent']==0);check(sum(c['count'] for c in snap()['cells'])==3)
 rows[0]['cause']='pvp';save();check(sync()['sent']==1,'archived correction sent once')
 publish(edition+2*86400);check(sync()['sent']==0)
 all_data=all_();check(sum(c['count'] for c in all_data['cells'])==4,'historical correction is not a duplicate')
 check(any(c['cause']=='pvp' and c['day']==rows[0]['t']//86400 for c in all_data['cells']))
 check(saved.read_text(encoding='utf-8')=='DeathAtlasDB = '+lua(db),'SavedVariables untouched')
 check(not any({'id','t','device','token','fingerprint'}&c.keys() for c in all_data['cells']))
 before=(addon/'CommunityData.lua').read_bytes()
 with patch.object(engine.data,'wow_running',return_value=True):
  try:sync()
  except engine.SyncError:check(True)
  else:raise AssertionError('WoW-open guard failed')
 check(before==(addon/'CommunityData.lua').read_bytes())
 result=engine.request_erasure(profile,state,store,BASE)
 check(result['erasure']=='queued');check(not state['consent'] and not state['enabled'])
 check(sum(c['count'] for c in all_()['cells'])==4,'not removed until next edition')
 publish(edition+3*86400);check(sum(c['count'] for c in all_()['cells'])==0,'removed from public all-time')
 check(engine.request_erasure(profile,state,store,BASE)['erasure']=='completed','revoked key can safely check completion')
 check(engine.api(BASE,'/v1/erase/status',{},cred['token'])['erasure']=='completed')
 try:engine.api(BASE,'/v1/upload',{'schema':1,'sharing':True,'records':[rows[0]]},cred['token'])
 except urllib.error.HTTPError as exc:check(exc.code==401,'revoked upload rejected')
 else:raise AssertionError('Erased installation can upload')
 check(saved.read_text(encoding='utf-8')=='DeathAtlasDB = '+lua(db),'local history still untouched')
 check(state['profiles'][BASE+'|'+install]['revoked'])
print('PASS',checks,'real Sync 0.4.0 HTTP/D1/R2/DPAPI checks')
