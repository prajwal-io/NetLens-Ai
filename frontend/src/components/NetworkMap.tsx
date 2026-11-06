import { isBoolean, usePageVisibility, usePreference } from '../hooks/preferences';
import { useId, useRef } from 'react';
import { m, useInView, useReducedMotion } from 'motion/react';

const nodes = [
 {id:'gateway',name:'Gateway',address:'10.0.0.1',x:400,y:210,detail:'Routes traffic between the illustrated devices. Select another node to follow its connection.'},
 {id:'workstation',name:'Workstation',address:'192.168.1.24',x:140,y:100,detail:'An example client opening an HTTPS connection through the gateway.',port:'443 / HTTPS'},
 {id:'dns',name:'DNS resolver',address:'10.0.0.4',x:135,y:330,detail:'An example name-resolution exchange. Short request and response flows.',port:'53 / DNS'},
 {id:'server',name:'Application server',address:'10.0.0.8',x:665,y:105,detail:'An example application endpoint receiving requests from a client.',port:'443 / HTTPS'},
 {id:'remote',name:'Remote host',address:'10.0.0.12',x:670,y:325,detail:'A highlighted connection illustrates where an investigator might look next. It is not a detected threat.',port:'22 / SSH'}
];
const isNode=(v:unknown):v is string=>typeof v==='string'&&nodes.some(n=>n.id===v);
const isZoom=(v:unknown):v is number=>typeof v==='number'&&[1,1.25,1.5,1.75].includes(v);
export function NetworkMap({compact=false,selectedDevice,onDeviceSelect}:{compact?:boolean;selectedDevice?:string;onDeviceSelect?:(id:string)=>void}){
 const [savedSelection,setSavedSelection]=usePreference('network-node','workstation',isNode);
 const selected=selectedDevice&&isNode(selectedDevice)?selectedDevice:savedSelection;
 const selectDevice=(id:string)=>{if(onDeviceSelect)onDeviceSelect(id);else setSavedSelection(id)};
 const reduce=useReducedMotion();
 const patternId=useId();
 const ref=useRef(null); const inView=useInView(ref); const [paused,setPaused]=usePreference('network-paused',false,isBoolean);
 const [zoom,setZoom]=usePreference('network-zoom',1,isZoom);const visible=usePageVisibility();
 const node=nodes.find(n=>n.id===selected)!;
 return <div ref={ref} className={'network-map '+(compact?'compact-map':'')}>
  <div className="map-heading"><span><span className="signal-mark"/> A network, made readable</span><span>Conceptual visualization</span><button className="flow-motion-toggle" aria-pressed={paused} onClick={()=>setPaused(!paused)}>{paused?'Resume flow':'Pause flow'}</button></div>
  <label className="device-select">Inspect device<select value={selected} onChange={e=>selectDevice(e.target.value)}>{nodes.map(n=><option key={n.id} value={n.id}>{n.name}</option>)}</select></label>
  <div className="network-tools"><span>Zoom follows the selected device</span><div><button aria-label="Zoom out network diagram" disabled={zoom===1} onClick={()=>setZoom(zoom-.25)}>-</button><output aria-label="Network zoom">{Math.round(zoom*100)}%</output><button aria-label="Zoom in network diagram" disabled={zoom===1.75} onClick={()=>setZoom(zoom+.25)}>+</button><button onClick={()=>{setZoom(1);selectDevice('workstation')}}>Reset diagram</button></div></div>
  <svg viewBox={`${Math.max(0,Math.min(800-800/zoom,node.x-400/zoom))} ${Math.max(0,Math.min(420-420/zoom,node.y-210/zoom))} ${800/zoom} ${420/zoom}`} role="group" aria-label="Interactive conceptual network. Select a device to inspect its connection.">
   <defs><pattern id={patternId} width="32" height="32" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".8" fill="var(--map-grid)"/></pattern></defs>
   <rect width="800" height="420" fill={`url(#${patternId})`}/>
   {[70,120,170].map(r=><circle key={r} cx="400" cy="210" r={r} fill="none" stroke="var(--map-ring)"/>)}
   {nodes.slice(1).map(n=><g key={n.id}>
    <path d={`M400 210 C${n.x} 210,400 ${n.y},${n.x} ${n.y}`} fill="none" stroke={selected===n.id?'var(--signal-blue)':'var(--map-link)'} strokeWidth={selected===n.id?2:1.2}/>
    {selected===n.id&&!reduce&&!paused&&inView&&visible&&<circle r="4" fill="var(--signal-blue)"><animateMotion dur="3s" repeatCount="indefinite" path={`M400 210 C${n.x} 210,400 ${n.y},${n.x} ${n.y}`}/></circle>}
   </g>)}
   {nodes.map(n=><g key={n.id} role="button" tabIndex={0} aria-label={`Inspect ${n.name}`} aria-pressed={selected===n.id} onClick={()=>selectDevice(n.id)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectDevice(n.id)}}} className="network-node"><title>{n.name}: {n.address}</title>
    <rect x={n.x-35} y={n.y-35} width="70" height="70" rx="16" fill={selected===n.id?'var(--signal-blue)':'var(--map-node)'} stroke={selected===n.id?'var(--signal-blue)':'var(--map-link)'}/>
    <path d={`M${n.x-10} ${n.y-7}h20v13h-20z M${n.x-6} ${n.y+12}h12 M${n.x} ${n.y+6}v6`} stroke={selected===n.id?'#08111e':'var(--map-icon)'} fill="none" strokeWidth="1.6"/>
    <text className="node-name" x={n.x} y={n.y+61} textAnchor="middle" fill="var(--ink)" fontSize={compact?22:18} fontWeight="500">{n.name}</text>
    {!compact&&<text className="node-address" x={n.x} y={n.y+82} textAnchor="middle" fill="var(--muted)" fontSize="15">{n.address}</text>}
   </g>)}
  </svg>
  <m.div className="map-inspector" key={selected} initial={{opacity:.5}} animate={{opacity:1}} transition={{duration:.18}} aria-live="polite"><span className="inspector-label">Selected connection</span><strong>{node.name} <span>{node.port??'Network routing'}</span></strong><p><span className="selected-address">{node.address}</span> / {node.detail}</p></m.div>
 </div>;
}
