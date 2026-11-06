import { useCallback, useEffect, useState } from 'react';

const preferenceEvent='netsight-preferences';
const memoryPreferences=new Map<string,unknown>();
export function usePreference<T>(key:string,fallback:T,accept:(value:unknown)=>value is T){
 const read=useCallback(()=>{
  try{const raw=sessionStorage.getItem('netsight:'+key);const value=raw===null?(memoryPreferences.get(key)??fallback):JSON.parse(raw);return accept(value)?value:fallback}catch{const value=memoryPreferences.get(key);return accept(value)?value:fallback}
 },[key,fallback,accept]);
 const [value,setValue]=useState<T>(read);
 useEffect(()=>{const update=()=>setValue(read());window.addEventListener(preferenceEvent,update);return()=>window.removeEventListener(preferenceEvent,update)},[read]);
 const save=useCallback((next:T)=>{
  memoryPreferences.set(key,next);setValue(next);try{sessionStorage.setItem('netsight:'+key,JSON.stringify(next))}catch{/* Preferences still work when storage is disabled. */}
  window.dispatchEvent(new Event(preferenceEvent));
 },[key]);
 return [value,save] as const;
}
export const isBoolean=(v:unknown):v is boolean=>typeof v==='boolean';
export const isString=(v:unknown):v is string=>typeof v==='string';
export function usePageVisibility(){
 const [visible,setVisible]=useState(!document.hidden);
 useEffect(()=>{const update=()=>setVisible(!document.hidden);document.addEventListener('visibilitychange',update);return()=>document.removeEventListener('visibilitychange',update)},[]);
 return visible;
}
