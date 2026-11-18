import fs from 'node:fs';
for(const name of ['landing','dashboard']){
 const r=JSON.parse(fs.readFileSync('../docs/lighthouse-'+name+'.report.json'));
 console.log(name,JSON.stringify({scores:Object.fromEntries(Object.entries(r.categories).map(([k,v])=>[k,Math.round(v.score*100)])),metrics:Object.fromEntries(['first-contentful-paint','largest-contentful-paint','cumulative-layout-shift','total-blocking-time'].map(k=>[k,r.audits[k].displayValue])),issues:Object.values(r.audits).filter(a=>a.score!==null&&a.score<.9).map(a=>({id:a.id,title:a.title,value:a.displayValue}))},null,2));
}
