import {test} from 'node:test';import assert from 'node:assert/strict';
import {checkWithRetry} from '../tools/github-monitor.mjs';
const now=1793512800000;
const good=async url=>Response.json(url.endsWith('/health')?{service:'Death Atlas'}:{schema:1,generated:now/1000,parts:[]});
test('healthy service succeeds without retry or waiting',async()=>{
 const result=await checkWithRetry({request:good,now:()=>now,wait:async()=>assert.fail('unexpected retry')});assert.equal(result.ok,true);assert.equal(result.attempt,1);
});
test('one network failure is retried before raising an operational alert',async()=>{
 let calls=0,waited=0;const result=await checkWithRetry({request:async url=>++calls===1?new Response('',{status:503}):good(url),now:()=>now,wait:async ms=>{waited+=ms;}});
 assert.equal(result.ok,true);assert.equal(result.attempt,2);assert.equal(waited,30000);
});
test('controlled failure exercises actual detector without calling production',async()=>{
 const result=await checkWithRetry({simulate:true,request:async()=>assert.fail('production must not be called'),wait:async()=>{}});
 assert.deepEqual(result,{ok:false,attempt:2,synthetic:true});
});
