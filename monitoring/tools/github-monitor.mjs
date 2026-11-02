import {appendFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import {probe} from '../src/monitor-core.ts';

export async function checkWithRetry({request=fetch,now=()=>Date.now(),wait=ms=>new Promise(resolve=>setTimeout(resolve,ms)),simulate=false}={}){
 const transport=simulate?async()=>new Response('',{status:503}):request;
 for(let attempt=1;attempt<=2;attempt++){
  try{return {ok:true,attempt,...await probe(undefined,transport,now())};}
  catch{if(attempt===2)return {ok:false,attempt,synthetic:simulate};await wait(simulate?0:30000);}
 }
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
 const simulate=process.env.SIMULATE_FAILURE==='true';
 const result=await checkWithRetry({simulate});
 const title=simulate?'CONTROLLED TEST — synthetic failure':result.ok?'Death Atlas is available':'Death Atlas needs operator review';
 const detail=result.ok?'API, published edition and one map verified.':'Two checks failed. Review API health, publication schedule and map files. No player history or credential is included.';
 console.log(title);console.log(detail);
 if(result.ok)console.log(JSON.stringify({edition:result.edition,ageHours:result.ageHours,maps:result.maps,attempt:result.attempt}));
 if(simulate)console.log('The production website and data were not changed. This failure is intentional.');
 if(process.env.GITHUB_STEP_SUMMARY)appendFileSync(process.env.GITHUB_STEP_SUMMARY,'## '+title+'\n\n'+detail+'\n\n'+(simulate?'Synthetic transport only; production was not changed.\n':'Publication follows the service schedule: hourly editions have 15 minutes of grace; daily editions at 06:00 UTC have one hour. Checks run on GitHub and may be delayed.\n'));
 if(!result.ok)process.exitCode=1;
}
