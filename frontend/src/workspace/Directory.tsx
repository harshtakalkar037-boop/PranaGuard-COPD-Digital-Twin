import {useEffect,useMemo,useState} from 'react';
import {ArrowRight,ChevronLeft,ChevronRight,ClipboardList,Search,ShieldCheck,Users} from 'lucide-react';
import {api,explainError} from '../api';
import {Empty,Loading,Notice,Panel,Pill,number,pct,time} from '../components';
import type {Directory,DirectoryItem,SessionUser} from './types';

export function DirectoryPage({user,revision,onOpen,onTwin}:{user:SessionUser;revision:number;onOpen:(pid:string)=>void;onTwin:(pid:string)=>void}){
 const [q,setQ]=useState('');const [city,setCity]=useState('');const [origin,setOrigin]=useState('');const [risk,setRisk]=useState('');const [sort,setSort]=useState<'name'|'city'|'risk'|'updated'>('name');const [page,setPage]=useState(1);
 const [data,setData]=useState<Directory|null>(null);const [error,setError]=useState('');const [loading,setLoading]=useState(true);
 const query=useMemo(()=>{const p=new URLSearchParams();if(q)p.set('q',q);if(city)p.set('city',city);if(origin)p.set('origin',origin);if(risk)p.set('risk',risk);p.set('sort',sort);p.set('page',String(page));p.set('page_size','12');return p.toString();},[q,city,origin,risk,sort,page]);
 useEffect(()=>{const t=setTimeout(()=>{setLoading(true);api<Directory>(`/workspace/patients?${query}`).then(d=>{setData(d);setError('');}).catch(e=>setError(explainError(e))).finally(()=>setLoading(false));},120);return ()=>clearTimeout(t);},[query,revision]);
 useEffect(()=>setPage(1),[q,city,origin,risk]);
 const cities=useMemo(()=>['Pune','Mumbai','Delhi','Bengaluru'],[]);
 const maxPage=data?Math.max(1,Math.ceil(data.total/data.page_size)):1;
 return <div className="pgx" data-testid="patient-directory">
  <div className="metric-grid four">
   <div className="metric-card"><div className="metric-head"><span>Signed in as</span></div><div className="metric-number metric-name">{user.display_name}</div><div className="metric-detail">{user.role==='doctor'?'Demo clinician':'Demo patient viewer'}</div></div>
   <div className="metric-card"><div className="metric-head"><span>Assigned patients</span></div><div className="metric-number">{data?data.assigned:'—'}</div><div className="metric-detail">Doctor-scoped · no cross-assignment leakage</div></div>
   <div className="metric-card"><div className="metric-head"><span>Matching filters</span></div><div className="metric-number">{data?data.total:'—'}</div><div className="metric-detail">{loading?'Searching…':'Server-side search, filters & sorting'}</div></div>
   <div className="metric-card"><div className="metric-head"><span>Data policy</span></div><div className="metric-number metric-name">Synthetic only</div><div className="metric-detail">Predictions only on supported historical twins</div></div>
  </div>
  <Panel title="Unified patient directory" subtitle="Historical twins and fictional registrations in one canonical view" action={<Pill tone="low"><ShieldCheck size={12}/>ALL SYNTHETIC</Pill>}>
   <div className="pgx-filters">
    <div className="pgx-search"><Search size={14}/><input aria-label="Search directory" placeholder="Search ID, name or city…" value={q} onChange={e=>setQ(e.target.value)}/></div>
    <select className="select-small" aria-label="City filter" value={city} onChange={e=>setCity(e.target.value)}><option value="">All cities</option>{cities.map(c=><option key={c}>{c}</option>)}</select>
    <select className="select-small" aria-label="Origin filter" value={origin} onChange={e=>setOrigin(e.target.value)}><option value="">All origins</option><option value="historical_twin">Historical twins</option><option value="manual_demo_registration">Demo registrations</option></select>
    <select className="select-small" aria-label="Model risk filter" value={risk} onChange={e=>setRisk(e.target.value)}><option value="">Any model state</option><option value="high">High72h risk</option><option value="elevated">Elevated72h risk</option><option value="low">Low72h risk</option><option value="unavailable">No prediction</option></select>
    <select className="select-small" aria-label="Sort directory" value={sort} onChange={e=>setSort(e.target.value as typeof sort)}><option value="name">Sort · name</option><option value="city">Sort · city</option><option value="risk">Sort ·72h risk</option><option value="updated">Sort · last observation</option></select>
   </div>
   {error&&<Notice tone="warning">{error}</Notice>}
   {loading&&!data?<Loading/>:<>
    <div className="table-scroll"><table className="pgx-table" aria-label="Patient directory"><thead><tr><th>Patient</th><th>Origin / status</th><th>72h model risk</th><th>Baseline</th><th>Care status</th><th>Last observation</th><th/></tr></thead>
     <tbody>{data?.items.map((p:DirectoryItem)=><tr key={p.patient_id}>
      <td><div className="patient-cell"><div className="patient-avatar">{(p.patient_id.match(/\d+/)?.[0]||'D').slice(0,3)}</div><div><strong>{p.display_name||p.patient_id}</strong><span>{p.patient_id} · {p.city} {p.age?`· ${p.age}y`:''}{p.sex?` · ${p.sex}`:''} <b className="synthetic-tag">SYNTHETIC</b></span></div></div></td>
      <td><Pill tone={p.origin==='historical_twin'?'low':'elevated'}>{p.origin==='historical_twin'?'Historical twin':'Fictional registration'}</Pill><br/><small className="muted-cell">{p.prediction_supported?'Prediction supported':'No frozen-model prediction'}</small></td>
      <td>{p.risk72==null?<Pill tone="neutral">— n/a</Pill>:<Pill tone={p.risk_category}>{pct(p.risk72)} · {p.risk_category}</Pill>}</td>
      <td><div className="baseline-mini"><span style={{width:`${Math.round(100*Math.min(72,p.baseline_hours)/72)}%`}}/></div><small>{number(p.baseline_hours,0)}/72h</small></td>
      <td><small className="muted-cell">{p.open_reviews} open reviews<br/>{p.open_notifications} open notifications<br/>Plan: {p.care_plan_status||'none'}</small></td>
      <td><small>{p.last_observation_at?time(p.last_observation_at,true):'None yet'}</small></td>
      <td><div className="pgx-inline"><button className="button secondary small-button" onClick={()=>onOpen(p.patient_id)}><ClipboardList size={13}/>Profile</button>{p.origin==='historical_twin'&&<button className="icon-button" aria-label={`Open twin ${p.patient_id}`} onClick={()=>onTwin(p.patient_id)}><ArrowRight size={14}/></button>}</div></td>
     </tr>)}</tbody></table></div>
    {data&&!data.items.length&&<Empty text="No synthetic patients match these filters."/>}
    {data&&<div className="table-footer"><span>{data.total?`${(page-1)*data.page_size+1}–${Math.min(page*data.page_size,data.total)}`:'0'} of {data.total} assigned synthetic patients</span><div className="pagination"><button className="icon-button" aria-label="Previous directory page" disabled={page<=1} onClick={()=>setPage(p=>p-1)}><ChevronLeft size={15}/></button><span>{page} / {maxPage}</span><button className="icon-button" aria-label="Next directory page" disabled={page>=maxPage} onClick={()=>setPage(p=>p+1)}><ChevronRight size={15}/></button></div></div>}
   </>}
   <p className="input-help">{data?.note}</p>
  </Panel>
  <Notice><Users size={14}/> Onboard fictional patients from the <strong>Onboarding &amp; registrations</strong> tab — one request-ID-protected form, persisted through the backend; new registrations never bypass the 72-hour baseline.</Notice>
 </div>;
}

type RegistryProps={revision:number;refresh:()=>void;notify:(s:string)=>void;selected:string;select:(s:string)=>void;openHistorical:(pid:string)=>void;openDevices:()=>void;openNotifications:()=>void};
export function PatientsSection({user,revision,refresh:_refresh,notify:_notify,onOpen,onTwin,registry}:{user:SessionUser;revision:number;refresh:()=>void;notify:(s:string)=>void;onOpen:(pid:string)=>void;onTwin:(pid:string)=>void;registry:React.ReactElement<RegistryProps>}){
 const [tab,setTab]=useState<'directory'|'onboarding'>('directory');
 return <><div className="segmented section-tabs"><button className={tab==='directory'?'selected':''} onClick={()=>setTab('directory')}>Patient directory</button><button className={tab==='onboarding'?'selected':''} onClick={()=>setTab('onboarding')}>Onboarding &amp; registrations</button></div>
 {tab==='directory'?<DirectoryPage user={user} revision={revision} onOpen={onOpen} onTwin={onTwin}/>:
  <div className="pgx">{registry}</div>}</>;
}
