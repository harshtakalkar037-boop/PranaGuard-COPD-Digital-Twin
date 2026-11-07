import {useEffect,useMemo,useState} from 'react';
import {Bell,CalendarClock,CheckCircle2,ChevronLeft,ChevronRight,ClipboardCheck,ClipboardList,Plus,Search,Users} from 'lucide-react';
import {api,explainError} from '../api';
import {Empty,Loading,Notice,Panel,Pill,time} from '../components';
import type {CareReview,CareSummary,Directory,ReviewDetail} from './types';

const STATUSES=['','new','awaiting_review','under_review','follow_up_scheduled','completed','closed'] as const;
const ACTIONS:Record<string,string[]>={new:['awaiting_review','under_review','closed'],awaiting_review:['under_review','closed'],under_review:['follow_up_scheduled','completed','closed'],follow_up_scheduled:['under_review','completed','closed'],completed:['closed'],closed:[]};

export function CareCentrePage({revision,notify,openProfile}:{revision:number;notify:(s:string)=>void;openProfile:(pid:string)=>void}){
 const [summary,setSummary]=useState<CareSummary|null>(null);const [error,setError]=useState('');
 const [status,setStatus]=useState('');const [q,setQ]=useState('');const [page,setPage]=useState(1);
 const [reviews,setReviews]=useState<{items:CareReview[];total:number;page_size:number}|null>(null);
 const [selected,setSelected]=useState<number|null>(null);const [detail,setDetail]=useState<ReviewDetail|null>(null);
 const [savedKey,setSavedKey]=useState(0);
 useEffect(()=>{api<CareSummary>('/workspace/care/summary').then(setSummary).catch(e=>setError(explainError(e)));},[revision,savedKey]);
 useEffect(()=>{const p=new URLSearchParams();if(status)p.set('status',status);p.set('page',String(page));p.set('page_size','10');api<{items:CareReview[];total:number;page_size:number}>(`/workspace/care/reviews?${p}`).then(r=>setReviews(r)).catch(e=>setError(explainError(e)));},[status,page,revision,savedKey]);
 useEffect(()=>{if(selected!=null)api<ReviewDetail>(`/workspace/care/reviews/${selected}`).then(setDetail).catch(e=>setError(explainError(e)));},[selected,savedKey,revision]);
 const filtered=useMemo(()=>reviews?.items.filter(r=>!q||r.patient_id.toLowerCase().includes(q.toLowerCase())||r.note.toLowerCase().includes(q.toLowerCase()))||[],[reviews,q]);
 const refreshAll=(msg?:string)=>{setSavedKey(k=>k+1);if(msg)notify(msg);};
 const maxPage=reviews?Math.max(1,Math.ceil(reviews.total/reviews.page_size)):1;
 return <div className="pgx" data-testid="care-action-centre">
  {error&&<div className="error-banner" role="alert">{error}<button className="icon-button" onClick={()=>setError('')} aria-label="Dismiss error">×</button></div>}
  {!summary?<Loading/>:<div className="metric-grid six">
   {[{label:'Assigned patients',value:summary.assigned_patients,icon:<Users size={17}/>,tone:'teal'},
     {label:'Pending reviews',value:summary.pending_reviews,icon:<ClipboardList size={17}/>,tone:'amber'},
     {label:'In review',value:summary.reviews_in_progress,icon:<ClipboardCheck size={17}/>,tone:'blue'},
     {label:'Follow-ups due',value:summary.follow_ups_due,icon:<CalendarClock size={17}/>,tone:'coral'},
     {label:'Completed',value:summary.completed_reviews,icon:<CheckCircle2 size={17}/>,tone:'teal'},
     {label:'Open notifications',value:summary.open_notifications,icon:<Bell size={17}/>,tone:'blue'}
    ].map(m=><div className="metric-card" key={m.label}><div className="metric-head"><span>{m.label}</span><div className={`metric-icon ${m.tone}`}>{m.icon}</div></div><div className="metric-number">{m.value}</div><div className="metric-detail">Persisted SQLite counts</div></div>)}
  </div>}
  <div className="care-grid">
   <div className="care-left">
    <NewReview revision={revision} onSaved={id=>{refreshAll('Review saved and persisted.');setSelected(id);}}/>
    <Panel title="Review queue" subtitle="Search, filter and open a review; all states persist" action={<div className="pgx-inline">
      <div className="pgx-search"><Search size={13}/><input aria-label="Filter review queue" placeholder="Patient or note…" value={q} onChange={e=>setQ(e.target.value)}/></div>
      <select className="select-small" aria-label="Review status filter" value={status} onChange={e=>{setStatus(e.target.value);setPage(1);}}>{STATUSES.map(s=><option key={s} value={s}>{s?s.replaceAll('_',' '):'All statuses'}</option>)}</select></div>}>
     {!reviews?<Loading/>:<>
      <div className="care-queue">{filtered.map(r=><button key={r.id} className={`care-card ${selected===r.id?'selected':''}`} onClick={()=>setSelected(r.id)}>
       <div className="care-card-top"><strong>{r.patient_id}</strong><Pill tone={r.status==='completed'||r.status==='closed'?'low':r.status==='follow_up_scheduled'?'elevated':'amber'}>{r.status.replaceAll('_',' ')}</Pill></div>
       <p>{r.note.split('\n')[0].slice(0,120)}</p>
       <small>{time(r.updated_at,true)}{r.follow_up_at?` · follow-up ${time(r.follow_up_at)}`:''} · {r.doctor}</small></button>)}
      </div>
      {!filtered.length&&<Empty text="No reviews match. Create one from the form above."/>}
      <div className="table-footer"><span>{reviews.total} persisted reviews</span><div className="pagination"><button className="icon-button" aria-label="Previous reviews page" disabled={page<=1} onClick={()=>setPage(p=>p-1)}><ChevronLeft size={14}/></button><span>{page} / {maxPage}</span><button className="icon-button" aria-label="Next reviews page" disabled={page>=maxPage} onClick={()=>setPage(p=>p+1)}><ChevronRight size={14}/></button></div></div>
     </>}
    </Panel>
   </div>
   <div className="care-right">
    {selected==null?<Panel title="Review workspace"><Empty text="Select a review from the queue (or create one) to open its workspace."/></Panel>:
     detail==null?<Panel title="Review workspace"><Loading/></Panel>:<ReviewWorkspace detail={detail} openProfile={openProfile} onSaved={refreshAll}/>}
   </div>
  </div>
 </div>;
}

