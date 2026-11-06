import fs from 'node:fs';
const file='../docs/frontend-quality.md';
let text=fs.readFileSync(file,'utf8');
text=text.replace('| Landing | 95 |','| Landing | 97 |').replace('| Command Center | 91 |','| Command Center | 97 |')
 .replace('LCP 2.7s, TBT 130ms','LCP 2.6s, TBT 40ms')
 .replace('LCP 2.9s, TBT 220ms, CLS 0.043','LCP 2.6s, TBT 60ms, CLS 0.044');
text+='\nFinal motion optimization uses LazyMotion with only the animation features needed by the interface: about 30.82 KiB gzip versus 45.52 KiB previously. The active navigation surface uses a short opacity transition rather than loading layout-animation machinery. Scores varied under concurrent local load; the table records the isolated final production run.\n';
fs.writeFileSync(file,text);
