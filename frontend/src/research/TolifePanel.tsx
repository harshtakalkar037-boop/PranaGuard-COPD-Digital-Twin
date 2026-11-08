/** Longitudinal COPD Research (TOLIFE) — corrected experiment first: event audit, reconciled counts,
 *  honest 24/48/72h feasibility-probe metrics, and longitudinal observed-channel series. */
import {useMemo,useState} from 'react';
import {Activity, Users} from 'lucide-react';
import {Line,LineChart,ReferenceLine,ResponsiveContainer,Tooltip,XAxis,YAxis} from 'recharts';
import {Loading, MetricCard, Notice, Panel, Pill, number, pct} from '../components';
import {useRemote} from '../hooks';
import {explainError} from '../api';
import type {TolifeOverview,TolifeParticipants,TolifeSeries} from './types';

const CHANNEL_LABELS:Record<string,string>={spo2_daily:'SpO₂ daily median (%)',hr_sleep_mean:'Sleep HR mean (bpm)',ppg_rmssd_ms:'PPG RMSSD (ms)',walked_dist_m:'Walked distance (m)',sleep_efficiency:'Sleep efficiency (%)',fev1_session_L:'FEV₁ session (L)'};

export function TolifePanel({revision}:{revision:number}){
  const {data:ov,error}=useRemote<TolifeOverview>('/models/tolife/overview',revision);
  const {data:series}=useRemote<TolifeSeries>('/models/tolife/series',revision);
  const {data:parts}=useRemote<TolifeParticipants>('/models/tolife/participants',revision);
  const channels=Object.keys(series?.series||{});
  const [channel,setChannel]=useState('spo2_daily');
  const countries=useMemo(()=>{
    const counts:Record<string,number>={};
    (parts?.participants||[]).forEach(p=>{counts[p.country]=(counts[p.country]||0)+1;});
    return Object.entries(counts).sort((a,b)=>b[1]-a[1]);
  },[parts]);
  if(!ov)return <Panel title='Longitudinal COPD research'><Loading label={error?`Unavailable: ${explainError(error)}`:'Loading TOLIFE research view…'}/></Panel>;
  const a=ov.event_audit;
  const activeChannel=channels.includes(channel)?channel:channels[0];
  return <>
    <Notice tone='warning'>
      <strong>Exploratory feasibility probe — not a clinically reliable predictor.</strong> {ov.corrected_experiment_note} The study-provided model-estimated CAT/CCQ/mMRC classes were removed from predictors, and only register events inside the observed monitoring frame are evaluated.
    </Notice>
    <div className='metric-grid research-metrics'>
      <MetricCard label='Register entries audited' value={a.total_entries} detail={`${a.unique_participants} unique participants · ${a.missing_dates} missing dates`} icon={<Activity size={18}/>}/>
      <MetricCard label='Inside observed frame' value={a.observed_frame.inside} detail={`${a.observed_frame.outside} register events fall outside any observed monitoring`} icon={<Activity size={18}/>} tone='amber'/>
      <MetricCard label='Valid measurements in prior 7d' value={a.events_with_valid_measurements_in_prior_7d} detail='Computed against observed participant-days only' icon={<Activity size={18}/>} tone='blue'/>
      <MetricCard label='Evaluable events' value={a.in_frame_events_with_prior_7d_measurements} detail='In-frame with prior-7-day measurements' icon={<Activity size={18}/>} tone='coral'/>
    </div>
    <div className='two-col'>
      <Panel title='Event audit & reconciliation' subtitle='Corrected v2 counting; raw register rows are never fused to twin identities'>
        <div className='status-rows'>
          <div><span>Raw register entries</span><strong>{a.total_entries}</strong></div>
          <div><span>Unique participants</span><strong>{a.unique_participants}</strong></div>
          <div><span>Missing event dates</span><strong>{a.missing_dates}</strong></div>
          <div><span>In device window</span><strong>{a.device_window.inside}<small> ({a.device_window.outside} outside)</small></strong></div>
          <div><span>In observed frame</span><strong>{a.observed_frame.inside}<small> ({a.observed_frame.outside} outside)</small></strong></div>
          <div><span>Prior-7d measurements</span><strong>{a.events_with_valid_measurements_in_prior_7d}</strong></div>
          <div><span>In-frame + prior-7d</span><strong>{a.in_frame_events_with_prior_7d_measurements}</strong></div>
        </div>
        <p className='input-help'>{a.note}</p>
      </Panel>
      <Panel title='24/48/72h feasibility horizons' subtitle='Leakage-corrected leave-one-participant-out probe; honest negative/weak results'>
        <div className='table-scroll'><table className='ablation-table'><thead><tr><th>Horizon</th><th>AUROC [95% CI]</th><th>AUPRC</th><th>Brier</th><th>Positive days</th></tr></thead><tbody>
          {Object.values(ov.horizons).map(h=>(
            <tr key={h.horizon_hours}>
              <td><strong>{h.horizon_hours}h</strong><small>{h.definition}</small></td>
              <td>{h.auroc===null?'n/a':`${number(h.auroc,3)}${h.auroc_ci?` [${h.auroc_ci.map(v=>number(v,3)).join('–')}]`:''}`}</td>
              <td>{h.auprc===null?'n/a':number(h.auprc,4)}<small> prev {pct(h.prevalence,2)}</small></td>
              <td>{h.brier===null?'n/a':number(h.brier,3)}</td>
              <td>{h.n_positive_days}/{h.n_eval_days}</td>
            </tr>))}
        </tbody></table></div>
        <Notice tone='warning'>Confidence intervals span 0.5 (chance). These exploratory results cannot support clinical use and are never mixed with Digital-Twin metrics.</Notice>
      </Panel>
    </div>
    <Panel title='Longitudinal observed-channel series' subtitle={series?.rel_day_definition||'Days relative to register onset'} action={series&&<Pill tone='blue'>{series.n_in_frame_events} in-frame onsets</Pill>}>
      {series?<>
        <div className='environment-selector'><label htmlFor='tolife-channel'>Observed channel</label>
          <select id='tolife-channel' value={activeChannel} onChange={e=>setChannel(e.target.value)}>{channels.map(c=><option key={c} value={c}>{CHANNEL_LABELS[c]||c}</option>)}</select>
          <Pill tone='neutral'>REAL-OBSERVED</Pill></div>
        <ResponsiveContainer width='100%' height={240}>
          <LineChart data={series.series[activeChannel]||[]} margin={{top:8,right:16,bottom:4,left:0}}>
            <XAxis dataKey='rel_day' tickFormatter={(v:number)=>`${v}`} label={{value:'days relative to onset',position:'insideBottomRight',offset:-2}}/>
            <YAxis domain={['auto','auto']} width={52}/>
            <Tooltip formatter={(v:unknown)=>number(v as number,2)}/>
            <ReferenceLine x={0} stroke='#c2410c' strokeDasharray='4 3'/>
            <Line type='monotone' dataKey='median' stroke='#0f766e' strokeWidth={2} dot={false} isAnimationActive={false}/>
            <Line type='monotone' dataKey='q1' stroke='#94a3b8' strokeWidth={1} dot={false} isAnimationActive={false} strokeDasharray='3 3'/>
            <Line type='monotone' dataKey='q3' stroke='#94a3b8' strokeWidth={1} dot={false} isAnimationActive={false} strokeDasharray='3 3'/>
          </LineChart>
        </ResponsiveContainer>
        <div className='chart-note'><span className='status-dot'/>Median with inter-quartile band across in-frame onsets (severity: {series.severity_of_in_frame_events.join(' / ')}). {series.channels_note}</div>
      </>:<Loading label='Loading longitudinal series…'/>}
    </Panel>
    <div className='two-col'>
      <Panel title='Study participants (coded identities)' subtitle='No identity merging with platform patients'>
        {parts?<div className='status-rows'>
          <div><span>Participants</span><strong>{parts.count}</strong></div>
          {countries.slice(0,6).map(([c,n])=><div key={c}><span>{c}</span><strong>{n}<Users size={12}/></strong></div>)}
          <div><span>Identity handling</span><strong className='small'>{parts.identity_note}</strong></div>
        </div>:<Loading label='Loading participants…'/>}
      </Panel>
      <Panel title='Evidence provenance' subtitle='Where this research view comes from'>
        <div className='status-rows'>
          <div><span>Dataset</span><strong className='small'>{ov.dataset}</strong></div>
          <div><span>Model id</span><strong>{ov.model_id}</strong></div>
          <div><span>Evidence class</span><strong>REAL_OBSERVED inputs · REAL_DERIVED metrics</strong></div>
        </div>
        <p className='input-help'>{ov.framing}</p>
        <Notice>Weak below/near-chance probe results are presented as executed evidence — they must not be read as a deployable early-warning capability.</Notice>
      </Panel>
    </div>
  </>;
}
