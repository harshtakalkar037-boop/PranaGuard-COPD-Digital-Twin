import {useEffect,useMemo,useState} from 'react';
import {ArrowUpRight,ChevronLeft,ChevronRight,Search} from 'lucide-react';
import {Empty,Pill,number,pct,time} from './components';
import type {Patient} from './types';

type Sort='risk72'|'risk48'|'risk24'|'patient'|'city'|'recent';
/** Overview data comes directly from the original historical cohort API. */
export function CohortRegistry({patients,query,setQuery,onOpen,compact=false}:{patients:Patient[];query:string;setQuery:(q:string)=>void;onOpen:(id:string)=>void;compact?:boolean}){
 const [risk,setRisk]=useState('all'),[sort,setSort]=useState<Sort>('risk72'),[page,setPage]=useState(1);
 const pageSize=compact?6:10;
 const filtered=useMemo(()=>{
  const matches=patients.filter(p=>(risk==='all'||(risk==='unavailable'?!p.prediction_supported:p.prediction_supported&&p.risk_category===risk))&&`${p.display_name} ${p.patient_id} ${p.city}`.toLowerCase().includes(query.trim().toLowerCase()));
  return matches.sort((a,b)=>{
   if(sort==='patient')return a.patient_id.localeCompare(b.patient_id);
   if(sort==='city')return a.city.localeCompare(b.city)||a.patient_id.localeCompare(b.patient_id);
   if(sort==='recent')return b.timestamp.localeCompare(a.timestamp)||a.patient_id.localeCompare(b.patient_id);
   const horizon=sort.slice(4);const av=a.prediction_supported?a.risks[horizon]:undefined;const bv=b.prediction_supported?b.risks[horizon]:undefined;
   if(av===undefined)return bv===undefined?a.patient_id.localeCompare(b.patient_id):1;
   if(bv===undefined)return -1;
   return bv-av||a.patient_id.localeCompare(b.patient_id);
  });
 },[patients,query,risk,sort]);
 useEffect(()=>setPage(1),[query,risk,sort]);
 const maxPage=Math.max(1,Math.ceil(filtered.length/pageSize)),currentPage=Math.min(page,maxPage);
 return <div className="cohort-table">
  <div className="table-toolbar cohort-controls">
   <div className="searchbox"><Search size={15}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search by twin ID, name or city" aria-label="Search patients"/></div>
   <div className="cohort-filter"><span>72h risk category</span><div className="segmented">{['all','high','elevated','low','unavailable'].map(r=><button key={r} aria-pressed={risk===r} className={risk===r?'selected':''} onClick={()=>setRisk(r)}>{r==='all'?'All patients':r[0].toUpperCase()+r.slice(1)}</button>)}</div></div>
   <label className="cohort-sort">Sort by<select aria-label="Sort historical cohort" value={sort} onChange={e=>setSort(e.target.value as Sort)}><option value="risk72">72h risk · high to low</option><option value="risk48">48h risk · high to low</option><option value="risk24">24h risk · high to low</option><option value="patient">Patient ID</option><option value="city">City</option><option value="recent">Most recent state</option></select></label>
  </div>
  <div className="table-scroll"><table><thead><tr><th>Patient twin</th><th>24h risk</th><th>48h risk</th><th>72h model risk</th><th>SpO₂</th><th>Resp. rate</th><th>Ambient PM2.5</th><th>Last state (UTC)</th><th scope="col">Actions</th></tr></thead><tbody>{filtered.slice((currentPage-1)*pageSize,currentPage*pageSize).map(p=><tr key={p.patient_id} onClick={()=>onOpen(p.patient_id)}><td><div className="patient-cell"><div className="patient-avatar">{p.display_name.match(/\d+/)?.[0]}</div><div><strong>{p.display_name}</strong><span>{p.patient_id} · {p.city} <b className="synthetic-tag">SYNTHETIC</b></span></div></div></td><td>{p.prediction_supported?pct(p.risks['24']):'Unavailable'}</td><td>{p.prediction_supported?pct(p.risks['48']):'Unavailable'}</td><td>{p.prediction_supported?<Pill tone={p.risk_category}>{pct(p.risks['72'])} <span>· {p.risk_category}</span></Pill>:'Unavailable'}</td><td>{number(p.current.spo2)}<small> %</small></td><td>{number(p.current.resp_rate)}<small> /min</small></td><td>{number(p.current.pm25)}<small> μg/m³</small></td><td>{time(p.timestamp,true)}<small> · v{p.version}</small>{p.missing_fields.length>0&&<span className="missing-dot" title="Missing measurements">*</span>}</td><td><button className="icon-button" aria-label={`Open ${p.patient_id}`} onClick={e=>{e.stopPropagation();onOpen(p.patient_id)}}><ArrowUpRight size={15}/></button></td></tr>)}</tbody></table></div>
  {!filtered.length&&<Empty text="No synthetic patients match these filters."/>}
  <div className="table-footer"><span>{filtered.length?`${(currentPage-1)*pageSize+1}–${Math.min(currentPage*pageSize,filtered.length)}`:'0'} of {filtered.length} synthetic twins</span><div className="pagination"><button className="icon-button" aria-label="Previous page" disabled={currentPage<=1} onClick={()=>setPage(p=>p-1)}><ChevronLeft size={15}/></button><span>{currentPage} / {maxPage}</span><button className="icon-button" aria-label="Next page" disabled={currentPage>=maxPage} onClick={()=>setPage(p=>p+1)}><ChevronRight size={15}/></button></div></div>
 </div>;
}
