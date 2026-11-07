import {useEffect,useMemo,useState} from 'react';
import {CalendarRange} from 'lucide-react';
import {Area,AreaChart,Bar,BarChart,CartesianGrid,Legend,Line,LineChart,ResponsiveContainer,Tooltip,XAxis,YAxis} from 'recharts';
import {api,explainError} from '../api';
import {Empty,Loading,Notice,Panel,number} from '../components';
import type {PatientInsights} from './types';

const PRESETS=[{label:'7 days',days:7},{label:'30 days',days:30},{label:'90 days',days:90}] as const;

function ChartPanel({title,subtitle,children,empty,unit}:{title:string;subtitle:string;children:React.ReactNode;empty:string;unit?:string}){
 return <Panel title={title} subtitle={unit?`${subtitle} · unit: ${unit}`:subtitle}>
  <div className="chart-wrap" data-testid={`chart-${title.toLowerCase().replace(/[^a-z0-9]+/g,'-')}`}>{empty?<Empty text={empty}/>:children}</div>
 </Panel>;
}

function iso(d:Date){return d.toISOString().slice(0,10);}

export function InsightsTab(){
 const today=iso(new Date());
 const [from,setFrom]=useState(iso(new Date(Date.now()-29*86400e3)));
 const [to,setTo]=useState(today);
 const [data,setData]=useState<PatientInsights|null>(null);const [error,setError]=useState('');const [loading,setLoading]=useState(true);
 useEffect(()=>{
  setLoading(true);
  const qs=new URLSearchParams({from,to}).toString();
  api<PatientInsights>(`/workspace/patient/insights?${qs}`).then(d=>{setData(d);setError('');}).catch(e=>setError(explainError(e))).finally(()=>setLoading(false));
 },[from,to]);
 const weekly=useMemo(()=>data?weeklyLines(data):[],[data]);
 const sputumTrend=useMemo(()=>data?data.sputum_entries.map(e=>({date:e.date,cough:e.cough,breathlessness:e.breathlessness})):[],[data]);
 const adherenceTrend=useMemo(()=>data?data.adherence.map(a=>({date:a.date,taken:a.taken?1:0,missed:a.taken?0:1,med:a.name})):[],[data]);
 const hasSymptoms=!!data&&data.replay_symptom_score.length>0;
 return <div className="pgx">
  <Panel title="Date range" subtitle="Graphs show only real recorded data — missing dates stay missing" action={<CalendarRange size={14}/>}>
   <div className="pgx-inline" data-testid="insights-ranges">
    {PRESETS.map(p=><button key={p.days} className={`button secondary small-button ${isPreset(from,to,p.days)?'selected':''}`} onClick={()=>{setTo(today);setFrom(iso(new Date(Date.now()-(p.days-1)*86400e3)));}}>{p.label}</button>)}
    <label className="input-help" htmlFor="ins-from">From <input id="ins-from" type="date" className="form-input" value={from} max={to} onChange={e=>setFrom(e.target.value||from)}/></label>
    <label className="input-help" htmlFor="ins-to">To <input id="ins-to" type="date" className="form-input" value={to} min={from} max={today} onChange={e=>setTo(e.target.value||to)}/></label>
   </div>
  </Panel>
  {error&&<Notice tone="warning">{error}</Notice>}
  {loading&&<Loading label="Building your insights from recorded entries…"/>}
  {data&&!loading&&<>
   <Panel title="Summary for this period" subtitle="Evidence-based counts from your actual entries">
    <ul className="summary-lines">{data.summary.length?data.summary.map((l,i)=><li key={i}>{l}</li>):<li>No records in this period.</li>}</ul>
    {weekly.length>0&&<h4 className="subheading">Monthly roll-up</h4>}
    {weekly.length>0&&<ul className="summary-lines">{weekly.map((l,i)=><li key={i}>{l}</li>)}</ul>}
   </Panel>
   <p className="input-help">{data.note}</p>
   <div className="two-col">
    <ChartPanel title="Breathlessness & cough" subtitle="From your sputum diary entries (patient-reported)" unit="0–10" empty={!sputumTrend.length?'No sputum diary entries in this range — add one in the Sputum diary tab.':''}>
     <ResponsiveContainer width="100%" height={220}><LineChart data={sputumTrend}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="date"/><YAxis domain={[0,10]} width={30}/><Tooltip/><Legend/><Line type="monotone" dataKey="cough" name="Cough (0–10)" stroke="#2563eb" connectNulls dot/><Line type="monotone" dataKey="breathlessness" name="Breathlessness (0–10)" stroke="#b45309" connectNulls dot/></LineChart></ResponsiveContainer>
    </ChartPanel>
    <ChartPanel title="Symptom-score trend" subtitle="Frozen synthetic replay dataset — not wearable telemetry" unit={data.units.symptom_score} empty={!hasSymptoms?`No replay symptom data inside ${from} → ${to} (replay covers ${data.replay_window.first} → ${data.replay_window.last}; pick a custom range to view it).`:''}>
     <ResponsiveContainer width="100%" height={220}><LineChart data={data.replay_symptom_score}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="date"/><YAxis domain={[0,10]} width={30}/><Tooltip/><Line type="monotone" dataKey="mean" name="Daily mean (0–10)" stroke="#b45309" connectNulls dot/></LineChart></ResponsiveContainer>
    </ChartPanel>
    <ChartPanel title="Breathing-rate history" subtitle="Frozen synthetic replay dataset — not wearable telemetry" unit={data.units.resp_rate} empty={!data.breathing_rate.length?`No replay vitals inside ${from} → ${to} (replay covers ${data.replay_window.first} → ${data.replay_window.last}; pick a custom range to view it).`:''}>
     <ResponsiveContainer width="100%" height={220}><AreaChart data={data.breathing_rate}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="date"/><YAxis width={30}/><Tooltip/><Legend/><Area type="monotone" dataKey="max" name="max breaths/min" stroke="#53b2a8" fill="#53b2a833"/><Area type="monotone" dataKey="min" name="min breaths/min" stroke="#0f9488" fill="#0f948822"/><Line type="monotone" dataKey="mean" name="daily mean" stroke="#0f766e" dot/></AreaChart></ResponsiveContainer>
    </ChartPanel>
    <ChartPanel title="Sleep" subtitle="From your daily logs" unit={data.units.sleep_hours} empty={!data.sleep.some(r=>r.value!=null)?'No sleep recorded in this range.':''}>
     <ResponsiveContainer width="100%" height={220}><BarChart data={data.sleep}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="date"/><YAxis width={30}/><Tooltip/><Bar dataKey="value" name="hours slept" fill="#6d5bd0"/></BarChart></ResponsiveContainer>
    </ChartPanel>
    <ChartPanel title="Activity" subtitle="From your daily logs" unit={data.units.activity_minutes} empty={!data.activity.some(r=>r.value!=null)?'No activity recorded in this range.':''}>
     <ResponsiveContainer width="100%" height={220}><BarChart data={data.activity}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="date"/><YAxis width={30}/><Tooltip/><Bar dataKey="value" name="minutes" fill="#0f9488"/></BarChart></ResponsiveContainer>
    </ChartPanel>
    <ChartPanel title="Hydration" subtitle="Water intake from your daily logs" unit={data.units.water_ml} empty={!data.hydration.some(r=>r.value!=null)?'No water intake recorded in this range.':''}>
     <ResponsiveContainer width="100%" height={220}><AreaChart data={data.hydration}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="date"/><YAxis width={42}/><Tooltip formatter={(v:number)=>`${v} ${data.units.water_ml}`}/><Area type="monotone" dataKey="value" name="water" stroke="#2563eb" fill="#2563eb22" connectNulls/></AreaChart></ResponsiveContainer>
    </ChartPanel>
    <ChartPanel title="Medication adherence" subtitle={data.sources.medication} unit="reports" empty={!adherenceTrend.length?'No adherence reports in this range.':''}>
     <ResponsiveContainer width="100%" height={220}><BarChart data={adherenceTrend}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="date"/><YAxis width={30} allowDecimals={false}/><Tooltip/><Legend/><Bar dataKey="taken" name="taken as prescribed" fill="#0f9488"/><Bar dataKey="missed" name="missed" fill="#e05d44"/></BarChart></ResponsiveContainer>
    </ChartPanel>
    <ChartPanel title="Wellbeing check-ins" subtitle="How you felt, grouped by day" unit="count" empty={!data.wellbeing.some(r=>r.value!=null)?'No wellbeing entries in this range.':''}>
     <ResponsiveContainer width="100%" height={220}><BarChart data={wellbeingCounts(data.wellbeing)}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="date"/><YAxis width={30} allowDecimals={false}/><Tooltip/><Legend/><Bar dataKey="better" name="better" fill="#0f9488"/><Bar dataKey="same" name="same" fill="#94a3b8"/><Bar dataKey="worse" name="worse" fill="#e05d44"/></BarChart></ResponsiveContainer>
    </ChartPanel>
   </div>
   <Notice>Sources: daily logs = your own entries · sputum = your diary · breathing rate & symptom-score trend = {data.sources.breathing_rate}. {data.replay_window.note}</Notice>
  </>}
 </div>;
}

