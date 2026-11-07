import {useEffect,useState} from 'react';
import {CalendarClock,CheckCircle2,HeartPulse,Pencil,ShieldCheck} from 'lucide-react';
import {CartesianGrid,Line,LineChart,ResponsiveContainer,Tooltip,XAxis,YAxis} from 'recharts';
import {api,explainError,patch,post,put} from '../api';
import {Empty,Loading,Notice,Panel,Pill,number,pct,time} from '../components';
import type {Activity,CarePlan,PlanResponse,Profile,SputumPage} from './types';

const TABS=['Overview','Sputum diary','Care plan','Activity & adherence','Reviews & notifications'] as const;

export function ProfilePage({pid,revision,notify,openTwin}:{pid:string;revision:number;notify:(s:string)=>void;openTwin:(pid:string)=>void}){
 const [tab,setTab]=useState<typeof TABS[number]>('Overview');
 const [data,setData]=useState<Profile|null>(null);const [error,setError]=useState('');const [savedKey,setSavedKey]=useState(0);
 useEffect(()=>{setData(null);setTab('Overview');},[pid]);
 useEffect(()=>{api<Profile>(`/workspace/patients/${pid}`).then(d=>{setData(d);setError('');}).catch(e=>setError(explainError(e)));},[pid,revision,savedKey]);
 const refresh=(msg?:string)=>{setSavedKey(k=>k+1);if(msg)notify(msg);};
 if(error)return <Notice tone="warning">{error}</Notice>;
 if(!data)return <Loading/>;
 const p=data.profile as {display_name?:string;age?:number;sex?:string;city?:string};
 return <div className="pgx" data-testid="patient-profile">
  <div className="twin-banner"><div className="large-avatar"><HeartPulse size={25}/></div>
   <div><div className="twin-name"><h2>{p.display_name||pid}</h2><Pill>SYNTHETIC PATIENT</Pill></div>
   <p>{pid} <b>·</b> {p.age} years <b>·</b> {p.sex} <b>·</b> {p.city} <b>·</b> {data.origin.replaceAll('_',' ')}</p></div>
   <div className="twin-banner-right">{data.model_state?<Pill tone={data.model_state.risk_category}>{pct(data.model_state.risks['72'])} · {data.model_state.risk_category}72h</Pill>:<Pill tone="elevated">No prediction — baseline {number(data.baseline.observed_hours,0)}/72h</Pill>}
    <span>{data.model_state?`State v${data.model_state.version} · ${time(data.model_state.timestamp,true)}`:'Fictional registration · model boundary enforced'}</span>
    {data.model_state&&<button className="button secondary small-button" onClick={()=>openTwin(pid)}>Open digital twin</button>}</div></div>
  <Notice>{data.caution}</Notice>
  <div className="segmented section-tabs">{TABS.map(t=><button key={t} className={tab===t?'selected':''} onClick={()=>setTab(t)}>{t}</button>)}</div>
  {tab==='Overview'&&<OverviewTab data={data}/>}
  {tab==='Sputum diary'&&<DiaryTab pid={pid} refresh={refresh} revision={revision}/>}
  {tab==='Care plan'&&<PlanTab pid={pid} refresh={refresh}/>}
  {tab==='Activity & adherence'&&<ActivityTab pid={pid} revision={revision}/>}
  {tab==='Reviews & notifications'&&<div className="two-col">
   <Panel title="Care review history" subtitle="Persisted workspace reviews">{data.reviews.length?<ol className="care-timeline">{data.reviews.map(r=><li key={r.id}><span className="status-dot"/><div><strong>{r.status.replaceAll('_',' ')}</strong><small>{time(r.updated_at,true)} · {r.doctor}</small><p>{r.note.split('\n')[0]}</p></div></li>)}</ol>:<Empty text="No care reviews for this patient yet."/>}</Panel>
   <Panel title="Notification history" subtitle="Actual persisted notification records">{data.notifications.notifications.length?<div className="care-queue">{data.notifications.notifications.map(n=><div key={n.id} className="care-card"><div className="care-card-top"><strong>{n.title}</strong><Pill tone={n.status==='resolved'||n.status==='closed'?'low':'amber'}>{n.status.replaceAll('_',' ')}</Pill></div><small>{time(n.created_at,true)}</small></div>)}</div>:<Empty text="No notifications for this synthetic patient."/>}</Panel>
  </div>}
 </div>;
}

