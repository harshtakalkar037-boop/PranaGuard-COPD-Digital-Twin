import {useEffect,useRef,useState} from 'react';
import {api} from './api';
export function useRemote<T>(path:string|null,revision=0){
 const [data,setData]=useState<T|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(true);
 const previous=useRef<string|null>(null);
 useEffect(()=>{let active=true;
  if(previous.current!==path){setData(null);previous.current=path}
  if(!path){setData(null);setError('');setLoading(false);return;}
  setLoading(true);setError('');
  api<T>(path).then(value=>{if(active)setData(value)}).catch(err=>{if(active){setData(null);setError(String(err.message))}}).finally(()=>{if(active)setLoading(false)});
  return ()=>{active=false};
 },[path,revision]);
 // During the render before the path-change effect runs, never display data
 // from the previous patient under the new patient context.
 return previous.current===path?{data,error,loading}:{data:null,error:'',loading:!!path};
}
