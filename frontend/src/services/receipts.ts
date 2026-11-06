import { usePreference } from '../hooks/preferences';
import type { Validation } from './api';
export interface Receipt {
 id:string;
 kind:'csv-validation';
 filename:string;
 rows:number;
 columns:string[];
 received_at:string;
 note:string;
}
const empty:Receipt[]=[];
function isReceipts(value:unknown):value is Receipt[]{
 return Array.isArray(value)&&value.length<=20&&value.every(r=>r&&r.kind==='csv-validation'&&typeof r.id==='string'&&typeof r.filename==='string'&&Number.isInteger(r.rows)&&r.rows>0&&Array.isArray(r.columns)&&r.columns.every((c:unknown)=>typeof c==='string')&&typeof r.note==='string'&&typeof r.received_at==='string'&&Number.isFinite(Date.parse(r.received_at)));
}
export function useReceipts(){
 const [receipts,setReceipts]=usePreference('validation-receipts',empty,isReceipts);
 function addReceipt(result:Validation){
  const receipt:Receipt={id:crypto.randomUUID(),kind:'csv-validation',filename:result.filename,rows:result.row_count,columns:result.columns,received_at:new Date().toISOString(),note:'CSV validation only. Received by this browser; no ML inference or predictions. Traffic rows are not saved.'};
  setReceipts([receipt,...receipts].slice(0,20));
 }
 return {receipts,addReceipt,clear:()=>setReceipts([])};
}
export function downloadReceipt(receipt:Receipt){
 const url=URL.createObjectURL(new Blob([JSON.stringify(receipt,null,2)],{type:'application/json'}));
 const link=document.createElement('a');link.href=url;link.download='netsight-validation-'+receipt.id.slice(0,8)+'.json';
 try{document.body.append(link);link.click()}finally{link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
}
