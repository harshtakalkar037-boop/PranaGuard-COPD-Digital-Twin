import {CalendarClock,CheckCircle2,ClipboardList,FileText,HeartPulse,ShieldCheck} from 'lucide-react';
import {explainError} from '../api';
import {useRemote} from '../hooks';
import {Empty,Loading,Notice,Panel,Pill,time} from '../components';
import type {PatientHome as Home} from './types';

export function PatientHomePage({navigate}:{navigate:(v:'patient-home'|'patient-records'|'patient-docs')=>void}){
 const {data,error}=useRemote<Home>('/workspace/patient/home',0);
 if(error)return <Notice tone="warning">{explainError(error)}</Notice>;
 if(!data)return <Loading label="Loading your demo health home…"/>;
 const p=data.profile as {display_name?:string;age?:number;sex?:string;city?:string};
 return <div className="pgx">
  <div className="twin-banner"><div className="large-avatar"><HeartPulse size={25}/></div>
   <div><div className="twin-name"><h2>Hello, {p.display_name||'demo patient'}</h2><Pill>SYNTHETIC DEMO</Pill></div>
   <p>{data.patient_id} {p.age?`· ${p.age} years`:''} {p.city?`· ${p.city}`:''} · Shared with your assigned doctor (demo)</p></div>
   <div className="twin-banner-right">{data.logged_today?<Pill tone="low">Today's log saved</Pill>:<Pill tone="amber">Today's log not saved yet</Pill>}
    <span>{data.streak_days} day{data.streak_days===1?'':'s'} in a row</span></div></div>
  <Notice>{data.note}</Notice>
  <div className="metric-grid four">
   <button className="metric-card as-button" onClick={()=>navigate('patient-records')} aria-label="Add today's health record"><div className="metric-head"><span>Daily log</span><div className="metric-icon teal"><ClipboardList size={17}/></div></div><div className="metric-number">{data.logged_today?'Saved ✓':'Add today'}</div><div className="metric-detail">Sputum, wellbeing, sleep, hydration, medication</div></button>
   <button className="metric-card as-button" onClick={()=>navigate('patient-docs')} aria-label="Open clinical documents"><div className="metric-head"><span>Documents</span><div className="metric-icon blue"><FileText size={17}/></div></div><div className="metric-number">{data.documents_count}</div><div className="metric-detail">Shared by your doctor · prescriptions and records</div></button>
   <div className="metric-card"><div className="metric-head"><span>Care plan</span><div className="metric-icon amber"><ShieldCheck size={17}/></div></div><div className="metric-number">{data.care_plan?data.care_plan.status:'None yet'}</div><div className="metric-detail">{data.care_plan?`Updated ${time(data.care_plan.updated_at,true)} by ${data.care_plan.doctor}`:'Your doctor has not added a demo care plan yet'}</div></div>
   <div className="metric-card"><div className="metric-head"><span>Reviewed</span><div className="metric-icon coral"><CheckCircle2 size={17}/></div></div><div className="metric-number">{data.latest_review.reviewed?'Yes':'Not yet'}</div><div className="metric-detail">{data.latest_review.reviewed?`Latest log reviewed by ${data.latest_review.reviewed_by}`:'Your latest log awaits doctor review'}</div></div>
  </div>
  {data.summary_lines?.length?<Panel title="Recent health summary" subtitle="Based only on your real recorded demo entries">
   <ul className="summary-lines">{data.summary_lines.map((l,i)=><li key={i}><CheckCircle2 size={13}/> {l}</li>)}</ul>
  </Panel>:null}
  <div className="two-col">
   <Panel title="Follow-up instructions" subtitle="From your doctor — demo instructions, not automatic treatment changes">
    {(()=>{const all=[...data.overdue_follow_ups,...data.follow_ups];return all.length?all.map(f=><div key={f.id} className="care-card"><div className="care-card-top"><strong>{f.instructions}</strong><Pill tone={data.overdue_follow_ups.some(o=>o.id===f.id)?'coral':'amber'}>{data.overdue_follow_ups.some(o=>o.id===f.id)?'overdue':'scheduled'}</Pill></div><small>{f.due_at?`Due ${time(f.due_at,true)}`: 'No due date'} · Dr. {f.doctor}</small></div>):<div className="care-card demo-preview"><div className="care-card-top"><strong>Next check-in</strong><Pill tone="blue">demo preview</Pill></div><p>Continue recording daily wellbeing and sputum diary entries so the assigned doctor can review the timeline.</p><small>Illustrative reminder · no follow-up has been sent by a clinician.</small></div>;})()}
   </Panel>
   <Panel title="Current care plan" subtitle="Doctor-documented demo care plan (read-only for you)">
    {data.care_plan?<><h4 className="subheading">Goals</h4><p>{data.care_plan.goals}</p>
     {data.care_plan.activity_guidance&&<><h4 className="subheading">Activity guidance</h4><p>{data.care_plan.activity_guidance}</p></>}
     {data.care_plan.adherence_support&&<><h4 className="subheading">Medication & adherence support</h4><p>{data.care_plan.adherence_support}</p></>}
     {data.care_plan.review_date&&<p className="input-help"><CalendarClock size={13}/> Next review: {data.care_plan.review_date}</p>}</>:<div className="care-card demo-preview"><div className="care-card-top"><strong>Care plan preview</strong><Pill tone="blue">demo preview</Pill></div><p><b>Goal:</b> Keep daily wellbeing and symptom records up to date.</p><p><b>Activity:</b> Record everyday activity and note changes from the usual routine.</p><p><b>Adherence:</b> Record medication-taking patterns for discussion with the assigned doctor.</p><small>This is illustrative guidance, not a saved care plan or medical instruction.</small></div>}
   </Panel>
  </div>
  <Panel title="Recent daily records" subtitle="What you logged recently · your doctor sees the same records">
   {data.recent_logs.length?<div className="table-scroll"><table className="pgx-table"><thead><tr><th>Date</th><th>Water</th><th>Activity</th><th>Sleep</th><th>Wellbeing</th><th>Reviewed</th></tr></thead><tbody>{data.recent_logs.map(l=><tr key={l.id}><td>{l.entry_date}</td><td>{l.water_ml??'—'} ml</td><td>{l.activity_minutes??'—'} min</td><td>{l.sleep_hours??'—'} h {l.sleep_quality?`(${l.sleep_quality})`:''}</td><td>{l.wellbeing??'—'}</td><td>{l.reviewed_by?<Pill tone="low">✓ {l.reviewed_by}</Pill>:<Pill>pending</Pill>}</td></tr>)}</tbody></table></div>:<Empty text="No records yet — add today's log from My Health Records."/>}
  </Panel>
 </div>;
}
