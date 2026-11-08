import {useEffect,useMemo,useState} from 'react';
import {Activity,FlaskConical,ShieldCheck} from 'lucide-react';
import {CartesianGrid,Legend,Line,LineChart,ResponsiveContainer,Tooltip,XAxis,YAxis} from 'recharts';
import {api,explainError} from '../api';
import {Empty,Loading,Notice,Panel,pct,time} from '../components';
import type {RiskExplanation,RiskHistory,RiskSnapshot} from './types';

function Disclaimer({text}:{text:string}){
 return <Notice tone="warning"><FlaskConical size={13}/> {text}</Notice>;
}

function SentinelCards({snap}:{snap:RiskSnapshot}){
 if(!snap.available||!snap.horizons)
  return <Panel title="24/48/72-hour model risk" subtitle="Honestly unavailable for this registration">
   <Empty text="No frozen-model prediction exists for this patient (72h baseline or feature frame not complete). Nothing is fabricated."/>
   <p className="input-help">{snap.data_completeness}</p>
  </Panel>;
 return <Panel title="24/48/72-hour model risk" subtitle={`Model ${snap.model_version} · predicted at ${snap.predicted_at?time(snap.predicted_at,true):'n/a'}`}>
  <div className="metric-grid three">
   {(['24','48','72'] as const).map(h=><div className="metric-card" key={h}>
    <div className="metric-head"><span>{h}h horizon</span></div>
    <div className="metric-number">{snap.horizons![h].risk==null?'n/a':pct(snap.horizons![h].risk!)}</div>
    <div className="metric-detail">{snap.horizons![h].label}</div>
   </div>)}
  </div>
  <div className="context-grid" style={{marginTop:10}}>
   <div><span>Model version</span><strong>{snap.model_version}</strong></div>
   <div><span>Input window</span><strong>{snap.input_window}</strong></div>
   <div><span>Data status</span><strong>{snap.data_completeness}</strong></div>
   <div><span>Review status</span><strong>{snap.review_status.status.replaceAll('_',' ')}{snap.review_status.updated_at?` · ${time(snap.review_status.updated_at,true)}`:''}</strong></div>
   <div><span>Calibration</span><strong>{snap.calibration}</strong></div>
   <div><span>Latest patient record edit</span><strong>{snap.freshness.latest_patient_record_update?time(snap.freshness.latest_patient_record_update,true):'none'}</strong></div>
  </div>
  {snap.warnings?.length?<Notice tone="warning">{snap.warnings.join(' · ')}</Notice>:null}
  <Disclaimer text={snap.disclaimer}/>
  <p className="input-help">{snap.note} Risk never auto-drives treatment in this demo.</p>
 </Panel>;
}

function TrendChart({items}:{items:RiskHistory['items']}){
 const byKey=useMemo(()=>{
  const m=new Map<string,{t:string;display:string;[k:string]:string|number}>();
  const ordered=[...items].sort((a,b)=>a.input_timestamp.localeCompare(b.input_timestamp));
  for(const r of ordered){
   const k=r.input_timestamp+':'+r.model_version;
   const row=m.get(k)||{t:k,display:time(r.input_timestamp,true)};
   row[`h${r.horizon}`]=Math.round(r.risk*1000)/10;
   m.set(k,row);
  }
  return [...m.values()];
 },[items]);
 if(!items.length)return <Empty text="No timestamped prediction history recorded yet — history appears when a doctor first views this section."/>;
 return <div className="chart-wrap"><ResponsiveContainer width="100%" height={230}>
  <LineChart data={byKey} margin={{top:6,right:12,left:-14,bottom:4}}>
   <CartesianGrid strokeDasharray="3 3"/>
   <XAxis dataKey="display"/>
   <YAxis domain={[0,100]} tickFormatter={(v:number)=>`${v}%`}/>
   <Tooltip formatter={(v:number)=>`${v}%`}/>
   <Legend/>
   <Line type="monotone" dataKey="h24" name="24h" stroke="#0f9488" dot/>
   <Line type="monotone" dataKey="h48" name="48h" stroke="#2563eb" dot/>
   <Line type="monotone" dataKey="h72" name="72h" stroke="#b45309" dot/>
  </LineChart>
 </ResponsiveContainer></div>;
}

function Explain({pid}:{pid:string}){
 const [data,setData]=useState<RiskExplanation|null>(null);const [error,setError]=useState('');const [open,setOpen]=useState(false);
 useEffect(()=>{if(open)api<RiskExplanation>(`/workspace/patients/${pid}/risk/explanation`).then(d=>{setData(d);setError('');}).catch(e=>setError(explainError(e)));},[open,pid]);
 if(!open)return <div className="pgx-inline"><button className="button secondary small-button" onClick={()=>setOpen(true)}><Activity size={13}/>Show model explanation (72h)</button></div>;
 if(error)return <Notice tone="warning">{error}</Notice>;
 if(!data)return <Loading/>;
 if(!data.available||!data.drivers.length)return <Empty text={data.note||'No explanation available for this prediction.'}/>;
 return <Panel title="Feature contributions (72h)" subtitle={data.method||'TreeSHAP (raw contributions, uncalibrated)'}>
  <div className="table-scroll"><table className="pgx-table"><thead><tr><th>Feature</th><th>Value</th><th>Contribution</th></tr></thead>
   <tbody>{data.drivers.map((d,i)=><tr key={`${d.feature}-${i}`}><td>{d.label||d.feature}</td><td>{d.value!=null?String(d.value):'—'}</td><td>{d.contribution!=null?(d.contribution>=0?'+':'')+d.contribution.toFixed(4):'—'}</td></tr>)}</tbody></table></div>
  <p className="input-help">{data.caution}</p>
 </Panel>;
}

export function RiskSection({pid}:{pid:string}){
 const [snap,setSnap]=useState<RiskSnapshot|null>(null);const [hist,setHist]=useState<RiskHistory|null>(null);const [error,setError]=useState('');
 useEffect(()=>{
  api<RiskSnapshot>(`/workspace/patients/${pid}/risk`).then(d=>{setSnap(d);setError('');}).catch(e=>setError(explainError(e)));
  api<RiskHistory>(`/workspace/patients/${pid}/risk/history`).then(d=>{setHist(d);setError('');}).catch(e=>setError(explainError(e)));
 },[pid]);
 if(error)return <Notice tone="warning">{error}</Notice>;
 if(!snap)return <Loading/>;
 return <>
  <SentinelCards snap={snap}/>
  <Panel title="Prediction history (timestamped captures)" subtitle={`${hist?hist.count:0} recorded predictions · duplicates never re-recorded`}>
   {!hist?<Loading/>:<TrendChart items={hist.items}/>}
   {hist&&<p className="input-help">{hist.note}</p>}
   {hist&&<Disclaimer text={hist.disclaimer}/>}
  </Panel>
  <Explain pid={pid}/>
  <p className="input-help"><ShieldCheck size={12}/> Experimental synthetic-data model estimate. Not clinically validated. Not intended for diagnosis, triage, or treatment decisions.</p>
 </>;
}
