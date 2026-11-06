import { useReceipts } from '../services/receipts';
import { useEffect, useRef, useState } from 'react';
import { Upload, ArrowRight, ArrowDownToLine, CheckCircle2, X, FileText } from 'lucide-react';
import { api, type Validation } from '../services/api';
import { Panel, Empty } from '../components/ui';
import { ContextNote, DefinitionList } from '../components/WorkspaceDetails';

const limit=5*1024*1024;
function fileError(file:File){
 if(!file.name.toLowerCase().endsWith('.csv'))return 'Choose a file with a .csv extension.';
 if(file.size===0)return 'This file is empty. Choose a CSV containing traffic records.';
 if(file.size>limit)return 'This file exceeds 5 MiB. Choose a smaller CSV.';
 return '';
}
export default function Analyzer(){
 const {addReceipt}=useReceipts();
 const [file,setFile]=useState<File|null>(null),[result,setResult]=useState<Validation|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[progress,setProgress]=useState(0),[notice,setNotice]=useState(''),[dragging,setDragging]=useState(false);
 const input=useRef<HTMLInputElement>(null),controller=useRef<AbortController|null>(null);
 useEffect(()=>()=>controller.current?.abort(),[]);
 function choose(next:File|undefined){
  if(controller.current)return;
  setResult(null);setNotice('');setFile(next??null);setError(next?fileError(next):'');setProgress(0);setDragging(false);
 }
 function remove(){choose(undefined);if(input.current)input.current.value=''}
 async function validate(){
  if(!file||fileError(file)||controller.current)return;
  const request=new AbortController();controller.current=request;
  setBusy(true);setError('');setResult(null);setNotice('');setProgress(0);
  try{const next=await api.validate(file,{signal:request.signal,onProgress:setProgress});if(!request.signal.aborted){setResult(next);addReceipt(next)}}
  catch(e){if((e as Error).name==='AbortError')setNotice('Validation cancelled. You can retry or choose another file.');else setError((e as Error).message)}
  finally{if(controller.current===request){controller.current=null;setBusy(false)}}
 }
 return <><ContextNote>Validation is available now. Your file is checked in memory and is not stored. Refreshing or leaving this page clears the file. A session receipt stores metadata only; ML classification requires a trained model.</ContextNote><div className="two-col analyzer-layout"><Panel title="Bring your traffic data"><p className="description">Start with a compatible flow CSV. We will check its structure and show you what is inside.</p><div className={'dropzone '+(dragging?'dragging':'')} onDragOver={e=>{e.preventDefault();if(!busy)setDragging(true)}} onDragLeave={()=>setDragging(false)} onDrop={e=>{e.preventDefault();if(e.dataTransfer.files.length>1){setError('Choose one CSV at a time.');setDragging(false);return}choose(e.dataTransfer.files[0])}}><Upload size={30} aria-hidden="true"/><h3>{file?'Your dataset is selected':'Drop your traffic CSV here'}</h3><p>UTF-8 CSV / up to 5 MiB / 50,000 flows</p><input ref={input} type="file" accept=".csv" aria-label="Traffic CSV file" disabled={busy} tabIndex={-1} onChange={e=>choose(e.target.files?.[0])}/><button disabled={busy} onClick={()=>input.current?.click()}>{file?'Replace file':'Browse files'}</button></div>{file&&<div className="selected-file"><FileText size={20} aria-hidden="true"/><div><strong>{file.name}</strong><span>{file.size<1024?file.size+' bytes':(file.size/1024).toFixed(1)+' KiB'} / CSV / {new Date(file.lastModified).toLocaleDateString()}</span></div><button aria-label="Remove selected file" disabled={busy} onClick={remove}><X size={18}/></button></div>}<div className="upload-actions"><a href="/sample-flows.csv" download><ArrowDownToLine size={17}/> Download sample CSV</a><button className="primary" disabled={!file||busy||!!(file&&fileError(file))} onClick={validate}>{busy?'Validating...':'Validate CSV'}<ArrowRight size={16}/></button></div>{busy&&<div className="upload-progress"><div role="status">{progress<100?'Uploading CSV: '+progress+'%':'Upload complete. Checking structure and values...'}</div><progress aria-label={progress<100?'CSV upload progress':'Validating CSV structure'} max={100} value={progress<100?progress:undefined}/><button onClick={()=>controller.current?.abort()}>Cancel validation</button></div>}{notice&&<p className="validation-notice" role="status">{notice}</p>}{error&&<div className="error" role="alert"><span>{error}</span>{file&&!fileError(file)&&<button onClick={validate} disabled={busy}>Retry</button>}</div>}{result&&<div className="success" role="status"><CheckCircle2 size={20}/><span><strong>{result.row_count} flows validated</strong><br/>{result.message}</span></div>}</Panel><Panel title="A clear input contract" aside={<span className="tag">flow-v1</span>}><p className="description">These four columns form the foundation schema. Additional columns are preserved in the preview.</p><DefinitionList items={ [['Destination Port','Integer / 0-65535'],['Flow Duration','Microseconds / nonnegative'],['Total Fwd Packets','Integer / nonnegative'],['Total Backward Packets','Integer / nonnegative']]}/><div className="inline-note"><h3>What gets checked?</h3><p>Required headers, duplicate columns, row lengths, numeric types, finite values, and upload limits.</p></div></Panel></div><Panel title="Inside your dataset" aside={<span className="tag">{result?'Validated input':'Awaiting a file'}</span>}>{result?<div className="table-scroll" tabIndex={0} role="region" aria-label="Validated dataset preview"><table><caption>First {result.preview.length} of {result.row_count} validated rows / validation only</caption><thead><tr>{result.columns.map(c=><th scope="col" key={c}>{c}</th>)}</tr></thead><tbody>{result.preview.map((r,i)=><tr key={i}>{result.columns.map(c=><td key={c}>{r[c]}</td>)}</tr>)}</tbody></table></div>:<Empty title="A preview before predictions">Validate a CSV to inspect its first five rows. This preview shows your input data, without adding classification labels.</Empty>}</Panel></>;
}
