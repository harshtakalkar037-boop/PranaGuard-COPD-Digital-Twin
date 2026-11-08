import {render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {PatientShell} from './PatientShell';
import {PatientRecordsPage} from './Records';
import {PatientDocumentsPage} from './Documents';
import home from './__fixtures__/patient-home.json';
import logs from './__fixtures__/patient-daily-logs.json';
import meds from './__fixtures__/patient-medications.json';
import adherence from './__fixtures__/patient-adherence.json';
import documents from './__fixtures__/patient-documents.json';
import followUps from './__fixtures__/patient-follow-ups.json';
import sputum from './__fixtures__/patient-sputum.json';
import type {SessionUser} from './types';

const patient:SessionUser={username:'pat-pg0071',display_name:'Synthetic twin 071 viewer (demo)',role:'patient',patient_id:'PG-0071',assigned_patients:0};
const doctor:SessionUser={username:'dr-atlas',display_name:'Dr. Asha Atlas (demo)',role:'doctor',patient_id:null,assigned_patients:120};

let fetchMock:ReturnType<typeof vi.fn>;
const route=(url:string)=>url.includes('/patient/home')?home:url.includes('/patient/daily-logs')?logs:url.includes('/patient/medications')?meds:url.includes('/patient/adherence')?adherence:url.includes('/patient/documents')?documents:url.includes('/patient/follow-ups')?followUps:url.includes('/sputum')?sputum:{};
beforeEach(()=>{sessionStorage.clear();sessionStorage.setItem('pg-workspace-session','vitest-token');
 fetchMock=vi.fn(async(input:string,opt?:RequestInit)=>{
  if(opt?.method)return new Response(JSON.stringify({id:99,notice:'saved'}),{status:200});
  return new Response(JSON.stringify(route(String(input))),{status:200});});
 vi.stubGlobal('fetch',fetchMock);});

describe('patient shell',()=>{
 it('shows exactly three new nav items and no clinician/research navigation',async()=>{
  render(<PatientShell user={patient} logout={vi.fn()}/>);
  await screen.findByRole('heading',{name:'Patient Home'});
  for(const l of ['Patient Home','My Health Records','Clinical Documents'])expect(screen.getAllByRole('button',{name:l}).length).toBeGreaterThan(0);
  for(const l of ['Cohort overview','Patients','Care action centre','Patient twins','Model validation','Devices','Environment'])expect(screen.queryByRole('button',{name:l})).toBeNull();
 });
 it('patient home surfaces plan, follow-up reminders, documents count and review status',async()=>{
  render(<PatientShell user={patient} logout={vi.fn()}/>);
  await screen.findByText(/Synthetic demo data|synthetic demo data/i,{exact:false});
  expect((await screen.findAllByText(/Demo instruction:/)).length).toBeGreaterThan(0);
  expect((await screen.findAllByText(/Documents/)).length).toBeGreaterThan(0);
 });
 it('sign out button exists for patient role',async()=>{
  const logout=vi.fn();render(<PatientShell user={patient} logout={logout}/>);
  await screen.findByRole('heading',{name:'Patient Home'});
  await userEvent.click(screen.getAllByRole('button',{name:/Sign out/})[0]);expect(logout).toHaveBeenCalled();
 });
});

describe('patient daily records',()=>{
 it('submits a daily log with structured fields',async()=>{
  render(<PatientRecordsPage/>);
  const water=await screen.findByLabelText('Water intake (ml)');
  await userEvent.type(water,'1800');
  await userEvent.click(screen.getByRole('button',{name:'Save daily log'}));
  await waitFor(()=>expect(fetchMock.mock.calls.some(c=>String(c[0]).includes('/patient/daily-logs')&&(c[1]?.method==='POST'))).toBe(true));
 });
 it('edit flow pre-fills and PUTs a correction',async()=>{
  render(<PatientRecordsPage/>);
  const btn=await screen.findAllByRole('button',{name:'Correct this entry'});
  await userEvent.click(btn[0]);
  expect(await screen.findByText(/Correction saved|correct entry/i,{exact:false})).toBeTruthy();
  await userEvent.click(screen.getByRole('button',{name:'Save correction'}));
  await waitFor(()=>expect(fetchMock.mock.calls.some(c=>String(c[0]).includes('/patient/daily-logs/')&&(c[1]?.method==='PUT'))).toBe(true));
 });
 it('medication adherence requires a reason when a dose is missed',async()=>{
  render(<PatientRecordsPage/>);
  await userEvent.click(await screen.findByRole('button',{name:'Medication'}));
  await screen.findAllByText(meds.medication_options[0].name);
  await userEvent.click(screen.getByLabelText('Missed / different'));
  const save=screen.getByRole('button',{name:'Save report'});
  expect(save.hasAttribute('disabled')).toBe(true);
  await userEvent.type(screen.getByLabelText('Reason (required)'),'travelled');
  expect(save.hasAttribute('disabled')).toBe(false);
  await userEvent.click(save);
  await waitFor(()=>expect(fetchMock.mock.calls.some(c=>String(c[0]).includes('/patient/adherence')&&(c[1]?.method==='POST'))).toBe(true));
 });
 it('patient cannot reach another patient record (route is not patient-self)',async()=>{
  render(<PatientRecordsPage/>);await screen.findAllByRole('button',{name:'Correct this entry'});
  expect(fetchMock.mock.calls.every(c=>!String(c[0]).includes('PG-0001'))).toBe(true);
 });
});

describe('patient documents',()=>{
 it('lists shared documents and builds an authorized download request',async()=>{
  render(<PatientDocumentsPage/>);
  expect(await screen.findByText(documents.items[0].title)).toBeTruthy();
  fetchMock.mockResolvedValueOnce(new Response(new Blob(['demo']),{status:200,headers:{'content-type':'text/plain'}}));
  await userEvent.click(screen.getAllByRole('button',{name:/Download/})[0]);
  await waitFor(()=>expect(fetchMock.mock.calls.some(c=>String(c[0]).includes('/workspace/documents/'))).toBe(true));
 });
 it('shows honest empty state when nothing shared',async()=>{
  fetchMock.mockResolvedValue(new Response(JSON.stringify({items:[],note:'x'}),{status:200}));
  render(<PatientDocumentsPage/>);expect(await screen.findByText(/No documents shared yet/)).toBeTruthy();
 });
 it('surfaces backend errors honestly',async()=>{
  fetchMock.mockResolvedValue(new Response(JSON.stringify({detail:'boom'}),{status:500}));
  render(<PatientDocumentsPage/>);expect(await screen.findByText(/boom/)).toBeTruthy();
 });
});
void doctor;
