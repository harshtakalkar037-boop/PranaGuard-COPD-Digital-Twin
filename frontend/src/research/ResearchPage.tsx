/** Research Models dashboard — three model cards (Digital Twin info + two external research models).
 *  Metrics are never merged or ranked across models: different datasets, different tasks. */
import {useState} from 'react';
import {Activity, ArrowRight, FlaskConical, HeartPulse, Mic, ShieldCheck} from 'lucide-react';
import {Loading, Notice, Panel, Pill, number, pct} from '../components';
import {useRemote} from '../hooks';
import {CoughPanel} from './CoughPanel';
import {TolifePanel} from './TolifePanel';
import {RegistryPanel} from './RegistryPanel';
import type {RegistryResponse} from './types';
import type {View} from '../types';
import './research.css';

type Tab='registry'|'cough'|'tolife';

export function ResearchPage({revision,navigate}:{revision:number;navigate:(v:View)=>void}){
  const [tab,setTab]=useState<Tab>('registry');
  const {data:registry,error}=useRemote<RegistryResponse>('/models/registry',revision);
  if(!registry)return <Panel title='Research models'><Loading label={error?`Research registry unavailable: ${error}`:'Loading research model registry…'}/></Panel>;
  const cough=registry.models.find(m=>m.model_kind==='cough_research');
  const tolife=registry.models.find(m=>m.model_kind==='tolife_research');
  const coughAuroc=(cough?.evaluation as {auroc?:number}|undefined)?.auroc;
  const coughSens=(cough?.evaluation as {sensitivity_copd?:number}|undefined)?.sensitivity_copd;
  const tolifeAuroc=(tolife?.evaluation as Record<string,{auroc?:number}>|undefined)?.['72']?.auroc;
  return <>
    <Notice tone='amber'>
      Three model cards, three separate datasets and tasks. Metrics are reported per model only — they are never merged, averaged or ranked against each other. None of these models is a validated diagnostic, screening or triage tool.
    </Notice>
    <div className='research-cards'>
      <div className='research-card'>
        <div className='research-card-head'><span className='research-icon twin'><HeartPulse size={20}/></span><div><strong>PranaGuard Digital Twin</strong><small>Production platform model — v1 + 48h v3 audit</small></div><Pill tone='neutral'>SYNTHETIC DATA</Pill></div>
        <p className='research-card-desc'>The platform's own twin model: LightGBM on the generated synthetic cohort, 24/48/72h horizon study plus the separate v3 48h audit. Fully disclosed as synthetic-generated; not validated on real patients.</p>
        <div className='research-card-metrics'>
          <div><span>72h AUROC (v1)</span><strong>reported under Model validation</strong></div>
        </div>
        <button className='text-link' onClick={()=>navigate('validation')}>Open executed validation<ArrowRight size={14}/></button>
      </div>
      <div className='research-card'>
        <div className='research-card-head'><span className='research-icon cough'><Mic size={20}/></span><div><strong>Cough Analysis</strong><small>External research model · Cough-COPD(CC) dataset</small></div><Pill tone='blue'>REAL-DERIVED</Pill></div>
        <p className='research-card-desc'>Calibrated random-forest classifier distinguishing COPD-labelled from healthy-labelled cough recordings. File-level evaluation; participant independence unverifiable.</p>
        <div className='research-card-metrics'>
          <div><span>File-level AUROC</span><strong>{number(coughAuroc,4)}</strong></div>
          <div><span>COPD sensitivity</span><strong>{pct(coughSens)}</strong><small> conservative — misses real COPD files</small></div>
        </div>
        <button className='button secondary small-button' onClick={()=>setTab('cough')}>Open Cough Analysis<ArrowRight size={13}/></button>
      </div>
      <div className='research-card'>
        <div className='research-card-head'><span className='research-icon tolife'><Activity size={20}/></span><div><strong>Longitudinal COPD Research</strong><small>External study view · TOLIFE Clinical Study A</small></div><Pill tone='blue'>REAL-OBSERVED</Pill></div>
        <p className='research-card-desc'>Longitudinal sensor and clinical-day exploration of the TOLIFE study with a leakage-corrected feasibility probe at 24/48/72h horizons. Below-chance results are reported honestly.</p>
        <div className='research-card-metrics'>
          <div><span>72h feasibility AUROC</span><strong>{number(tolifeAuroc,3)}</strong><small> CI spans chance</small></div>
          <div><span>Framing</span><strong>Exploratory</strong></div>
        </div>
        <button className='button secondary small-button' onClick={()=>setTab('tolife')}>Open longitudinal research<ArrowRight size={13}/></button>
      </div>
    </div>
    <div className='segmented research-tabs' role='tablist' aria-label='Research model sections'>
      <button role='tab' aria-selected={tab==='registry'} onClick={()=>setTab('registry')} className={tab==='registry'?'selected':''}><ShieldCheck size={13}/> Model registry</button>
      <button role='tab' aria-selected={tab==='cough'} onClick={()=>setTab('cough')} className={tab==='cough'?'selected':''}><Mic size={13}/> Cough Analysis</button>
      <button role='tab' aria-selected={tab==='tolife'} onClick={()=>setTab('tolife')} className={tab==='tolife'?'selected':''}><FlaskConical size={13}/> Longitudinal research</button>
    </div>
    {tab==='registry'&&<RegistryPanel registry={registry}/>}
    {tab==='cough'&&<CoughPanel revision={revision}/>}
    {tab==='tolife'&&<TolifePanel revision={revision}/>}
  </>;
}