function OverviewTab({data}:{data:Profile}){
 return <><div className="two-col">
  <Panel title="Identity & clinical attributes" subtitle="Synthetic cohort attributes or fictional registration fields — never a real record">
   <div className="context-grid">{Object.entries(data.profile).filter(([k])=>!['display_name','patient_id','environment_source'].includes(k)).map(([k,v])=><div key={k}><span>{k.replaceAll('_',' ')}</span><strong>{String(v)}</strong></div>)}</div>
   <p className="input-help">{String(data.details.copd_history||'')} {String(data.details.diagnosis_info||'')}</p></Panel>
  <Panel title="Model boundary" subtitle="Frozen research models never ingest monitoring data">
   {data.model_state?<><div className="context-grid"><div><span>24h risk</span><strong>{pct(data.model_state.risks['24'])}</strong></div><div><span>48h risk (v1 stored)</span><strong>{pct(data.model_state.risks['48'])}</strong></div><div><span>72h risk</span><strong>{pct(data.model_state.risks['72'])}</strong></div><div><span>Prediction supported</span><strong>{data.model_state.prediction_supported?'yes':'no'}</strong></div></div>
   <p className="input-help">Frozen {data.model_state.model_version} · separate v3 48h lives on the twin page. Model quality is weak at 72h — see validation.</p></>
   :<><div className="baseline-mini large"><span style={{width:`${Math.round(100*Math.min(72,data.baseline.observed_hours)/72)}%`}}/></div><p className="input-help">{data.baseline.notice}</p></>}
  </Panel></div>
  <Panel title="Recent manual monitoring entries" subtitle="Fictional hand-entered observations (demo)">
   {data.observations.length?<div className="table-scroll"><table className="pgx-table"><thead><tr><th>Recorded</th><th>Symptom score</th><th>Adherence</th><th>Note</th></tr></thead><tbody>{data.observations.slice(0,8).map(o=><tr key={o.id}><td>{time(o.created_at,true)}</td><td>{o.symptom_score}/10</td><td>{pct(o.adherence,0)}</td><td>{o.note||'—'}</td></tr>)}</tbody></table></div>:<Empty text="No manual monitoring entries recorded yet."/>}
  </Panel></>;
}

