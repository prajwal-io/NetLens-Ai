export interface Health { status:string;service:string;model_loaded:boolean;model_version:string|null }
export interface Validation {valid:boolean;filename:string;row_count:number;columns:string[];preview:Record<string,string>[];message:string}
const base=((import.meta as ImportMeta & {env:Record<string,string>}).env.VITE_API_BASE_URL||'/api/v1').replace(/\/$/,'');
export class ApiError extends Error{
 constructor(message:string,public status=0){super(message);this.name='ApiError'}
}
function decode(text:string,status:number){
 let body;
 try{body=JSON.parse(text)}catch{throw new ApiError(status>=400?'Cannot reach NetSight API. Check that the backend is running on port 8000.':'The API returned an unreadable response. Please retry.',status)}
 if(status<200||status>=300)throw new ApiError(typeof body?.error?.message==='string'?body.error.message:'The request could not be completed.',status);
 return body;
}
function validated(body:unknown):Validation{
 const r=body as Validation|null;
 const strings=(v:unknown):v is string[]=>Array.isArray(v)&&v.length>0&&v.every(c=>typeof c==='string'&&c.trim().length>0);
 if(!r||r.valid!==true||typeof r.filename!=='string'||!r.filename.trim()||typeof r.message!=='string'||!Number.isInteger(r.row_count)||r.row_count<1||!strings(r.columns)||new Set(r.columns).size!==r.columns.length||!Array.isArray(r.preview)||r.preview.length<1||r.preview.length>Math.min(5,r.row_count)||!r.preview.every(row=>row&&typeof row==='object'&&!Array.isArray(row)&&r.columns.every(c=>typeof row[c]==='string')))throw new ApiError('The validation response was incomplete. Please retry.');
 return r;
}
export const api={
 async health(signal?:AbortSignal):Promise<Health>{
  try{
   const response=await fetch(base+'/health',{signal:signal?AbortSignal.any([signal,AbortSignal.timeout(15000)]):AbortSignal.timeout(15000)});
   const body=decode(await response.text(),response.status) as Health;
   if(!body||body.status!=='ok'||typeof body.service!=='string'||typeof body.model_loaded!=='boolean'||(body.model_version!==null&&typeof body.model_version!=='string'))throw new ApiError('The backend returned an invalid health response.');
   return body;
  }catch(e){
   if(e instanceof TypeError)throw new ApiError('Cannot reach NetSight API. Check that the backend is running on port 8000.');
   if(e instanceof DOMException&&e.name==='TimeoutError')throw new ApiError('The API request timed out. Please retry.');
   throw e;
  }
 },
 validate(file:File,options:{signal?:AbortSignal;onProgress?:(percent:number)=>void}={}):Promise<Validation>{
  return new Promise((resolve,reject)=>{
   const xhr=new XMLHttpRequest();
   const abort=()=>xhr.abort();
   const clean=()=>options.signal?.removeEventListener('abort',abort);
   xhr.open('POST',base+'/traffic/validate');xhr.timeout=30000;
   xhr.upload.onprogress=e=>{if(e.lengthComputable)options.onProgress?.(Math.min(100,Math.round(e.loaded/e.total*100)))};
   xhr.upload.onload=()=>options.onProgress?.(100);
   xhr.onload=()=>{clean();try{resolve(validated(decode(xhr.responseText,xhr.status)))}catch(e){reject(e)}};
   xhr.onerror=()=>{clean();reject(new ApiError('Cannot reach NetSight API. Check that the backend is running on port 8000.'))};
   xhr.ontimeout=()=>{clean();reject(new ApiError('CSV validation timed out. Please retry.'))};
   xhr.onabort=()=>{clean();reject(new DOMException('Validation cancelled.','AbortError'))};
   if(options.signal?.aborted){reject(new DOMException('Validation cancelled.','AbortError'));return}
   options.signal?.addEventListener('abort',abort,{once:true});
   const data=new FormData();data.append('file',file);xhr.send(data);
  });
 }
};
