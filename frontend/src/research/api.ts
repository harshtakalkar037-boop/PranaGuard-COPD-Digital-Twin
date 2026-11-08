/** Audio upload helper — FormData multipart (browser sets the boundary; the shared JSON helper must not be reused for file bodies). */
import {ApiError} from '../api';

const API_ORIGIN=(import.meta.env.VITE_API_BASE_URL||'').replace(/\/+$/,'');
const API_BASE=API_ORIGIN?`${API_ORIGIN}/api`:'/api';

export async function uploadCoughAudio<T>(file:File):Promise<T>{
  const body=new FormData();body.append('file',file,file.name);
  const session=sessionStorage.getItem('pg-workspace-session');
  let response:Response;
  try{
    response=await fetch(`${API_BASE}/models/cough/infer`,{method:'POST',body,headers:{...(session?{'Authorization':`Bearer ${session}`}:{})}});
  }catch{
    throw new ApiError(0,'Cannot reach the local PranaGuard backend. Start uvicorn and retry.');
  }
  if(!response.ok){
    let detail=response.statusText;
    try{const parsed=await response.json();detail=typeof parsed.detail==='string'?parsed.detail:'Backend request failed.';}catch{/* keep status text */}
    throw new ApiError(response.status,detail);
  }
  return response.json() as Promise<T>;
}
