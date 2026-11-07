import {useEffect,useState} from 'react';
import {CheckCircle2,Droplets,History as HistoryIcon,Moon,Pencil,ShieldCheck} from 'lucide-react';
import {api,explainError,post,put} from '../api';
import {Empty,Loading,Notice,Panel,Pill,time} from '../components';
import type {Adherence,DailyLog,DailyLogPage,MedOption,SputumPage} from './types';

interface LogForm{entry_date:string;water_ml:string;food_notes:string;activity_minutes:string;sleep_hours:string;sleep_quality:string;wellbeing:string;notes:string}
const emptyForm:LogForm={entry_date:new Date().toISOString().slice(0,10),water_ml:'',food_notes:'',activity_minutes:'',sleep_hours:'',sleep_quality:'',wellbeing:'',notes:''};

function toPayload(f:LogForm){
 return {entry_date:f.entry_date,water_ml:f.water_ml===''?null:Number(f.water_ml),food_notes:f.food_notes,
  activity_minutes:f.activity_minutes===''?null:Number(f.activity_minutes),sleep_hours:f.sleep_hours===''?null:Number(f.sleep_hours),
  sleep_quality:f.sleep_quality||null,wellbeing:f.wellbeing||null,notes:f.notes};
}

export function PatientRecordsPage(){
 const [tab,setTab]=useState<'daily'|'sputum'|'medication'|'history'>('daily');
 const [logs,setLogs]=useState<DailyLogPage|null>(null);const [meds,setMeds]=useState<MedOption[]>([]);
 const [adh,setAdh]=useState<Adherence[]>([]);const [sputum,setSputum]=useState<SputumPage|null>(null);
 const [form,setForm]=useState<LogForm>(emptyForm);const [editing,setEditing]=useState<DailyLog|null>(null);
 const [busy,setBusy]=useState(false);const [msg,setMsg]=useState('');const [error,setError]=useState('');
 const [adhState,setAdhState]=useState<Record<number,{as_prescribed:boolean;missed_reason:string}>>({});
 const refresh=()=>{
  api<DailyLogPage>('/workspace/patient/daily-logs').then(setLogs).catch(e=>setError(explainError(e)));
  api<{medication_options:MedOption[]}>('/workspace/patient/medications').then(r=>{setMeds(r.medication_options);setAdhState(s=>{const n={...s};for(const m of r.medication_options)if(!(m.id in n))n[m.id]={as_prescribed:true,missed_reason:''};return n;});}).catch(e=>setError(explainError(e)));
  api<{items:Adherence[]}>('/workspace/patient/adherence').then(r=>setAdh(r.items)).catch(e=>setError(explainError(e)));
 };
 useEffect(()=>{refresh();
  // self sputum history via own patient id comes from home payload instead
  api<{patient_id:string}>('/workspace/patient/home').then(h=>api<SputumPage>(`/workspace/patients/${h.patient_id}/sputum`).then(setSputum).catch(()=>setSputum(null))).catch(()=>{});
 },[]);
 async function save(){
  setBusy(true);setError('');setMsg('');
  try{
   if(editing){await put<{id:number}>(`/workspace/patient/daily-logs/${editing.id}`,toPayload(form));setMsg('Correction saved — your original entry stays in the audit trail.');setEditing(null);}
   else{await post<{id:number}>('/workspace/patient/daily-logs',toPayload(form));setMsg('Daily log saved. Your doctor can review it in their Care Action Centre view.');}
   setForm(emptyForm);refresh();
  }catch(e){setError(explainError(e));}finally{setBusy(false);}
 }
 async function saveAdherence(id:number){
  const s=adhState[id];setBusy(true);setError('');setMsg('');
  try{await post<{id:number}>('/workspace/patient/adherence',{medication_id:id,as_prescribed:s.as_prescribed,taken_at:new Date().toISOString(),missed_reason:s.as_prescribed?null:s.missed_reason||null});
   setMsg('Medication report saved.');refresh();}catch(e){setError(explainError(e));}finally{setBusy(false);}
 }
 function startEdit(l:DailyLog){
  setEditing(l);setTab('daily');
  setForm({entry_date:l.entry_date,water_ml:l.water_ml==null?'':String(l.water_ml),food_notes:l.food_notes||'',
   activity_minutes:l.activity_minutes==null?'':String(l.activity_minutes),sleep_hours:l.sleep_hours==null?'':String(l.sleep_hours),
   sleep_quality:l.sleep_quality||'',wellbeing:l.wellbeing||'',notes:l.notes||''});
 }
 const setF=(k:keyof LogForm)=>(e:React.ChangeEvent<HTMLInputElement|HTMLSelectElement|HTMLTextAreaElement>)=>setForm(f=>({...f,[k]:e.target.value}));
 return <div className="pgx">
  <Notice>Synthetic demo records for <strong>your own twin only</strong>. Corrections keep the original in the audit trail. Nothing here changes medication — prescriptions come from your doctor.</Notice>
  <div className="segmented section-tabs">{([['daily','Daily log'],['sputum','Sputum diary'],['medication','Medication'],['history','History & trends']] as const).map(([k,l])=><button key={k} className={tab===k?'selected':''} onClick={()=>setTab(k)}>{l}</button>)}</div>
  {error&&<div className="error-banner" role="alert">{error}</div>}
  {msg&&<div className="notice info" role="status">{msg}</div>}
  {tab==='daily'&&<div className="two-col">
   <Panel title={editing?`Correct entry for ${editing.entry_date}`:'Log today'} subtitle="Wellbeing, hydration, sleep, activity — fictional demo data">
    <label className="field-label" htmlFor="dl-date">Date</label><input id="dl-date" className="form-input" type="date" value={form.entry_date} max={new Date().toISOString().slice(0,10)} onChange={setF('entry_date')} disabled={!!editing}/>
    <div className="context-grid" style={{margin:'10px 0'}}>
     <div><label className="field-label" htmlFor="dl-water">Water intake (ml)</label><input id="dl-water" className="form-input" type="number" min={0} max={12000} value={form.water_ml} onChange={setF('water_ml')} placeholder="e.g. 1800"/></div>
     <div><label className="field-label" htmlFor="dl-act">Activity / walking (min)</label><input id="dl-act" className="form-input" type="number" min={0} max={1440} value={form.activity_minutes} onChange={setF('activity_minutes')} placeholder="e.g. 20"/></div>
     <div><label className="field-label" htmlFor="dl-sleep">Sleep (hours)</label><input id="dl-sleep" className="form-input" type="number" step="0.5" min={0} max={24} value={form.sleep_hours} onChange={setF('sleep_hours')} placeholder="e.g. 7.5"/></div>
     <div><label className="field-label" htmlFor="dl-sleepq">Sleep quality</label><select id="dl-sleepq" className="form-select" value={form.sleep_quality} onChange={setF('sleep_quality')}><option value="">—</option><option value="good">good</option><option value="fair">fair</option><option value="poor">poor</option></select></div>
    </div>
    <label className="field-label" htmlFor="dl-well">General wellbeing</label><select id="dl-well" className="form-select" value={form.wellbeing} onChange={setF('wellbeing')}><option value="">—</option><option value="better">Better than usual</option><option value="same">About the same</option><option value="worse">Worse than usual</option></select>
    <label className="field-label" htmlFor="dl-food">Food & nutrition notes</label><textarea id="dl-food" rows={2} maxLength={1000} value={form.food_notes} onChange={setF('food_notes')} placeholder="What did you eat today? (demo)"/>
    <label className="field-label" htmlFor="dl-notes">Other symptoms / notes</label><textarea id="dl-notes" rows={2} maxLength={1500} value={form.notes} onChange={setF('notes')} placeholder="Anything else for your doctor to see? (demo)"/>
    <div className="pgx-inline">
     <button className="button primary" disabled={busy||!form.entry_date} onClick={save}><CheckCircle2 size={15}/>{editing?'Save correction':'Save daily log'}</button>
     {editing&&<button className="button subtle" onClick={()=>{setEditing(null);setForm(emptyForm);}}>Cancel</button>}
    </div>
    {editing&&<p className="input-help">Editing is allowed anytime, but the original submission and timestamps stay preserved in the demo audit trail.</p>}
   </Panel>
   <Panel title="Submitted daily records" subtitle="Newest first · shared with your assigned doctor">
    {!logs?<Loading/>:logs.items.length?<div className="care-queue">{logs.items.map(l=><div key={l.id} className="care-card">
     <div className="care-card-top"><strong>{l.entry_date}</strong><span className="pgx-inline">{l.edited?<Pill tone="amber">edited</Pill>:null}{l.reviewed_by?<Pill tone="low">✓ reviewed by {l.reviewed_by}</Pill>:<Pill>awaiting review</Pill>}</span></div>
     <p>{['Water: '+(l.water_ml!=null?`${l.water_ml} ml`:'—'),'Activity: '+(l.activity_minutes!=null?`${l.activity_minutes} min`:'—'),'Sleep: '+(l.sleep_hours!=null?`${l.sleep_hours} h`:'—'),'Wellbeing: '+(l.wellbeing||'—')].filter(x=>!x.endsWith('—')).join(' · ')||'No structured fields recorded'}</p>
     {l.notes&&<p className="care-note">{l.notes}</p>}
     <small>Submitted {time(l.created_at,true)}{l.review_note?` · doctor note: ${l.review_note}`:''}</small>
     <div className="pgx-inline"><button className="button secondary small-button" onClick={()=>startEdit(l)}><Pencil size={13}/>Correct this entry</button></div></div>)}</div>:<Empty text="No daily records yet."/>}
   </Panel></div>}
  {tab==='sputum'&&<SputumSelfLog/>}
  {tab==='medication'&&<div className="two-col">
   <Panel title="Today's medication" subtitle="Record whether you took each clinician-documented demo medication">
    {meds.length?<div className="care-queue">{meds.map(m=><div key={m.id} className="care-card">
     <div className="care-card-top"><strong>{m.name}</strong><Pill tone="neutral">{m.dose||'dose n/a'} · {m.frequency||'frequency n/a'}</Pill></div>
     <small>Documented by Dr. {m.added_by} · {time(m.created_at)}</small>
     <label className="field-label">Did you take it as documented?</label>
     <div className="pgx-inline">
      <label className="radio-label"><input type="radio" name={`adh-${m.id}`} checked={adhState[m.id]?.as_prescribed!==false} onChange={()=>setAdhState(s=>({...s,[m.id]:{...s[m.id],as_prescribed:true}}))}/> Taken as prescribed</label>
      <label className="radio-label"><input type="radio" name={`adh-${m.id}`} checked={adhState[m.id]?.as_prescribed===false} onChange={()=>setAdhState(s=>({...s,[m.id]:{...s[m.id],as_prescribed:false}}))}/> Missed / different</label>
     </div>
     {adhState[m.id]?.as_prescribed===false&&<><label className="field-label" htmlFor={`adh-note-${m.id}`}>Reason (required)</label><input id={`adh-note-${m.id}`} className="form-input" maxLength={300} value={adhState[m.id]?.missed_reason||''} onChange={e=>setAdhState(s=>({...s,[m.id]:{...s[m.id],missed_reason:e.target.value}}))}/></>}
     <button className="button primary small-button" disabled={busy||(adhState[m.id]?.as_prescribed===false&&!(adhState[m.id]?.missed_reason||'').trim())} onClick={()=>saveAdherence(m.id)}><CheckCircle2 size={14}/>Save report</button>
    </div>)}</div>:<Empty text="Your doctor has not documented any demo medication yet."/>}
    <p className="input-help">You cannot change prescriptions here — only report adherence. Medication names come from the doctor's documented demo list.</p>
   </Panel>
   <Panel title="Adherence history" subtitle="What you have reported">
    {adh.length?<ol className="care-timeline">{adh.map(a=><li key={a.id}><span className="status-dot"/><div><strong>{a.medication_name}</strong><small>{time(a.taken_at,true)}</small><p>{a.as_prescribed?'Taken as prescribed':`Missed — ${a.missed_reason||'no reason given'}`}{a.note?` · ${a.note}`:''}</p></div></li>)}</ol>:<Empty text="No adherence reports yet."/>}
   </Panel></div>}
  {tab==='history'&&<HistoryTab logs={logs} sputum={sputum}/>}
 </div>;
}