function NewReview({revision,onSaved}:{revision:number;onSaved:(id:number)=>void}){
 const [patients,setPatients]=useState<Directory|null>(null);const [pid,setPid]=useState('');const [note,setNote]=useState('');const [follow,setFollow]=useState('');const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [open,setOpen]=useState(false);
 useEffect(()=>{api<Directory>('/workspace/patients?page_size=50').then(setPatients).catch(()=>setPatients(null));},[revision]);
 useEffect(()=>{if(patients&&!pid&&patients.items.length)setPid(patients.items[0].patient_id);},[patients,pid]);
 async function save(){setBusy(true);setError('');try{const r=await api<{review:CareReview}>('/workspace/care/reviews',{method:'POST',body:JSON.stringify({patient_id:pid,note,follow_up_at:follow?new Date(follow).toISOString():null})});setNote('');setFollow('');setOpen(false);onSaved(r.review.id);}catch(e){setError(explainError(e));}finally{setBusy(false);}}
 if(!open)return <button className="button primary w-full" onClick={()=>setOpen(true)}><Plus size={15}/> Start a new care review</button>;
 return <Panel title="New care review" subtitle="Documentation only — never a clinical action" className="care-new">
  {!patients||!patients.items.length?<Empty text="No patients are assigned to this demo account."/>:<>
  <label className="field-label" htmlFor="review-patient">Assigned patient</label>
  <select id="review-patient" className="form-select" value={pid} onChange={e=>setPid(e.target.value)}>{patients.items.map(p=><option key={p.patient_id} value={p.patient_id}>{p.patient_id} · {p.display_name}</option>)}</select>
  <label className="field-label" htmlFor="review-note">Review note</label>
  <textarea id="review-note" rows={3} value={note} onChange={e=>setNote(e.target.value)} placeholder="Document the demo review…" maxLength={2000}/>
  <label className="field-label" htmlFor="review-follow">Optional follow-up (sets status to follow-up scheduled)</label>
  <input id="review-follow" type="datetime-local" className="form-input" value={follow} onChange={e=>setFollow(e.target.value)}/>
  {error&&<Notice tone="warning">{error}</Notice>}
  <div className="pgx-inline" style={{marginTop:10}}><button className="button primary" disabled={busy||note.trim().length<3} onClick={save}>{busy?'Saving…':'Save review'}</button><button className="button subtle" onClick={()=>setOpen(false)}>Cancel</button></div></>}
 </Panel>;
}

