import {render,screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {describe,expect,it,vi,beforeEach} from 'vitest';
import {cloneElement} from 'react';
import type {ReactElement} from 'react';
import {RiskSection} from './Risk';
import {InsightsTab} from './Insights';
import {PatientHomePage} from './PatientHome';

vi.mock('recharts',async importOriginal=>{const original=await importOriginal<typeof import('recharts')>();return {...original,ResponsiveContainer:({children}:{children:ReactElement<{width?:number;height?:number}>})=><div>{cloneElement(children,{width:700,height:230})}</div>};});

const snapshot={patient_id:'PG-0071',available:true,source:'frozen replay inference (pg-synthetic-v1)',
 horizons:{'24':{risk:0.0151,label:'raw 0–1 score ×100'},'48':{risk:0.1011,label:'raw 0–1 score ×100'},'72':{risk:0.2966,label:'raw 0–1 score ×100'}},
 risk_category:'elevated',model_version:'pg-synthetic-v1',predicted_at:'2026-09-13T07:00:00Z',state_version:1040,
 input_window:'hourly twin state at 2026-09-13 07:00:00+00:00',data_completeness:'supported',missing_fields:[],warnings:[],
 freshness:{state_timestamp:'2026-09-13T07:00:00Z',latest_patient_record_update:'2026-11-06T09:00:00Z'},
 review_status:{status:'completed',updated_at:'2026-11-05T10:00:00Z'},calibration:'none (raw LightGBM score)',
 disclaimer:'Experimental synthetic-data model estimate. Not clinically validated. Not intended for diagnosis, triage, or treatment decisions.',note:'Risk outputs are estimates.'};
const history={count:3,disclaimer:snapshot.disclaimer,note:'Timestamped captures',items:[
 {id:1,horizon:24,model_version:'pg-synthetic-v1',risk:0.0151,state_version:1040,input_timestamp:'2026-09-13T07:00:00Z',recorded_at:'2026-11-06T10:00:00Z',data_status:'supported',provenance:'{}'},
 {id:2,horizon:48,model_version:'pg-synthetic-v1',risk:0.1011,state_version:1040,input_timestamp:'2026-09-13T07:00:00Z',recorded_at:'2026-11-06T10:00:00Z',data_status:'supported',provenance:'{}'},
 {id:3,horizon:72,model_version:'pg-synthetic-v1',risk:0.2966,state_version:1040,input_timestamp:'2026-09-13T07:00:00Z',recorded_at:'2026-11-06T10:00:00Z',data_status:'supported',provenance:'{}'}]};
const explain={patient_id:'PG-0071',horizon:72,available:true,method:'LightGBM native TreeSHAP',model_version:'pg-synthetic-v1',
 drivers:[{feature:'age',value:48,contribution:-1.55,label:'Age'},{feature:'symptom_mean6',value:2.04,contribution:0.22,label:'Symptom Mean6'}],caution:'correlation, not causation. Raw TreeSHAP weights are not calibrated outputs.'};
const today=new Date().toISOString().slice(0,10);
const insights={range:{start:today,end:today,days:1},summary:['1 day(s) with daily-log entries'],
 daily_logs:[{entry_date:today,symptom_score:3,water_ml:1800,activity_minutes:20,sleep_hours:7.5,sleep_quality:'good',wellbeing:'same'}],
 sputum_entries:[{date:today,colour:'clear',volume:'scant',cough:2,breathlessness:1}],
 adherence:[{date:today,taken:true,name:'Demo inhaler',missed_reason:null}],
 sleep:[{date:today,value:7.5,quality:'good'}],activity:[{date:today,value:20}],hydration:[{date:today,value:1800}],
 wellbeing:[{date:today,value:1,label:'same'}],breathing_rate:[],replay_symptom_score:[],
 units:{water_ml:'ml',activity_minutes:'minutes',sleep_hours:'hours',resp_rate:'breaths/min',symptom_score:'0–10'},
 sources:{daily_logs:'patient-reported',sputum:'diary',medication:'patient-reported',breathing_rate:'frozen synthetic replay dataset (hourly simulated vitals) — not wearable data',replay_symptom_score:'frozen synthetic replay dataset'},
 replay_window:{first:'2026-07-27',last:'2026-09-13',note:'Frozen synthetic replay timestamps'},note:'Graphs show only real records.'};
const home={patient_id:'PG-0071',profile:{display_name:'Demo Patient'},baseline:{status:'done',observed_hours:1000},logged_today:true,streak_days:3,
 recent_logs:[],recent_adherence:[],care_plan:null,follow_ups:[],overdue_follow_ups:[],documents_count:2,documents_recent:[],
 latest_review:{reviewed:true,reviewed_by:'dr-atlas'},
 summary_lines:['You logged your wellbeing on 3 of the last 14 days.','Medication reports in the last 14 days: 2 of 2 taken as documented.'],note:'demo'};

let fetchMock:ReturnType<typeof vi.fn>;
beforeEach(()=>{
 sessionStorage.setItem('pg-workspace-session','vitest-token');
 fetchMock=vi.fn(async(input:string)=>{
  if(input.includes('/risk/explanation'))return new Response(JSON.stringify(explain),{status:200});
  if(input.includes('/risk/history'))return new Response(JSON.stringify(history),{status:200});
  if(input.includes('/risk'))return new Response(JSON.stringify(snapshot),{status:200});
  if(input.includes('/patient/insights'))return new Response(JSON.stringify(insights),{status:200});
  if(input.includes('/patient/home'))return new Response(JSON.stringify(home),{status:200});
  return new Response('{}',{status:200});
 });
 vi.stubGlobal('fetch',fetchMock);
});

describe('doctor risk visibility (v6)',()=>{
 it('renders 24/48/72 cards with disclaimer, version and review status',async()=>{
  render(<RiskSection pid="PG-0071"/>);
  await screen.findByText(/24h horizon/);
  expect(screen.getByText('48h horizon')).toBeTruthy();expect(screen.getByText('72h horizon')).toBeTruthy();
  expect(screen.getAllByText('pg-synthetic-v1').length).toBeGreaterThan(0);
  expect(screen.getAllByText(/Experimental synthetic-data model estimate/).length).toBeGreaterThan(0);
  expect(screen.getByText(/completed/)).toBeTruthy();
 });
 it('shows timestamped prediction history and lazy explanation on demand',async()=>{
  render(<RiskSection pid="PG-0071"/>);
  await screen.findByText(/Prediction history/);
  await userEvent.click(screen.getByRole('button',{name:/Show model explanation/}));
  await screen.findByText('Symptom Mean6');
  expect(screen.getByText('+0.2200')).toBeTruthy();
 });
});

describe('patient insights (v6)',()=>{
 it('renders graphs panel with range controls and patient-safe summary',async()=>{
  render(<InsightsTab/>);
  await screen.findByText('Breathlessness & cough');
  expect(screen.getByText('Breathing-rate history')).toBeTruthy();
  expect(screen.getByText('Medication adherence')).toBeTruthy();
  expect(screen.getAllByText(/not wearable/,{exact:false}).length).toBeGreaterThan(0);
  expect(screen.getByTestId('insights-ranges')).toBeTruthy();
 });
 it('labels the replay window honestly for breathing-rate gaps',async()=>{
  render(<InsightsTab/>);
  await screen.findAllByText(/replay covers 2026-07-27 → 2026-09-13/).then(xs=>expect(xs.length).toBeGreaterThan(0));
 });
});

describe('patient home summary lines (v6)',()=>{
 it('shows data-backed summary lines on Patient Home',async()=>{
  render(<PatientHomePage navigate={()=>{}}/>);
  await screen.findByText('Recent health summary');
  expect(screen.getByText(/logged your wellbeing on 3 of the last 14 days/)).toBeTruthy();
  expect(screen.getByText(/2 of 2 taken as documented/)).toBeTruthy();
 });
});