function DiaryTab({pid,refresh,revision}:{pid:string;refresh:(m?:string)=>void;revision:number}){
 const [page,setPage]=useState(1);const [data,setData]=useState<SputumPage|null>(null);const [error,setError]=useState('');
 const [form,setForm]=useState({colour:'clear',volume:'scant',consistency:'thin',cough:'3',breathlessness:'2',note:'',occurred_at:new Date().toISOString().slice(0,16)});
 const [file,setFile]=useState<File|null>(null);const [busy,setBusy]=useState(false);const [reviewNote,setReviewNote]=useState<Record<number,string>>({});
 useEffect(()=>{api<SputumPage>(`/workspace/patients/${pid}/sputum?page=${page}`).then(setData).catch(e=>setError(explainError(e)));},[pid,page,revision]);
 async function save(){
  setBusy(true);setError('');
  try{
   let attachment=null;
   if(file){
    if(file.size>512*1024){setError('Attachment exceeds the 512 KB demo limit.');setBusy(false);return;}
    attachment={filename:file.name,media_type:file.type,data_base64:await toBase64(file)};
   }
   await post(`/workspace/patients/${pid}/sputum`,{...form,cough:+form.cough,breathlessness:+form.breathlessness,occurred_at:new Date(form.occurred_at).toISOString(),attachment});
   setFile(null);setForm({...form,note:''});refresh('Diary entry saved and visible below.');
   const d=await api<SputumPage>(`/workspace/patients/${pid}/sputum?page=1`);setData(d);
  }catch(e){setError(explainError(e));}finally{setBusy(false);}
 }
 return <div className="care-grid"><Panel title="Log diary entry" subtitle="Patient-reported fictional record · photo optional, documentation only" className="care-new">
  <label className="field-label" htmlFor="d-time">Date & time</label><input id="d-time" type="datetime-local" className="form-input" value={form.occurred_at} max={new Date().toISOString().slice(0,16)} onChange={e=>setForm({...form,occurred_at:e.target.value})}/>
  <div className="pgx-form-grid"><div className="pgx-field"><label className="field-label" htmlFor="d-colour">Colour</label><select id="d-colour" className="form-select" value={form.colour} onChange={e=>setForm({...form,colour:e.target.value})}>{['clear','white','cream','yellow','green','rust','other'].map(v=><option key={v}>{v}</option>)}</select></div>
  <div className="pgx-field"><label className="field-label" htmlFor="d-volume">Volume</label><select id="d-volume" className="form-select" value={form.volume} onChange={e=>setForm({...form,volume:e.target.value})}>{['none','scant','moderate','large'].map(v=><option key={v}>{v}</option>)}</select></div>
  <div className="pgx-field"><label className="field-label" htmlFor="d-consistency">Consistency</label><select id="d-consistency" className="form-select" value={form.consistency} onChange={e=>setForm({...form,consistency:e.target.value})}>{['thin','thick','sticky'].map(v=><option key={v}>{v}</option>)}</select></div></div>
  <div className="pgx-form-grid"><div className="pgx-field"><label className="field-label" htmlFor="d-cough">Cough (0–10)</label><input id="d-cough" type="number" min={0} max={10} className="form-input" value={form.cough} onChange={e=>setForm({...form,cough:e.target.value})}/></div>
  <div className="pgx-field"><label className="field-label" htmlFor="d-breath">Breathlessness (0–10)</label><input id="d-breath" type="number" min={0} max={10} className="form-input" value={form.breathlessness} onChange={e=>setForm({...form,breathlessness:e.target.value})}/></div></div>
  <label className="field-label" htmlFor="d-note">Notes</label><textarea id="d-note" rows={2} maxLength={1500} value={form.note} onChange={e=>setForm({...form,note:e.target.value})}/>
  <label className="field-label" htmlFor="d-photo">Optional photo (PNG/JPEG/WebP ≤512KB)</label><input id="d-photo" type="file" accept="image/png,image/jpeg,image/webp" className="form-input" onChange={e=>setFile(e.target.files?.[0]||null)}/>
  {error&&<Notice tone="warning">{error}</Notice>}
  <button className="button primary w-full" disabled={busy} onClick={save}>{busy?'Saving…':'Save diary entry'}</button>
  <p className="input-help">Photographs are stored as documentation metadata only. This demo never diagnoses infection or determines treatment from images.</p>
 </Panel>
 <Panel title="Diary history" subtitle={data?.notice||''}>
  {error&&<Notice tone="warning">{error}</Notice>}
  {!data?<Loading/>:<>
   <div className="care-queue">{data.items.map(e=><div key={e.id} className="care-card">
    <div className="care-card-top"><strong>{time(e.occurred_at,true)}</strong><Pill tone={e.reviewed_at?'low':'amber'}>{e.reviewed_at?'reviewed':'awaiting clinician note'}</Pill></div>
    <p>{e.colour} · {e.volume} · {e.consistency} — cough {e.cough}/10, breathlessness {e.breathlessness}/10{e.note?` — ${e.note}`:''}</p>
    {e.attachment&&<div className="diary-attachment"><img src={`/api/workspace/attachments/${e.attachment.id}`} alt={`Diary attachment ${e.attachment.filename}`}/><small>{e.attachment.filename} · {Math.round(e.attachment.size/1024)}KB · sha256 {e.attachment.sha256.slice(0,12)}…</small></div>}
    {e.reviewed_at?<small className="muted-cell">Reviewed by {e.reviewed_by} · {time(e.reviewed_at,true)}<br/>{e.review_note}</small>:
     <div className="pgx-inline"><input className="form-input diary-review-input" aria-label={`Review note for entry ${e.id}`} placeholder="Clinician review note (min 3 chars)" value={reviewNote[e.id]||''} onChange={ev=>setReviewNote({...reviewNote,[e.id]:ev.target.value})}/>
     <button className="button secondary small-button" disabled={(reviewNote[e.id]||'').trim().length<3} onClick={async()=>{try{await patch(`/workspace/sputum/${e.id}/review`,{note:reviewNote[e.id]});refresh('Review note saved.');const d=await api<SputumPage>(`/workspace/patients/${pid}/sputum?page=${page}`);setData(d);}catch(err){setError(explainError(err));}}}><CheckCircle2 size={13}/>Mark reviewed</button></div>}
   </div>)}</div>
   {!data.items.length&&<Empty text="No diary entries yet — the first one will appear here after saving."/>}
   <div className="table-footer"><span>{data.total} entries</span><div className="pagination"><button className="icon-button" aria-label="Previous diary page" disabled={page<=1} onClick={()=>setPage(p=>p-1)}>‹</button><span>{page}</span><button className="icon-button" aria-label="Next diary page" disabled={!data||(page*data.page_size)>=data.total} onClick={()=>setPage(p=>p+1)}>›</button></div></div>
  </>}
 </Panel></div>;
}

