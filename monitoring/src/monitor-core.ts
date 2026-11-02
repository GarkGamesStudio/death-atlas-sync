// Shared read-only probe: no histories, credentials or private API access.
export async function probe(base='https://garkgames.com/api/deathatlas/v1',request:typeof fetch=fetch,now=Date.now()){
 const get=async(path:string)=>{const r=await request(base+path,{headers:{Accept:'application/json','Cache-Control':'no-cache'},signal:AbortSignal.timeout(15000),redirect:'error'});if(!r.ok)throw Error('http');return r.json() as Promise<any>;};
 const health=await get('/health');if(health.service!=='Death Atlas'||health.maintenance===true||health.uploads===false)throw Error('service');
 const manifest=await get('/files/manifest');
 if(manifest.schema!==1||!Number.isSafeInteger(manifest.generated)||!Array.isArray(manifest.parts))throw Error('manifest');
 const seconds=now/1000,hourly=health.publicationIntervalSeconds===3600;
 const since=Number(health.publicationStartedAt||0);
 const rollout=hourly&&since>0&&seconds<(Math.floor(since/3600)+1)*3600+900;
 const age=(seconds-manifest.generated)/3600;if(age>(hourly&&!rollout?3:30)||age<-.1)throw Error('stale');
 const interval=hourly?3600:86400,offset=hourly?0:21600,grace=hourly?900:3600;
 const expected=Math.floor((seconds-offset)/interval)*interval+offset;
 if(!rollout&&seconds>=expected+grace&&manifest.generated<expected)throw Error('publication_late');
 const sample=manifest.parts[0];
 if(sample){if(!/^editions\/maps\/[a-f0-9]{64}\.json$/.test(sample.key))throw Error('reference');const map=await get('/files/'+sample.key);if(map.schema!==5||map.grid!==0||!Array.isArray(map.cells)||map.cells.length!==sample.cells)throw Error('map');}
 return {ok:true,serviceVersion:health.version,edition:manifest.generated,ageHours:Math.round(age*10)/10,maps:manifest.parts.length};
}