function HistoryTab({logs,sputum}:{logs:DailyLogPage|null;sputum:SputumPage|null}){
 return <div className="two-col">
  <Panel title="Trend of your wellbeing" subtitle="Structured values of your fictional daily records">
   {!logs?<Loading/>:logs.items.length?
    <div className="table-scroll"><table className="pgx-table"><thead><tr><th>Date</th><th><Droplets size={12}/> Water</th><th>Activity</th><th><Moon size={12}/> Sleep</th><th>Wellbeing</th><th>Reviewed</th></tr></thead><tbody>
     {logs.items.slice(0,14).map(l=><tr key={l.id}><td>{l.entry_date}</td><td>{l.water_ml??'—'} ml</td><td>{l.activity_minutes??'—'} min</td><td>{l.sleep_hours??'—'} h</td><td>{l.wellbeing??'—'}</td><td>{l.reviewed_by?<CheckCircle2 size={14}/>:'—'}</td></tr>)}</tbody></table></div>:<Empty text="Nothing logged yet."/>}
  </Panel>
  <Panel title="Sputum diary history" subtitle="Your own submissions with doctor review status">
   {!sputum?<Empty text="No sputum entries yet — use the Sputum diary tab to add one."/>:sputum.items.length?<ol className="care-timeline">{sputum.items.slice(0,10).map(s=><li key={s.id}><span className="status-dot"/><div><strong>{s.colour} · {s.volume} · {s.consistency}</strong><small>{time(s.occurred_at,true)}</small><p>cough {s.cough}/10 · breathlessness {s.breathlessness}/10 {s.note?`— ${s.note}`:''} {s.reviewed_by?`· reviewed by Dr. ${s.reviewed_by}`:''}</p></div></li>)}</ol>:<Empty text="No sputum entries yet."/>}
  </Panel></div>;
}