function isPreset(from:string,to:string,n:number){return to===iso(new Date())&&(Date.parse(to)-Date.parse(from))/86400e3===n-1;}
function wellbeingCounts(rows:{date:string;label?:string}[]){const m=new Map<string,{date:string;better:number;same:number;worse:number}>();for(const r of rows){if(!r.label)continue;const e=m.get(r.date)||{date:r.date,better:0,same:0,worse:0};if(r.label==='better'||r.label==='same'||r.label==='worse')e[r.label]++;m.set(r.date,e);}return [...m.values()].sort((a,b)=>a.date.localeCompare(b.date));}
function weeklyLines(d:PatientInsights):string[]{
 const weeks=new Map<string,{n:number;sleep:number[];water:number[];activity:number[]}>();
 const touch=(date:string)=>{const wk=date.slice(0,7);if(!weeks.has(wk))weeks.set(wk,{n:0,sleep:[],water:[],activity:[]});return weeks.get(wk)!;};
 for(const r of d.sleep){const wk=touch(r.date);if(r.value!=null&&r.quality!==undefined||r.value!=null){wk.sleep.push(r.value as number);}wk.n++;}
 for(const r of d.hydration){const wk=touch(r.date);if(r.value!=null)wk.water.push(r.value as number);}
 for(const r of d.activity){const wk=touch(r.date);if(r.value!=null)wk.activity.push(r.value as number);}
 if(!weeks.size)return [];
 const avg=(xs:number[])=>xs.reduce((a,b)=>a+b,0)/xs.length;
 return [...weeks.entries()].sort().map(([wk,v])=>{
  const parts=[`${wk} · ${v.n} day(s) with entries`];
  if(v.sleep.length)parts.push(`avg sleep ${number(avg(v.sleep))}h`);
  if(v.water.length)parts.push(`avg water ${number(avg(v.water),0)}ml`);
  if(v.activity.length)parts.push(`avg activity ${number(avg(v.activity),0)}min`);
  return parts.join(' — ');
 });
}
