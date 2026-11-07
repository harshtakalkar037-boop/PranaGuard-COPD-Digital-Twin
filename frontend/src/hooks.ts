import {useEffect,useState} from 'react';
import {api} from './api';
export function useRemote<T>(path:string|null,revision=0){
 const [data,setData]=useState<T|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(true);
 useEffect(()=>{let active=true;if(!path){setLoading(false);return;}
 setLoading(true);setError('');api<T>(path).then(value=>{if(active)setData(value);}).catch(err=>{if(active)setError(String(err.message));}).finally(()=>{if(active)setLoading(false);});
 return ()=>{active=false;};},[path,revision]);
 return {data,error,loading};
}
