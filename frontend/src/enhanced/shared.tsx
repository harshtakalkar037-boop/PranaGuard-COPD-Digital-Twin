import {useState} from 'react';
import type {FormEvent,ReactNode} from 'react';
import {AlertTriangle} from 'lucide-react';
import {Notice} from '../components';
export const prefix='/enhanced';
export const label=(s:string)=>s.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());
export const date=(s:string|null|undefined)=>s?new Date(s).toLocaleString('en-GB',{timeZone:'UTC',dateStyle:'medium',timeStyle:'short'})+' UTC':'Not available';
export const requestId=()=>globalThis.crypto?.randomUUID?.().replaceAll('-','')||`demo_${Date.now()}_${Math.random().toString(36).slice(2)}`;
export interface PageProps {revision:number;refresh:()=>void;notify:(message:string)=>void;}
export function useMutation({refresh,notify}:Pick<PageProps,'refresh'|'notify'>){
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 async function run<T>(fn:()=>Promise<T>,success?:string|((result:T)=>string)):Promise<T|undefined>{
  setBusy(true);setError('');try{const result=await fn();refresh();if(success)notify(typeof success==='function'?success(result):success);return result;}
  catch(e){setError(e instanceof Error?e.message:'Request failed. Retry the backend action.');return undefined;}finally{setBusy(false);}
 }
 return {run,busy,error,clearError:()=>setError('')};
}
export function ErrorNotice({error}:{error:string}){return error?<div role="alert" className="pgx-error"><Notice tone="warning"><strong>Request could not be completed.</strong> {error}</Notice></div>:null;}
export function Field({label:caption,id,children,hint}:{label:string;id:string;children:ReactNode;hint?:string}){return <div className="pgx-field"><label className="field-label" htmlFor={id}>{caption}</label>{children}{hint&&<small className="pgx-help">{hint}</small>}</div>;}
export function DemoNotice(){return <Notice tone="warning"><strong>Fictional monitoring workspace.</strong> All patient details and device readings are demo data. No real hardware, diagnosis, clinical intervention or emergency response is provided. Original v1 study: 72h discrimination is below chance and sensitivity is zero at 0.35 for every original horizon. Separate v3 48h evidence is labelled explicitly; none is clinically validated.</Notice>;}
export function SubmitButton({busy,children}:{busy:boolean;children:ReactNode}){return <button className="button primary" type="submit" disabled={busy}>{busy?'Saving to backend…':children}</button>;}
export function onSubmit(fn:()=>void){return (e:FormEvent)=>{e.preventDefault();fn();};}
export function Missing(){return <span className="pgx-missing"><AlertTriangle size={12}/>Missing</span>;}
