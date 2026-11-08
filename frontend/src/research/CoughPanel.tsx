/** Cough Analysis (external research model) — info, optional audio inference, metrics, attribution, limitations.
 *  The model is never described as diagnostic/screening; its low COPD sensitivity is shown prominently. */
import {useState} from 'react';
import {AlertTriangle, Mic, Upload} from 'lucide-react';
import {Empty, Loading, MetricCard, Notice, Panel, Pill, number, pct} from '../components';
import {useRemote} from '../hooks';
import {explainError} from '../api';
import {uploadCoughAudio} from './api';
import type {CoughHistory, CoughInfo, CoughPrediction} from './types';

function confusion(m:CoughInfo['test_metrics']['confusion']):{tn:number;fp:number;fn:number;tp:number}{
  if(Array.isArray(m))return {tn:m[0][0],fp:m[0][1],fn:m[1][0],tp:m[1][1]};
  return m;
}

export function CoughPanel({revision}:{revision:number}){
  const {data:info,error}=useRemote<CoughInfo>('/models/cough/info',revision);
  const {data:history}=useRemote<CoughHistory>('/models/cough/history?limit=10',revision);
  const [file,setFile]=useState<File|null>(null);
  const [busy,setBusy]=useState(false);const [result,setResult]=useState<CoughPrediction|null>(null);const [inferError,setInferError]=useState('');
  if(!info)return <Panel title='Cough Analysis'><Loading label={error?`Unavailable: ${explainError(error)}`:'Loading cough research model…'}/></Panel>;
  const m=info.test_metrics;const cm=confusion(m.confusion);
  const missed=cm.fn,actualCOPD=cm.fn+cm.tp;
  async function infer(){
    if(!file)return;
    setBusy(true);setInferError('');setResult(null);
    try{setResult(await uploadCoughAudio<CoughPrediction>(file));}
    catch(e){setInferError(explainError(e));}
    finally{setBusy(false);}
  }
  return <>
    <Notice tone='warning'>
      <AlertTriangle size={15}/> <strong>Low COPD sensitivity: {pct(m.sensitivity_copd)}.</strong> At the shipped threshold this model missed {missed} of {actualCOPD} COPD-labelled test files. It is not a diagnostic or screening tool and must not rule disease in or out.
    </Notice>
    <div className='two-col'>
      <Panel title='Model & dataset' subtitle='Calibrated random forest on external cough recordings'>
        <div className='status-rows'>
          <div><span>Model</span><strong>{info.model_id} · v{info.version}</strong></div>
          <div><span>Dataset</span><strong>Cough-COPD(CC) · Zenodo 14881818 (CC-BY-4.0)</strong></div>
          <div><span>Publisher split</span><strong>{info.train.n} train / {info.test.n} test files</strong></div>
          <div><span>Test composition</span><strong>{info.test.COPD} COPD / {info.test.Healthy} healthy</strong></div>
          <div><span>Task</span><strong>Binary file-level study-cough classification</strong></div>
          <div><span>Protocol</span><strong>{info.protocol}</strong></div>
          <div><span>Evidence class</span><strong>REAL_DERIVED <small>(trained on REAL_OBSERVED recordings)</small></strong></div>
          <div><span>Runtime provenance</span><strong className='small'>{info.runtime_environment}</strong></div>
        </div>
        <Notice>No participant identifiers are published for this dataset, so a participant-independent evaluation cannot be verified — file-level metrics are an optimistic upper bound.</Notice>
      </Panel>
      <Panel title='Audio inference' subtitle='Runs the bundled artifact only when the audio pipeline is available'>
        {info.inference_available
          ?<>
            <p className='input-help'>Upload a short cough recording (WAV/FLAC/OGG). Features (MFCC, log-Mel, ZCR, RMS, spectral centroid) are extracted in the backend exactly as during training; the calibrated model returns a probability with its input hash. Predictions are persisted to the research audit log.</p>
            <label className='field-label' htmlFor='cough-file'>Cough recording</label>
            <input id='cough-file' type='file' accept='audio/*' className='form-input' onChange={e=>{setFile(e.target.files?.[0]||null);setResult(null);setInferError('');}}/>
            <button className='button primary' disabled={!file||busy} onClick={infer}><Upload size={15}/>{busy?'Running inference…':'Run cough research inference'}</button>
            {inferError&&<Notice tone='warning'>Inference unavailable: {inferError}</Notice>}
            {result&&<div className='cough-result' role='status'>
              <div className='cough-result-head'><Pill tone={result.class_label==='COPD'?'amber':'low'}>{result.class_label}-labelled</Pill><strong>P(COPD label) {number(result.p_copd,3)}</strong></div>
              <div className='prob-bar' aria-label={`Calibrated probability ${number(result.p_copd,3)}`}><i style={{width:`${Math.round(result.p_copd*100)}%`}}/></div>
              <div className='status-rows'>
                <div><span>Model version</span><strong>{result.model_version}</strong></div>
                <div><span>Audio decoded</span><strong>{number(result.audio.duration_s,2)}s · {result.audio.samplerate_hz} Hz</strong></div>
                <div><span>Input hash</span><strong className='small'>{result.input_hash}</strong></div>
              </div>
              <Notice tone='warning'>{result.disclaimer}</Notice>
            </div>}
          </>
          :<Notice tone='warning'>Audio inference is not available in this runtime{info.inference_note?`: ${info.inference_note}`:''}. The evaluation dashboard below still reflects the executed experiment — no predictions are fabricated.</Notice>}
      </Panel>
    </div>
    <div className='metric-grid research-metrics'>
      <MetricCard label='AUROC · file level' value={number(m.auroc,4)} detail='Multiple recordings per participant; upper bound' icon={<Mic size={18}/>}/>
      <MetricCard label='AUPRC' value={number(m.auprc,4)} detail={`Prevalence baseline ${number(m.prevalence_copd,3)}`} icon={<Mic size={18}/>} tone='blue'/>
      <MetricCard label='COPD sensitivity' value={pct(m.sensitivity_copd)} detail={`${missed}/${actualCOPD} COPD files missed`} icon={<AlertTriangle size={18}/>} tone='coral'/>
      <MetricCard label='Specificity' value={pct(m.specificity)} detail='Healthy-labelled files' icon={<Mic size={18}/>} tone='amber'/>
      <MetricCard label='Brier score' value={number(m.brier,4)} detail='After sigmoid calibration (cv=5)' icon={<Mic size={18}/>} tone='blue'/>
      <MetricCard label='Accuracy / F1(COPD)' value={<>{pct(m.accuracy)}<small> / {number(m.f1_copd,3)}</small></>} detail='Threshold 0.5; not a clinical cutoff' icon={<Mic size={18}/>}/>
    </div>
    <div className='two-col'>
      <Panel title='Dataset-level feature attribution' subtitle='Generated by this research module — no Digital-Twin SHAP reuse'>
        <div className='attr-list'>
          {info.global_feature_importance.slice(0,15).map(f=>(
            <div key={f.feature} className='attr-row'>
              <span className='attr-name'>{f.feature}</span>
              <div className='attr-bar'><i style={{width:`${Math.min(100,Math.round(f.importance/(info.global_feature_importance[0]?.importance||1)*100))}%`}}/></div>
              <span className='attr-val'>{number(f.importance,4)}</span>
            </div>
          ))}
        </div>
        <p className='input-help'>{info.global_feature_importance_note} Feature importance is descriptive and is not causality.</p>
      </Panel>
      <Panel title='Limitations — read before any interpretation' subtitle='These bound every number on this screen'>
        <ul className='limit-list'>{info.limitations.map((l,i)=><li key={i}><AlertTriangle size={13}/>{l}</li>)}</ul>
        <Notice tone='warning'>Exploratory research output. Not validated for diagnosis, screening, triage, monitoring or treatment decisions.</Notice>
      </Panel>
    </div>
    <Panel title='Persisted inference log' subtitle='Backend-persisted; no fabricated history'>
      {history&&history.count>0
        ?<div className='table-scroll'><table><thead><tr><th>Time (UTC)</th><th>File</th><th>Label</th><th>P(COPD)</th><th>Audio</th><th>Input hash</th></tr></thead><tbody>
          {history.predictions.map(p=><tr key={p.id}><td>{p.created_at.slice(0,19).replace('T',' ')}</td><td>{p.input_summary.filename}</td><td>{p.output.class_label}</td><td>{number(p.output.p_copd,3)}</td><td>{number(p.input_summary.audio.duration_s,1)}s</td><td className='small'>{p.input_hash}</td></tr>)}
        </tbody></table></div>
        :<Empty text='No cough inferences recorded yet in this deployment.'/>}
    </Panel>
  </>;
}
