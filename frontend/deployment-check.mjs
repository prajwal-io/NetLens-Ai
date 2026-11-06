const base=process.env.AUDIT_URL||'http://127.0.0.1:4175';
for(const path of ['/','/command-center','/threat-investigation?q=443&label=All&sort=port','/unknown-route']){
 const response=await fetch(base+path);
 if(response.status!==200)throw new Error('SPA route failed: '+path);
 if(response.headers.get('x-content-type-options')!=='nosniff')throw new Error('Missing content-type protection');
 if(response.headers.get('referrer-policy')!=='strict-origin-when-cross-origin')throw new Error('Missing referrer policy');
}
const health=await(await fetch(base+'/api/v1/health')).json();
if(health.status!=='ok'||health.model_loaded!==false)throw new Error('Unexpected local API health');
console.log('PASS: direct SPA routes, deep links, preview headers, and same-origin API health.');
