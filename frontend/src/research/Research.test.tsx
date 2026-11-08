/** Research models module — routes render real backend responses, no fabricated numbers. */
import {render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {cloneElement} from 'react';
import type {ReactElement} from 'react';
import {ResearchPage} from './ResearchPage';
import registry from './__fixtures__/registry.json';
import coughInfo from './__fixtures__/cough-info.json';
import tolifeOverview from './__fixtures__/tolife-overview.json';
import tolifeSeries from './__fixtures__/tolife-series.json';
import tolifeParticipants from './__fixtures__/tolife-participants.json';
vi.mock('recharts',async importOriginal=>{const original=await importOriginal<typeof import('recharts')>();return {...original,ResponsiveContainer:({children}:{children:ReactElement<{width?:number;height?:number}>})=><div>{cloneElement(children,{width:700,height:250})}</div>};});
let fetchMock:ReturnType<typeof vi.fn>;
beforeEach(()=>{
  const responses=(url:string)=>url.includes('/models/registry')?registry:url.includes('/models/cough/info')?coughInfo:url.includes('/models/cough/history')?{predictions:[],count:0}:url.includes('/models/tolife/overview')?tolifeOverview:url.includes('/models/tolife/series')?tolifeSeries:url.includes('/models/tolife/participants')?tolifeParticipants:{};
  fetchMock=vi.fn(async(input:string)=>new Response(JSON.stringify(responses(String(input))),{status:200}));
  vi.stubGlobal('fetch',fetchMock);
});
const ready=async()=>{render(<ResearchPage revision={0} navigate={()=>{}}/>);await screen.findByText('PranaGuard Digital Twin');};
describe('research dashboard cards',()=>{
  it('renders three model cards without mixing metrics',async()=>{
    await ready();
    expect(screen.getAllByText('Cough Analysis').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Longitudinal COPD Research').length).toBeGreaterThan(0);
    expect(screen.getByText(/never merged, averaged or ranked/i)).toBeInTheDocument();
    expect(screen.getByText('0.9316')).toBeInTheDocument();
  });
  it('registry tab lists models and expands verbatim detail',async()=>{
    await ready();
    await userEvent.click(screen.getByRole('tab',{name:/Model registry/}));
    expect(screen.getByText('cough-copd-rf-calibrated')).toBeInTheDocument();
    expect(screen.getByText('tolife-longitudinal-probe-v2')).toBeInTheDocument();
    await userEvent.click(screen.getByLabelText('Expand Cough Analysis'));
    await screen.findByText(/Executed evaluation \(verbatim\)/);
  });
});
describe('cough research panel',()=>{
  const openCough=async()=>{await ready();await userEvent.click(screen.getByRole('tab',{name:/Cough Analysis/}));return screen.findByText(/Low COPD sensitivity/);};
  it('shows honest low sensitivity and limitation framing',async()=>{
    await openCough();
    expect(screen.getAllByText('57.8%').length).toBeGreaterThan(0);
    expect(screen.getByText(/not a diagnostic or screening tool/i)).toBeInTheDocument();
    expect(screen.getByText(/Feature importance is descriptive/i)).toBeInTheDocument();
  });
  it('offers inference only when the backend artifact is available',async()=>{
    await openCough();
    expect(screen.getByLabelText('Cough recording')).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Run cough research inference'})).toBeDisabled();
  });
  it('surfaces explicit unavailability when inference is off',async()=>{
    fetchMock.mockImplementation(async(input:string)=>{
      const url=String(input);
      if(url.includes('/models/cough/info'))return new Response(JSON.stringify({...coughInfo,inference_available:false,inference_note:'cough_model.joblib not present'}),{status:200});
      const all=(u:string)=>u.includes('/models/registry')?registry:u.includes('/models/cough/history')?{predictions:[],count:0}:{};
      return new Response(JSON.stringify(all(url)),{status:200});
    });
    await openCough();
    expect(screen.getByText(/no predictions are fabricated/i)).toBeInTheDocument();
  });
  it('posts the file as multipart and shows the returned probability',async()=>{
    fetchMock.mockImplementation(async(input:string)=>{
      const url=String(input);
      if(url.includes('/models/cough/infer'))return new Response(JSON.stringify({model_id:'cough-copd-rf-calibrated',model_version:'1.0.0',class_label:'COPD',p_copd:0.777,p_healthy:0.223,threshold:0.5,audio:{duration_s:1.2,samplerate_hz:16000},input_hash:'abc123',evidence:'REAL_OBSERVED input',disclaimer:'Experimental cough-classification research model. NOT a diagnosis.'}),{status:200});
      const responses=(u:string)=>u.includes('/models/registry')?registry:u.includes('/models/cough/info')?coughInfo:u.includes('/models/cough/history')?{predictions:[],count:0}:{};
      return new Response(JSON.stringify(responses(url)),{status:200});
    });
    await openCough();
    const file=new File([new Uint8Array([82,73,70,70,36,0,0,0])],'cough.wav',{type:'audio/wav'});
    await userEvent.upload(screen.getByLabelText('Cough recording'),file);
    await userEvent.click(screen.getByRole('button',{name:'Run cough research inference'}));
    await screen.findByText('COPD-labelled');
    expect(screen.getByText(/NOT a diagnosis/)).toBeInTheDocument();
    const call=fetchMock.mock.calls.find(c=>String(c[0]).includes('/models/cough/infer'));
    expect(call![1]!.body).toBeInstanceOf(FormData);
  });
});
describe('tolife research panel',()=>{
  const openTolife=async()=>{await ready();await userEvent.click(screen.getByRole('tab',{name:/Longitudinal research/}));return screen.findByText(/Leakage-corrected leave-one-participant-out/);};
  it('renders reconciled audit counts and honest horizons',async()=>{
    await openTolife();
    expect(screen.getAllByText('80').length).toBeGreaterThan(0);
    expect(screen.getAllByText((_,el)=>el?.tagName==='TD'&&/0\.355 \[/.test(el?.textContent||'')).length).toBe(1);
    expect(screen.getAllByText((_,el)=>el?.tagName==='TD'&&/0\.389 \[/.test(el?.textContent||'')).length).toBe(1);
    expect(screen.getAllByText((_,el)=>el?.tagName==='TD'&&/0\.393 \[/.test(el?.textContent||'')).length).toBe(1);
    expect(screen.getByText(/Exploratory feasibility probe/)).toBeInTheDocument();
  });
  it('switches observed channels from real series data',async()=>{
    await openTolife();
    const sel=await screen.findByLabelText('Observed channel');
    await userEvent.selectOptions(sel,'ppg_rmssd_ms');
    await waitFor(()=>expect((sel as HTMLSelectElement).value).toBe('ppg_rmssd_ms'));
  });
});