function SputumSelfLog(){
 // Self-service sputum entry for the linked patient; reuses the scoped /patients/{pid}/sputum endpoints with own id.
 const [mine,setMine]=useState('');const [form,setForm]=useState({colour:'clear',volume:'scant',consistency:'thin',cough:'3',breathlessness:'2',note:'',occurred_at:new Date().toISOString().slice(0,16)});
 const [file,setFile]=useState<File|null>(null);const [list,setList]=useState<SputumPage|null>(null);const [busy,setBusy]=useState(false);const [msg,setMsg]=useState('');const [error,setError]=useState('');
 useEffect(()=>{api<{patient_id:string}>('/workspace/patient/home').then(h=>setMine(h.patient_id)).catch(e=>setError(explainError(e)));},[]);
 useEffect(()=>{if(mine)api<SputumPage>(`/workspace/patients/${mine}/sputum`).then(setList).catch(e=>setError(explainError(e)));},[mine,msg]);
 async function save(){
  if(!mine)return;setBusy(true);setError('');setMsg('');
  try{
   let attachment:null|{filename:string;media_type:string;data_base64:string}=null;
   if(file){
    if(file.size>512*1024)throw new Error('Photo too large: 512 KB demo limit.');
    const buf=await file.arrayBuffer();let binary='';const bytes=new Uint8Array(buf);for(let i=0;i<bytes.length;i++)binary+=String.fromCharCode(bytes[i]);
    attachment={filename:file.name,media_type:file.type as 'image/png',data_base64:btoa(binary)};
   }
   await post<{id:number}>(`/workspace/patients/${mine}/sputum`,{occurred_at:new Date(form.occurred_at).toISOString(),colour:form.colour,volume:form.volume,consistency:form.consistency,cough:Number(form.cough),breathlessness:Number(form.breathlessness),note:form.note,attachment});
   setMsg('Sputum diary entry saved — your doctor sees it immediately.');
   setForm({...form,note:''});setFile(null);
  }catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}
 }
 const setF=(k:string)=>(e:React.ChangeEvent<HTMLInputElement|HTMLSelectElement|HTMLTextAreaElement>)=>setForm(f=>({...f,[k]:e.target.value}));
 return <div className="two-col">
  <Panel title="Add sputum diary entry" subtitle="Fictional COPD diary record — photos are documentation, not AI diagnosis">
   {error&&<div className="error-banner" role="alert">{error}</div>}{msg&&<div className="notice info" role="status">{msg}</div>}
   <label className="field-label" htmlFor="sp-when">When</label><input id="sp-when" className="form-input" type="datetime-local" value={form.occurred_at} onChange={setF('occurred_at')}/>
   <div className="context-grid" style={{margin:'10px 0'}}>
    <div><label className="field-label" htmlFor="sp-colour">Colour</label><select id="sp-colour" className="form-select" value={form.colour} onChange={setF('colour')}>{['clear','white','cream','yellow','green','rust','other'].map(c=><option key={c} value={c}>{c}</option>)}</select></div>
    <div><label className="field-label" htmlFor="sp-vol">Quantity</label><select id="sp-vol" className="form-select" value={form.volume} onChange={setF('volume')}>{['none','scant','moderate','large'].map(c=><option key={c} value={c}>{c}</option>)}</select></div>
    <div><label className="field-label" htmlFor="sp-cons">Consistency</label><select id="sp-cons" className="form-select" value={form.consistency} onChange={setF('consistency')}>{['thin','thick','sticky'].map(c=><option key={c} value={c}>{c}</option>)}</select></div>
    <div><label className="field-label" htmlFor="sp-cough">Cough (0–10)</label><input id="sp-cough" className="form-input" type="number" min={0} max={10} value={form.cough} onChange={setF('cough')}/></div>
    <div><label className="field-label" htmlFor="sp-breath">Breathlessness (0–10)</label><input id="sp-breath" className="form-input" type="number" min={0} max={10} value={form.breathlessness} onChange={setF('breathlessness')}/></div>
   </div>
   <label className="field-label" htmlFor="sp-note">Notes (optional)</label><textarea id="sp-note" rows={2} maxLength={1500} value={form.note} onChange={setF('note')}/>
   <label className="field-label" htmlFor="sp-photo">Photo attachment (optional record only)</label><input id="sp-photo" className="form-input" type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>setFile(e.target.files?.[0]||null)}/>
   <div className="pgx-inline"><button className="button primary" disabled={busy} onClick={save}><ShieldCheck size={15}/>Save diary entry</button></div>
  </Panel>
  <Panel title="Your sputum diary" subtitle="Doctor can flag entries as reviewed">
   {!list?<Loading/>:list.items.length?<div className="care-queue">{list.items.map(s=><div key={s.id} className="care-card">
    <div className="care-card-top"><strong>{s.colour} · {s.volume} · {s.consistency}</strong>{s.reviewed_by?<Pill tone="low">✓ reviewed by {s.reviewed_by}</Pill>:<Pill>awaiting review</Pill>}</div>
    <p>cough {s.cough}/10 · breathlessness {s.breathlessness}/10</p>{s.note&&<p className="care-note">{s.note}</p>}
    <small><HistoryIcon size={11}/> {time(s.occurred_at,true)}{s.attachment?` · photo ${s.attachment.filename} (${Math.round(s.attachment.size/1024)} KB)`:''}</small></div>)}</div>:<Empty text="No entries yet."/>}
  </Panel></div>;
}
