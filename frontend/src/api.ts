const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');
export const API_BASE = API_ORIGIN ? `${API_ORIGIN}/api` : '/api';

export class ApiError extends Error{
  status:number;
  constructor(status:number,message:string){super(message);this.status=status;}
}

export function explainError(e:unknown):string{
  if(e instanceof ApiError){
    if(e.status===0)return e.message;
    if(e.status===401)return 'Sign-in required or demo session expired. '+e.message;
    if(e.status===403)return 'Not permitted for this demo account (patient not assigned or insufficient role). '+e.message;
    if(e.status===404)return 'Not found: '+e.message;
    if(e.status===409)return 'Conflict: '+e.message;
    if(e.status===422)return 'Validation: '+e.message;
    if(e.status>=500)return 'Backend error (HTTP '+e.status+'): '+e.message;
    return e.message;
  }
  return String((e as Error)?.message||e);
}

const pendingGetRequests=new Map<string,Promise<unknown>>();

export async function api<T>(path:string, options:RequestInit={}):Promise<T>{
  const token=sessionStorage.getItem('pg-demo-token');
  const session=sessionStorage.getItem('pg-workspace-session');
  const method=(options.method||'GET').toUpperCase();
  const requestKey=method==='GET'?`${API_BASE}${path}|${session||''}|${token||''}`:null;
  if(requestKey){
    const pending=pendingGetRequests.get(requestKey);
    if(pending)return pending as Promise<T>;
  }
  const request=(async()=>{
    let response:Response;
    try{
      response=await fetch(`${API_BASE}${path}`,{...options,headers:{'Content-Type':'application/json',...(token?{'X-Demo-Token':token}:{}),...(session?{'Authorization':`Bearer ${session}`}:{}),...options.headers}});
    }catch{
      throw new ApiError(0,'Cannot reach the local PranaGuard backend. Start uvicorn and retry.');
    }
    if(!response.ok){let detail=response.statusText;try{const body=await response.json();detail=typeof body.detail==='string'?body.detail:Array.isArray(body.detail)?body.detail.map((d:{loc?:string[];msg?:string})=>`${d.loc?.slice(1).join('.')||'request'}: ${d.msg||'Invalid value'}`).join('; '):'Backend request failed.';}catch{/* retain status */}throw new ApiError(response.status,detail);}
    return response.json() as Promise<T>;
  })();
  if(!requestKey)return request;
  pendingGetRequests.set(requestKey,request);
  try{return await request;}finally{if(pendingGetRequests.get(requestKey)===request)pendingGetRequests.delete(requestKey);}
}

export const post=<T,>(path:string,body:unknown={})=>api<T>(path,{method:'POST',body:JSON.stringify(body)});
export const put=<T,>(path:string,body:unknown={})=>api<T>(path,{method:'PUT',body:JSON.stringify(body)});
export const patch=<T,>(path:string,body:unknown={})=>api<T>(path,{method:'PATCH',body:JSON.stringify(body)});

export function websocketUrl():string {
  const origin = API_ORIGIN || window.location.origin;
  const url = new URL(origin);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  url.pathname = '/api/ws';
  url.search = '';
  url.hash = '';
  return url.toString();
}
