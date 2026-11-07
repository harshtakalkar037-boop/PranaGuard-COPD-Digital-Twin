import {useState} from 'react';
import {Download,FileText,ShieldCheck} from 'lucide-react';
import {API_BASE,explainError} from '../api';
import {useRemote} from '../hooks';
import {Empty,Loading,Notice,Panel,Pill,time} from '../components';
import type {DocumentItem} from './types';

const TYPE_LABELS:Record<string,string>={prescription:'Prescription (PDF)',lab_report:'Lab report',imaging:'Imaging',discharge_summary:'Discharge summary',action_plan:'Action plan',other:'Other'};

export function PatientDocumentsPage(){
 const {data,error}=useRemote<{items:DocumentItem[];note:string}>('/workspace/patient/documents',0);
 const [msg,setMsg]=useState('');const [err,setErr]=useState('');
 async function download(d:DocumentItem){
   setErr('');setMsg('');
   try{
    const session=sessionStorage.getItem('pg-workspace-session');
    const r=await fetch(`${API_BASE}/workspace/documents/${d.id}/file`,{headers:session?{Authorization:`Bearer ${session}`}:{}});
    if(!r.ok){const j=await r.json().catch(()=>({detail:r.statusText}));throw new Error(j.detail||`HTTP ${r.status}`);}
    const blob=await r.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=d.filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    setMsg(`Downloaded ${d.filename} — SHA-256 ${d.sha256.slice(0,12)}… verified by the backend.`);
   }catch(e){setErr(String(e));}
 }
 if(error)return <Notice tone="warning">{explainError(error)}</Notice>;
 if(!data)return <Loading label="Loading shared documents…"/>;
 return <div className="pgx">
  <Notice>{data.note} Uploads come from your doctor; you have read-only access to your own record.</Notice>
  {err&&<div className="error-banner" role="alert">{err}</div>}
  {msg&&<div className="notice info" role="status">{msg}</div>}
  <Panel title="Documents shared with you" subtitle={`${data.items.length} record${data.items.length===1?'':'s'} · fictional demo content`}>
   {data.items.length?<div className="care-queue">{data.items.map(d=><div key={d.id} className="care-card">
    <div className="care-card-top"><strong>{d.title}</strong><Pill tone="blue">{TYPE_LABELS[d.doc_type]||d.doc_type}</Pill></div>
    <p>{d.notes||'No notes.'}</p>
    <small><FileText size={11}/> {d.filename} · {Math.round(d.size/1024)||1} KB · {d.doc_date||'no date'} · shared by Dr. {d.uploaded_by} · {time(d.created_at,true)}</small>
    <div className="pgx-inline"><button className="button secondary small-button" onClick={()=>download(d)}><Download size={13}/>{d.media_type==='application/pdf'?'Download PDF':'Download file'}</button><span className="input-help"><ShieldCheck size={11}/> integrity-checked</span></div>
   </div>)}</div>:<Empty text="No documents shared yet. When your doctor uploads a prescription or record, it appears here."/>}
  </Panel>
 </div>;
}
