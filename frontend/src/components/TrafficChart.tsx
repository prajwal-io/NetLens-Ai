import { useEffect, useId, useRef, useState } from 'react';
interface Bucket {time:string;normal:number;suspicious:number}
export function TrafficChart({data}:{data:Bucket[]}){
 const titleId=useId(),descId=useId();
 const ref=useRef<HTMLDivElement>(null);
 const [width,setWidth]=useState(720);
 useEffect(()=>{
  const element=ref.current;if(!element)return;
  const observer=new ResizeObserver(([entry])=>setWidth(Math.max(260,Math.round(entry.contentRect.width))));
  observer.observe(element);return()=>observer.disconnect();
 },[]);
 const [selected,setSelected]=useState<number|null>(null);
 const x=(i:number)=>48+i*((width-80)/(data.length-1));
 const y=(value:number)=>172-value/400*146;
 const path=(key:'normal'|'suspicious')=>data.map((r,i)=>(i?'L':'M')+x(i)+' '+y(r[key])).join(' ');
 const active=selected===null?null:data[selected]??null;
 return <div ref={ref} className="native-traffic-chart"><svg viewBox={`0 0 ${width} 205`} role="group" aria-labelledby={titleId} aria-describedby={descId}><title id={titleId}>Sample normal and suspicious traffic over time</title><desc id={descId}>Flow counts from {data[0].time} to {data[data.length-1].time}. Each point can be focused or selected. The complete values are also available in Read chart data.</desc>{[0,100,200,300,400].map(v=><g key={v}><line x1="48" x2={width-32} y1={y(v)} y2={y(v)} stroke="#edf0f4"/><text x="34" y={y(v)+4} textAnchor="end" fill="#53667f" fontSize="13">{v}</text></g>)}<path d={path('normal')} stroke="#3268f5" strokeWidth="2.5" vectorEffect="non-scaling-stroke" fill="none"/><path d={path('suspicious')} stroke="#ed554a" strokeWidth="2" vectorEffect="non-scaling-stroke" fill="none"/>{data.map((r,i)=><g key={r.time}>{(i===0||i===data.length-1||i===Math.floor(data.length/2))&&<text x={x(i)} y="196" textAnchor="middle" fill="#53667f" fontSize="13">{r.time}</text>}<circle cx={x(i)} cy={y(r.normal)} r={selected===i?5:12} fill={selected===i?'#3268f5':'transparent'} role="button" tabIndex={0} aria-label={`${r.time}: ${r.normal} normal and ${r.suspicious} suspicious sample flows`} onFocus={()=>setSelected(i)} onMouseEnter={()=>setSelected(i)} onClick={()=>setSelected(i)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setSelected(i)}}}><title>{r.time}: {r.normal} normal / {r.suspicious} suspicious</title></circle></g>)}</svg><div className="chart-reading" aria-live="polite">{active?<><strong>{active.time}</strong><span>Normal {active.normal}</span><span>Suspicious {active.suspicious}</span></>:<span>Hover or focus a point to inspect the sample.</span>}</div></div>;
}
