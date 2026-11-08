/** Model registry panel — id, version, dataset, task, preprocessing, artifact, metrics and limitations per model. */
import {useState} from 'react';
import {ChevronDown, ChevronRight} from 'lucide-react';
import {Pill} from '../components';
import type {RegistryResponse} from './types';

export function RegistryPanel({registry}:{registry:RegistryResponse}){
  const [open,setOpen]=useState<string>('');
  return <div className='table-scroll'><table className='registry-table'>
    <thead><tr><th/><th>Model</th><th>Version</th><th>Dataset</th><th>Task</th><th>Inference</th><th>Evidence</th><th>Registered</th></tr></thead>
    <tbody>
      {registry.models.map(m=>{
        const expanded=open===m.model_id;
        return <>
          <tr key={m.model_id} className='registry-row'>
            <td><button className='icon-button' aria-label={`${expanded?'Collapse':'Expand'} ${m.model_display_name}`} onClick={()=>setOpen(expanded?'':m.model_id)}>{expanded?<ChevronDown size={14}/>:<ChevronRight size={14}/>}</button></td>
            <td><strong>{m.model_display_name}</strong><small>{m.model_id}</small></td>
            <td>{m.version}</td>
            <td className='small'>{m.dataset_source}</td>
            <td className='small'>{m.task_type}</td>
            <td><Pill tone={m.inference_method==='none'?'neutral':m.inference_method==='report_only'?'amber':'low'}>{m.inference_method}</Pill></td>
            <td><Pill tone='blue'>{m.provenance_evidence_class}</Pill></td>
            <td className='small'>{m.registered_at.slice(0,10)}</td>
          </tr>
          {expanded&&<tr key={`${m.model_id}-detail`} className='registry-detail'>
            <td/><td colSpan={7}>
              <div className='registry-detail-grid'>
                <div><h4>Preprocessing</h4><code className='registry-code'>{JSON.stringify(m.preprocessing)}</code></div>
                <div><h4>Feature schema</h4><code className='registry-code'>{JSON.stringify(m.feature_schema)}</code></div>
                <div><h4>Artifact</h4><code className='registry-code'>{m.artifact_path||'report-only — no executable artifact'}</code></div>
                <div><h4>Supported outputs</h4><code className='registry-code'>{m.supported_outputs.join(', ')}</code></div>
                <div className='registry-wide'><h4>Executed evaluation (verbatim)</h4><code className='registry-code'>{JSON.stringify(m.evaluation,null,1)}</code></div>
                <div className='registry-wide'><h4>Limitations</h4><ul className='limit-list in-table'>{m.limitations.map((l,i)=><li key={i}>{l}</li>)}</ul></div>
              </div>
            </td>
          </tr>}
        </>;
      })}
    </tbody>
  </table></div>;
}