function ReviewWorkspace({detail,openProfile,onSaved}:{detail:ReviewDetail;openProfile:(pid:string)=>void;onSaved:(msg?:string)=>void}){
 const r=detail.review;const [note,setNote]=useState('');const [follow,setFollow]=useState('');const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 async function move(status:string){setBusy(true);setError('');try{await api(`/workspace/care/reviews/${r.id}`,{method:'PATCH',body:JSON.stringify({status,note:note||undefined,follow_up_at:follow?new Date(follow).toISOString():undefined})});setNote('');setFollow('');onSaved(`Review ${status.replaceAll('_',' ')}.`);}catch(e){setError(explainError(e));}finally{setBusy(false);}}
 async function completeFollowup(){setBusy(true);setError('');try{await api(`/workspace/care/reviews/${r.id}/complete-follow-up`,{method:'POST',body:JSON.stringify({note})});setNote('');onSaved('Follow-up completion recorded.');}catch(e){setError(explainError(e));}finally{setBusy(false);}}
 return <Panel title={`Review #${r.id} · ${r.patient_id}`} subtitle={`Saved at twin/state version ${r.state_version} · owner ${r.doctor}`} action={<Pill tone={r.status==='completed'||r.status==='closed'?'low':'amber'}>{r.status.replaceAll('_',' ')}</Pill>}>
  <div className="pgx-inline"><button className="text-link" onClick={()=>openProfile(r.patient_id)}>Open patient profile</button></div>
  <p className="care-note">{r.note.split('\n')[0]}</p>
  {r.follow_up_at&&<p className="input-help">Follow-up scheduled: {time(r.follow_up_at,true)}</p>}
  {ACTIONS[r.status]?.length?<>
   <label className="field-label" htmlFor="rw-note">Add note (optional)</label>
   <textarea id="rw-note" rows={2} value={note} onChange={e=>setNote(e.target.value)} maxLength={2000}/>
   <label className="field-label" htmlFor="rw-follow">Follow-up date (required to schedule)</label>
   <input id="rw-follow" type="datetime-local" className="form-input" value={follow} onChange={e=>setFollow(e.target.value)}/>
   {error&&<Notice tone="warning">{error}</Notice>}
   <div className="pgx-inline">{ACTIONS[r.status].map(s=><button key={s} className="button secondary small-button" disabled={busy} onClick={()=>move(s)}>{s.replaceAll('_',' ')}</button>)}</div>
   {r.status==='follow_up_scheduled'&&<button className="button primary small-button" disabled={busy} onClick={completeFollowup}>Record follow-up completed</button>}
  </>:<Notice tone="info">This review is {r.status.replaceAll('_',' ')}; the workflow keeps closed records immutable.</Notice>}
  <h4 className="subheading">Timeline</h4>
  <ol className="care-timeline">{detail.timeline.map(e=><li key={e.id}><span className="status-dot"/><div><strong>{e.event}</strong><small>{time(e.created_at,true)} · {e.actor}</small>{e.note&&<p>{e.note}</p>}</div></li>)}</ol>
 </Panel>;
}
