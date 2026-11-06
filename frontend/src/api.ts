import {handleExpiredSession} from './session';
const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');
const API_BASE = API_ORIGIN ? `${API_ORIGIN}/api` : '/api';

export async function api<T>(path:string, options:RequestInit={}):Promise<T>{
  const token=sessionStorage.getItem('pg-demo-token');
  const portalToken=sessionStorage.getItem('pg-portal-token');
  const response=await fetch(`${API_BASE}${path}`,{...options,headers:{'Content-Type':'application/json',...(token?{'X-Demo-Token':token}:{}),...(portalToken?{'Authorization':`Bearer ${portalToken}`}:{ }),...options.headers}});
  if(!response.ok){let detail=response.statusText;try{const body=await response.json();detail=typeof body.detail==='string'?body.detail:Array.isArray(body.detail)?body.detail.map((d:{loc?:string[];msg?:string})=>`${d.loc?.slice(1).join('.')||'request'}: ${d.msg||'Invalid value'}`).join('; '):'Backend request failed.';}catch{/* retain status */}if(response.status===401)handleExpiredSession(portalToken,detail);throw new Error(detail);}
  return response.json();
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
