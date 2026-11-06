import { useCallback, useEffect, useRef, useState } from 'react';
import { api, type Health } from '../services/api';
export function useBackendStatus(){
 const [health,setHealth]=useState<Health|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(true),[lastChecked,setLastChecked]=useState<Date|null>(null),[lastGood,setLastGood]=useState<Date|null>(null),[online,setOnline]=useState(navigator.onLine);
 const controller=useRef<AbortController|null>(null);
 const refresh=useCallback(async()=>{
  controller.current?.abort();
  const request=new AbortController();controller.current=request;
  setLoading(true);setError('');
  try{
   const next=await api.health(request.signal);
   if(request.signal.aborted)return;
   setHealth(next);setLastGood(new Date());
  }catch(e){
   if(request.signal.aborted)return;
   setHealth(null);setError((e as Error).message);
  }finally{if(!request.signal.aborted){setLoading(false);setLastChecked(new Date())}}
 },[]);
 useEffect(()=>{
  void refresh();
  const timer=setInterval(()=>{if(!document.hidden&&navigator.onLine)void refresh()},30000);
  const visibility=()=>{if(!document.hidden)void refresh()};
  const connectivity=()=>{setOnline(navigator.onLine);if(navigator.onLine)void refresh();else{controller.current?.abort();setHealth(null);setLoading(false);setError('You are offline. Reconnect, then retry the backend connection.')}};
  document.addEventListener('visibilitychange',visibility);window.addEventListener('online',connectivity);window.addEventListener('offline',connectivity);
  return()=>{clearInterval(timer);controller.current?.abort();document.removeEventListener('visibilitychange',visibility);window.removeEventListener('online',connectivity);window.removeEventListener('offline',connectivity)};
 },[refresh]);
 return {health,error,loading,lastChecked,lastGood,online,refresh};
}
