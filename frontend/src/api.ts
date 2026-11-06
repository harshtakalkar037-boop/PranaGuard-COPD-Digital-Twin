import {handleExpiredSession} from './session';
const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');
const API_BASE = API_ORIGIN ? `${API_ORIGIN}/api` : '/api';

/** JSON request with explicit transport, HTTP and invalid-response errors. */
export async function requestJson<T>(url:string,options:RequestInit={},sentToken?:string|null):Promise<T>{
  let response:Response;
  try{response=await fetch(url,options)}catch(err){
    if(err instanceof Error&&err.name==='AbortError')throw err;
    throw new Error('Network error: unable to reach the server. Check your connection and try again.');
  }
  if(!response.ok){
    let detail='';
    try{const body=await response.json();detail=typeof body.detail==='string'?body.detail:Array.isArray(body.detail)?body.detail.map((d:{loc?:string[];msg?:string})=>`${d.loc?.slice(1).join('.')||'request'}: ${d.msg||'Invalid value'}`).join('; '):'';}catch{/* an HTTP error can have a non-JSON body */}
    if(response.status===401)handleExpiredSession(sentToken,detail);
    const prefix:Record<number,string>={401:'Authentication required',403:'Permission denied',404:'Record not found',422:'Invalid request'};
    const title=prefix[response.status]||(response.status>=500?'Server error':`Request failed (${response.status})`);
    throw new Error(`${title} (HTTP ${response.status})${detail?`: ${detail}`:'.'}`);
  }
  try{return await response.json() as T}catch{throw new Error('Invalid server response: expected JSON. Please retry or contact the administrator.');}
}
export async function api<T>(path:string, options:RequestInit={}):Promise<T>{
  const token=sessionStorage.getItem('pg-demo-token');
  const portalToken=sessionStorage.getItem('pg-portal-token');
  return requestJson<T>(`${API_BASE}${path}`,{...options,headers:{'Content-Type':'application/json',...(token?{'X-Demo-Token':token}:{}),...(portalToken?{'Authorization':`Bearer ${portalToken}`}:{ }),...options.headers}},portalToken);
}

export const post=<T,>(path:string,body:unknown={})=>api<T>(path,{method:'POST',body:JSON.stringify(body)});

export function websocketUrl():string {
  const origin = API_ORIGIN || window.location.origin;
  const url = new URL(origin);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  url.pathname = '/api/ws';
  url.search = '';
  url.hash = '';
  return url.toString();
}