function toBase64(file:File):Promise<string>{return new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(String(r.result).split(',')[1]);r.onerror=reject;r.readAsDataURL(file);});}

function PlanTab({pid,refresh}:{pid:string;refresh:(m?:string)=>void}){
 const [data,setData]=useState<PlanResponse|null>(null);const [error,setError]=useState('');const [busy,setBusy]=useState(false);const [editing,setEditing]=useState(false);
 const [form,setForm]=useState({goals:'',activity_guidance:'',adherence_support:'',environment_notes:'',review_date:'',status:'draft',change_note:''});
 useEffect(()=>{api<PlanResponse>(`/workspace/patients/${pid}/plan`).then(d=>{setData(d);if(d.plan)setForm({goals:d.plan.goals,activity_guidance:d.plan.activity_guidance,adherence_support:d.plan.adherence_support,environment_notes:d.plan.environment_notes,review_date:d.plan.review_date||'',status:d.plan.status,change_note:''});}).catch(e=>setError(explainError(e)));},[pid,refresh===undefined]);
 useEffect(()=>{api<PlanResponse>(`/workspace/patients/${pid}/plan`).then(setData).catch(()=>{});},[pid]);
 async function save(){setBusy(true);setError('');try{const r=await put<{plan:CarePlan}> (`/workspace/patients/${pid}/plan`,form);setData(d=>({...d!,plan:r.plan,revisions:d?.revisions||[],notice:''}));setEditing(false);refresh('Care plan documentation saved.');
  const fresh=await api<PlanResponse>(`/workspace/patients/${pid}/plan`);setData(fresh);}catch(e){setError(explainError(e));}finally{setBusy(false);}}
 if(!data)return <Loading/>;
 return <div className="care-grid"><Panel title="Care-plan documentation" subtitle={data.notice} action={!editing&&<button className="button secondary small-button" onClick={()=>setEditing(true)}><Pencil size={13}/>{data.plan?'Edit plan':'Create plan'}</button>}>
  {editing?<>
   <label className="field-label" htmlFor="plan-goals">Documented goals</label><textarea id="plan-goals" rows={3} value={form.goals} maxLength={3000} onChange={e=>setForm({...form,goals:e.target.value})} placeholder="e.g. Daily walk as tolerated; review inhaler technique at next visit (documentation, not instructions)"/>
   <label className="field-label" htmlFor="plan-activity">Activity guidance (documentation)</label><textarea id="plan-activity" rows={2} value={form.activity_guidance} maxLength={2000} onChange={e=>setForm({...form,activity_guidance:e.target.value})}/>
   <label className="field-label" htmlFor="plan-adherence">Adherence support notes</label><textarea id="plan-adherence" rows={2} value={form.adherence_support} maxLength={2000} onChange={e=>setForm({...form,adherence_support:e.target.value})}/>
   <label className="field-label" htmlFor="plan-env">Environment notes</label><textarea id="plan-env" rows={2} value={form.environment_notes} maxLength={2000} onChange={e=>setForm({...form,environment_notes:e.target.value})}/>
   <div className="pgx-form-grid"><div className="pgx-field"><label className="field-label" htmlFor="plan-date">Review date</label><input id="plan-date" type="date" className="form-input" value={form.review_date} min={new Date().toISOString().slice(0,10)} onChange={e=>setForm({...form,review_date:e.target.value})}/></div>
   <div className="pgx-field"><label className="field-label" htmlFor="plan-status">Status</label><select id="plan-status" className="form-select" value={form.status} onChange={e=>setForm({...form,status:e.target.value})}>{['draft','active','completed','cancelled'].map(s=><option key={s}>{s}</option>)}</select></div></div>
   <label className="field-label" htmlFor="plan-change">Change note (stored in revision history)</label><input id="plan-change" className="form-input" value={form.change_note} maxLength={500} onChange={e=>setForm({...form,change_note:e.target.value})}/>
   {error&&<Notice tone="warning">{error}</Notice>}
   <div className="pgx-inline" style={{marginTop:10}}><button className="button primary" disabled={busy||form.goals.trim().length<3} onClick={save}>{busy?'Saving…':'Save plan'}</button><button className="button subtle" onClick={()=>setEditing(false)}>Cancel</button></div>
  </>:data.plan?<><div className="pgx-inline"><Pill tone={data.plan.status==='active'?'low':'elevated'}>{data.plan.status}</Pill>{data.plan.review_date&&<small><CalendarClock size={12}/> review {data.plan.review_date}</small>}</div>
   <dl className="pgx-definition"><dt>Goals</dt><dd>{data.plan.goals}</dd>{data.plan.activity_guidance&&<><dt>Activity guidance</dt><dd>{data.plan.activity_guidance}</dd></>}{data.plan.adherence_support&&<><dt>Adherence support</dt><dd>{data.plan.adherence_support}</dd></>}{data.plan.environment_notes&&<><dt>Environment</dt><dd>{data.plan.environment_notes}</dd></>}<dt>Saved</dt><dd>{time(data.plan.updated_at,true)} by {data.plan.doctor}</dd></dl></>:<Empty text="No care-plan documentation yet."/>}
 </Panel>
 <Panel title="Revision history" subtitle="Previous saved versions are kept, never overwritten silently">
  {data.revisions.length?<ol className="care-timeline">{data.revisions.map(r=><li key={r.id}><span className="status-dot"/><div><strong>Revision #{r.id}</strong><small>{time(r.created_at,true)} · {r.actor}</small><p>{r.change_note||'Update'}</p></div></li>)}</ol>:<Empty text="No revisions yet."/>}
  <p className="input-help"><ShieldCheck size={12}/> This demo documents plans only. It never prescribes medication or treatment.</p>
 </Panel></div>;
}

function ActivityTab({pid,revision}:{pid:string;revision:number}){
 const [data,setData]=useState<Activity|null>(null);const [error,setError]=useState('');
 useEffect(()=>{api<Activity>(`/workspace/patients/${pid}/activity`).then(d=>setData(d)).catch(e=>setError(explainError(e)));},[pid,revision]);
 if(error)return <Notice tone="warning">{error}</Notice>;
 if(!data)return <Loading/>;
 const adherence=data.series.filter(d=>d.adherence_manual!==undefined);const steps=data.series.filter(d=>d.steps_simulated_device!==undefined||d.heart_rate_simulated_device!==undefined);
 return <><Notice>{data.missing} Sources: {data.sources}.</Notice>
 <div className="two-col">
  <Panel title="Adherence & symptoms" subtitle={`${data.manual_entries} hand-entered fictional observations`}>
   {adherence.length?<div style={{height:230}}><ResponsiveContainer width="100%" height="100%"><LineChart data={adherence}><CartesianGrid strokeDasharray="3 4" vertical={false} stroke="#eaf0ed"/><XAxis dataKey="date" tick={{fontSize:10}}/><YAxis tick={{fontSize:10}} width={30}/><Tooltip/><Line type="monotone" dataKey="adherence_manual" name="Adherence (0–1)" stroke="#1c7569" strokeWidth={2} dot/><Line type="monotone" dataKey="symptom_manual" name="Symptom score (0–10)" stroke="#d3a15b" strokeWidth={2} dot/></LineChart></ResponsiveContainer></div>:<Empty text="No manual observation entries for this patient yet."/>}
  </Panel>
  <Panel title="Simulated device activity" subtitle={`${data.device_samples} validated ingestion samples`}>
   {steps.length?<div style={{height:230}}><ResponsiveContainer width="100%" height="100%"><LineChart data={steps}><CartesianGrid strokeDasharray="3 4" vertical={false} stroke="#eaf0ed"/><XAxis dataKey="date" tick={{fontSize:10}}/><YAxis tick={{fontSize:10}} width={30}/><Tooltip/><Line type="monotone" dataKey="steps_simulated_device" name="Steps (simulated)" stroke="#247e6d" strokeWidth={2} dot={false}/><Line type="monotone" dataKey="heart_rate_simulated_device" name="Heart rate (simulated)" stroke="#c67c66" strokeWidth={1.5} dot={false}/></LineChart></ResponsiveContainer></div>:<Empty text="No simulated device readings yet — associate and start a device from Onboarding & registrations."/>}
  </Panel>
 </div>
 <Panel title="Latest monitoring snapshot" subtitle="Persisted backend monitoring state version">
  {data.latest_monitoring?<pre className="hash-code snapshot-pre">{JSON.stringify(data.latest_monitoring,null,2)}</pre>:<Empty text="No persisted monitoring snapshots yet."/>}
 </Panel></>;
}
