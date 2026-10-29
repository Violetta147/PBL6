import {makeModel,follow} from './model.mjs';import * as A from './vendor/kit/audit.mjs';import * as TA from './vendor/kit/turn-audit.mjs';import {writeFileSync} from 'node:fs';
const {T,R,P}=makeModel();
A.settle(R,P);A.auditOrExit(R,P);
const result=TA.orbitOrExit(T,R,P,{sweep:{at:x=>follow({device:x}),from:0,to:360,frame:1},clips:[{name:'open-close',at:t=>follow({device:35,explode:t<=1?t:2-t}),from:0,to:2,frame:1/60}],quick:process.argv.includes('--quick'),only:process.argv.find(a=>a.startsWith('--only='))?.slice(7).split(','),log:t=>console.log(new Date().toISOString(),t)});
writeFileSync('audit-results.json',JSON.stringify(result,null,2));
