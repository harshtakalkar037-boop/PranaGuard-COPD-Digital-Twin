import {useState,cloneElement} from 'react';
import type {ReactElement} from 'react';
import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {PatientsPage} from './Patients';
import {DevicesPage} from './Devices';
import {EnvironmentPage} from './Environment';
import {NotificationsPage} from './Notifications';
import {SourcesPage} from './Sources';
import {api} from '../api';
import registryFixture from './__fixtures__/registry.json';
import profileFixture from './__fixtures__/profile.json';
import devicesFixture from './__fixtures__/devices.json';
import readingsFixture from './__fixtures__/device-readings.json';
import citiesFixture from './__fixtures__/cities.json';
import environmentFixture from './__fixtures__/environment.json';
import notificationsFixture from './__fixtures__/notifications.json';
import notificationFixture from './__fixtures__/notification-detail.json';
import emailFixture from './__fixtures__/email.json';
import provenanceFixture from './__fixtures__/provenance.json';
import type {DeviceList,Notification,NotificationList,ReviewStatus} from './types';

// Fixtures are captured real local API responses. Mutations below are controlled
// component-test doubles, not provider evidence or production fallback values.
vi.mock('recharts',async importOriginal=>{const original=await importOriginal<typeof import('recharts')>();return {...original,ResponsiveContainer:({children}:{children:ReactElement<{width?:number;height?:number}>})=><div>{cloneElement(children,{width:700,height:250})}</div>};});
const pid=profileFixture.profile.patient_id;const nid=notificationFixture.id;
const copy=<T,>(v:T):T=>JSON.parse(JSON.stringify(v));
let fetchMock:ReturnType<typeof vi.fn>;let devices:DeviceList;let notification:Notification;let notices:NotificationList;let failure:string;
const notify=vi.fn(),refresh=vi.fn(),select=vi.fn(),openProfile=vi.fn();
const pageProps={revision:0,refresh,notify};
const response=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status});
const calls=(suffix:string,method='POST')=>fetchMock.mock.calls.filter(([url,options])=>String(url).endsWith(suffix)&&options?.method===method);

beforeEach(()=>{
 vi.clearAllMocks();devices=copy(devicesFixture) as unknown as DeviceList;notification=copy(notificationFixture) as unknown as Notification;notices=copy(notificationsFixture) as unknown as NotificationList;failure='';
 fetchMock=vi.fn(async(input:string,options?:RequestInit)=>{
  const url=new URL(String(input),'http://component-test.local');const path=url.pathname.replace('/api/enhanced','');const method=options?.method||'GET';const body=typeof options?.body==='string'?JSON.parse(options.body):{};
  if(failure&&path===failure)return response({detail:'Controlled test: backend request failed.'},503);
  if(path==='/environment/cities')return response(citiesFixture);
  if(path.startsWith('/environment/'))return response(environmentFixture);
  if(path==='/registry/patients'&&method==='POST')return response({patient_id:pid,duplicate:false,prediction_supported:false,notice:'Fictional patient saved with no new prediction.'});
  if(path==='/registry/patients'){
   const rows=registryFixture.patients.filter(p=>{const q=url.searchParams.get('q')||'';return (p.patient_id+' '+p.display_name+' '+p.city).toLowerCase().includes(q.toLowerCase())&&(!url.searchParams.get('city')||p.city===url.searchParams.get('city'))&&(!url.searchParams.get('status')||p.monitoring_status===url.searchParams.get('status'));});
   return response({...registryFixture,patients:rows,total:rows.length});
  }
  if(path.endsWith('/observations')||path.endsWith('/reviews'))return response({id:1,notice:'Controlled synthetic component-test mutation.'});
  if(path.startsWith('/registry/patients/'))return response(profileFixture);
  if(path==='/devices'&&method==='POST')return response(devices.devices.find(d=>d.kind===body.kind)||devices.devices[0]);
  if(path==='/devices')return response(devices);
  if(path.includes('/devices/')&&path.endsWith('/readings'))return response(readingsFixture);
  if(path.includes('/devices/')&&(path.endsWith('/start')||path.endsWith('/stop'))){const d=devices.devices.find(d=>path.includes(d.id))!;d.is_simulating=path.endsWith('/start');d.status=d.is_simulating?'connected_simulation':'disconnected';return response(d);}
  if(path==='/notifications/test'){
   notification={...notification,status:'active',unread:true,read_at:null,history:notification.history?.slice(0,1)};notices.notifications=notices.notifications.map(n=>n.id===notification.id?notification:n);return response(notification);
  }
  if(path==='/notifications'){
   const rows=notices.notifications.filter(n=>(!url.searchParams.get('category')||n.category===url.searchParams.get('category'))&&(!url.searchParams.get('patient_id')||n.patient_id===url.searchParams.get('patient_id'))&&(url.searchParams.get('unread_only')!=='true'||n.unread));
   return response({...notices,notifications:rows,counts:{unread:notices.notifications.filter(n=>n.unread).length,total:notices.notifications.length,open:notices.notifications.filter(n=>!['resolved','closed'].includes(n.status)).length}});
  }
  if(path.startsWith('/notifications/')){
   const id=Number(path.split('/').pop());let n=id===notification.id?notification:notices.notifications.find(n=>n.id===id)!;
   if(method==='PATCH'){
    const old=n.status;n={...n,...(body.status?{status:body.status as ReviewStatus}:{}),...(typeof body.read==='boolean'?{unread:!body.read,read_at:body.read?notificationFixture.updated_at:null}:{})};
    if(id===notification.id){notification=n;notification.history=[...(notification.history||[]),{id:999+(notification.history?.length||0),created_at:notificationFixture.updated_at,from_status:old,to_status:n.status,action:'review',note:body.note||'Component test read update',actor:'demo_workspace'}];}
    notices.notifications=notices.notifications.map(item=>item.id===id?n:item);
   }
   return response({...n,history:n.history||[]});
  }
  if(path==='/email/test')return response({...emailFixture.outbox[0],patient_data_included:false,inbox_delivery_verified:false});
  if(path==='/email')return response(emailFixture);
  if(path==='/provenance')return response(provenanceFixture);
  return response({detail:'Unexpected component-test route: '+path},404);
 });vi.stubGlobal('fetch',fetchMock);
});

function Registry({selected=''}:{selected?:string}){return <PatientsPage {...pageProps} selected={selected} select={select} openHistorical={vi.fn()} openCare={vi.fn()} openDevices={vi.fn()} openNotifications={vi.fn()}/>;}
function DeviceHarness(){const [revision,setR]=useState(0);return <DevicesPage revision={revision} refresh={()=>setR(r=>r+1)} notify={notify} selectedPatient={pid} selectPatient={select} openProfile={openProfile}/>;}
function NotificationHarness(){const [revision,setR]=useState(0);return <NotificationsPage revision={revision} refresh={()=>setR(r=>r+1)} notify={notify} openProfile={openProfile}/>;}

describe('fictional registry and onboarding',()=>{
 it('renders captured registry records and explicit fictional identity language',async()=>{render(<Registry/>);await screen.findByRole('heading',{name:'All synthetic patients'});await screen.findByText('PG-0001');expect(screen.getByText(/120 original historical patients/)).toBeInTheDocument();});
 it('searches server records by ID and reports an honest empty result',async()=>{render(<Registry/>);await screen.findByText('PG-0001');await userEvent.type(screen.getByLabelText('Search registry by patient ID'),pid);await screen.findByRole('button',{name:'Open profile '+pid});expect(screen.queryByRole('button',{name:'Open profile PG-0001'})).not.toBeInTheDocument();await userEvent.clear(screen.getByLabelText('Search registry by patient ID'));await userEvent.type(screen.getByLabelText('Search registry by patient ID'),'NO-SUCH-ID');await screen.findByText('No fictional patients match these registry filters.');});
 it('requests city and onboarding filters through the typed API path',async()=>{render(<Registry/>);await screen.findByText('PG-0001');fireEvent.change(screen.getByLabelText('Filter registry city'),{target:{value:'Pune'}});fireEvent.change(screen.getByLabelText('Filter registry status'),{target:{value:'collecting_baseline'}});await waitFor(()=>expect(fetchMock.mock.calls.some(c=>String(c[0]).includes('city=Pune')&&String(c[0]).includes('status=collecting_baseline'))).toBe(true));});
 it('uses the shared workspace search to filter the assigned registry',async()=>{
  const props={...pageProps,selected:'',select,openHistorical:vi.fn(),openCare:vi.fn(),openDevices:vi.fn(),openNotifications:vi.fn()};
  const {rerender}=render(<PatientsPage {...props} search=""/>);await screen.findByText('PG-0001');
  rerender(<PatientsPage {...props} search={pid}/>);await screen.findByRole('button',{name:'Open profile '+pid});
  expect(screen.queryByRole('button',{name:'Open profile PG-0001'})).not.toBeInTheDocument();
 });
 it('requires fictional confirmation before registration and sends no client-selected ID',async()=>{
  render(<Registry/>);await screen.findByText('PG-0001');await userEvent.click(screen.getByRole('button',{name:'Add fictional patient'}));expect(screen.getByRole('button',{name:'Save fictional patient'})).toBeDisabled();
  await userEvent.type(screen.getByLabelText('Fictional alias',{exact:true}),'Atlas Test');fireEvent.change(screen.getByLabelText('Demo age (18–100)'),{target:{value:'58'}});await userEvent.click(screen.getByRole('checkbox',{name:/I confirm that all identity/}));await userEvent.click(screen.getByRole('button',{name:'Save fictional patient'}));
  await waitFor(()=>expect(select).toHaveBeenCalledWith(pid));const body=JSON.parse(calls('/registry/patients')[0][1]!.body as string);expect(body.fictional_identity_confirmed).toBe(true);expect(body.source_type).toBe('manual_demo');expect(body.baseline_spo2).toBeNull();expect(body).not.toHaveProperty('patient_id');
 });
 it('opens a complete profile without inventing predictions',async()=>{render(<Registry selected={pid}/>);await screen.findByRole('heading',{name:profileFixture.profile.display_name});expect(screen.getByText('No 24/48/72h prediction is available for this registration.')).toBeInTheDocument();expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow',String(profileFixture.baseline.observed_hours));expect(screen.queryByRole('button',{name:/Open original twin/})).not.toBeInTheDocument();});
 it('brings account provisioning and selected care access into the patient profile',async()=>{
  const openCare=vi.fn();render(<PatientsPage {...pageProps} selected={pid} select={select} openHistorical={vi.fn()} openCare={openCare} openDevices={vi.fn()} openNotifications={vi.fn()}/>);
  await screen.findByRole('heading',{name:'Care and account access'});
  expect(screen.getByRole('button',{name:'Provision assigned patient'})).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button',{name:'Open care record'}));expect(openCare).toHaveBeenCalledWith(pid);
 });
 it('displays actual ingested readings, monitoring versions and separate environment context',async()=>{render(<Registry selected={pid}/>);await screen.findByLabelText('Monitoring version');expect(screen.getByRole('heading',{name:'Monitoring-only twin state'})).toBeInTheDocument();expect(screen.getByRole('heading',{name:'Current city context (separate)'})).toBeInTheDocument();const old=profileFixture.monitoring_versions.at(-1)!;fireEvent.change(screen.getByLabelText('Monitoring version'),{target:{value:String(old.version)}});expect(screen.getByText('Monitoring v'+old.version+' · received',{exact:false})).toBeInTheDocument();});
 it('persists explicitly fictional symptom/adherence input through POST',async()=>{render(<Registry selected={pid}/>);await screen.findByLabelText('Fictional symptom score (0–10)');fireEvent.change(screen.getByLabelText('Fictional symptom score (0–10)'),{target:{value:'7'}});fireEvent.change(screen.getByLabelText('Fictional adherence (%)'),{target:{value:'45'}});await userEvent.click(screen.getByRole('checkbox',{name:'This observation is fictional demo data.'}));await userEvent.click(screen.getByRole('button',{name:'Save fictional observation'}));await waitFor(()=>expect(calls('/observations')).toHaveLength(1));expect(JSON.parse(calls('/observations')[0][1]!.body as string)).toMatchObject({fictional_data_confirmed:true,symptom_score:7,adherence:.45});});
 it('keeps empty review actions disabled and posts actual review notes',async()=>{render(<Registry selected={pid}/>);await screen.findByLabelText('Fictional review note');expect(screen.getByRole('button',{name:'Save demo review'})).toBeDisabled();await userEvent.type(screen.getByLabelText('Fictional review note'),'Fictional baseline reviewed.');await userEvent.click(screen.getByRole('button',{name:'Save demo review'}));await waitFor(()=>expect(calls('/reviews')).toHaveLength(1));});
 it('shows backend failure without fabricating a profile',async()=>{failure='/registry/patients/'+pid;render(<Registry selected={pid}/>);await screen.findByRole('alert');expect(screen.getByText(/Controlled test: backend request failed/)).toBeInTheDocument();expect(screen.queryByText(profileFixture.profile.display_name)).not.toBeInTheDocument();});
});

describe('generic simulated devices',()=>{
 it('exposes all4 generic capability types without hardware claims',async()=>{render(<DeviceHarness/>);await screen.findByLabelText('Generic device type');expect(screen.getByLabelText('Generic device type').querySelectorAll('option')).toHaveLength(4);expect(screen.getByText(/No Bluetooth\/USB hardware or commercial device compatibility/)).toBeInTheDocument();});
 it('associates a device without starting it automatically',async()=>{render(<DeviceHarness/>);await screen.findByLabelText('Generic device type');fireEvent.change(screen.getByLabelText('Simulation interval (seconds)'),{target:{value:'3'}});await userEvent.click(screen.getByRole('button',{name:'Associate simulated device'}));await waitFor(()=>expect(calls('/devices')).toHaveLength(1));expect(fetchMock.mock.calls.some(c=>String(c[0]).endsWith('/start'))).toBe(false);expect(JSON.parse(calls('/devices')[0][1]!.body as string)).toMatchObject({patient_id:pid,interval_seconds:3});});
 it('executes Start/Stop on the backend and renders returned simulation status',async()=>{render(<DeviceHarness/>);const d=devices.devices[0];await screen.findByRole('button',{name:'Start simulation '+d.id});await userEvent.click(screen.getByRole('button',{name:'Start simulation '+d.id}));await waitFor(()=>expect(screen.getByRole('button',{name:'Stop simulation '+d.id})).toBeEnabled());expect(calls('/'+d.id+'/start')).toHaveLength(1);await userEvent.click(screen.getByRole('button',{name:'Stop simulation '+d.id}));await waitFor(()=>expect(screen.getByRole('button',{name:'Start simulation '+d.id})).toBeEnabled());});
 it('requires a synthetic patient selection rather than generating an unlinked stream',async()=>{render(<DevicesPage {...pageProps} selectedPatient="" selectPatient={select} openProfile={openProfile}/>);await screen.findByText('Select a synthetic patient to associate a generic simulated device. No simulation starts automatically.');expect(screen.queryByRole('button',{name:'Associate simulated device'})).not.toBeInTheDocument();});
});

describe('modelled city environment',()=>{
 it('renders actual captured context, source timestamps and explicit AQI scale',async()=>{render(<EnvironmentPage {...pageProps}/>);await screen.findByRole('heading',{name:'Ambient air · modelled'});expect(screen.getByText('U.S. AQI, NOT Indian CPCB NAQI.')).toBeInTheDocument();expect(screen.getAllByText('Modelled external').length).toBeGreaterThan(0);expect(screen.getByLabelText('Context city').querySelectorAll('option')).toHaveLength(4);});
 it('uses explicit backend refresh and leaves model input boundary visible',async()=>{render(<EnvironmentPage {...pageProps}/>);await screen.findByRole('button',{name:'Refresh context'});await userEvent.click(screen.getByRole('button',{name:'Refresh context'}));await waitFor(()=>expect(calls('/environment/Pune/refresh')).toHaveLength(1));expect(screen.getByText('Context only. Never enters frozen ML features or changes historical predictions.')).toBeInTheDocument();});
});

describe('persistent notification review and email honesty',()=>{
 it('filters categories and patient links through the server',async()=>{render(<NotificationHarness/>);await screen.findByRole('button',{name:'Create test notification'});fireEvent.change(screen.getByLabelText('Notification category filter'),{target:{value:'patient_monitoring'}});fireEvent.change(screen.getByLabelText('Notification patient filter'),{target:{value:pid}});await waitFor(()=>expect(fetchMock.mock.calls.some(c=>String(c[0]).includes('category=patient_monitoring')&&String(c[0]).includes('patient_id='+pid))).toBe(true));});
 it('creates a test event and reviews acknowledgement/under-review/resolution/closure',async()=>{render(<NotificationHarness/>);await screen.findByRole('button',{name:'Create test notification'});await userEvent.click(screen.getByRole('button',{name:'Create test notification'}));await screen.findByRole('heading',{name:notificationFixture.title});for(const name of ['Acknowledge notification','Mark under review','Resolve notification','Close notification']){await userEvent.click(await screen.findByRole('button',{name}));}await waitFor(()=>expect(notification.status).toBe('closed'));expect(calls('/notifications/'+nid,'PATCH')).toHaveLength(4);expect(screen.getByRole('heading',{name:'Persistent review timeline'})).toBeInTheDocument();});
 it('marks reading independently of review status',async()=>{render(<NotificationHarness/>);await userEvent.click(await screen.findByRole('button',{name:'Create test notification'}));await userEvent.click(await screen.findByRole('button',{name:'Mark read'}));await waitFor(()=>expect(notification.unread).toBe(false));expect(notification.status).toBe('active');});
 it('keeps disabled email as not-sent and exposes no recipient override field',async()=>{render(<NotificationHarness/>);await screen.findByRole('button',{name:'Run demo email test'});expect(screen.getAllByText('Not sent disabled',{exact:true})).toHaveLength(emailFixture.outbox.filter(e=>e.status==='not_sent_disabled').length);await userEvent.click(screen.getByRole('button',{name:'Run demo email test'}));await waitFor(()=>expect(calls('/email/test')).toHaveLength(1));expect(notify).toHaveBeenCalledWith(emailFixture.outbox[0].detail);expect(screen.queryByRole('textbox',{name:/recipient/i})).not.toBeInTheDocument();});
});

describe('data-source transparency and API validation',()=>{
 it('classifies synthetic/manual/simulated/modelled sources and preserves missingness',async()=>{render(<SourcesPage {...pageProps} openProfile={openProfile}/>);await screen.findByRole('heading',{name:'Record-level source ledger'});expect(screen.getByText('No real clinical records or physical-device observations are present.')).toBeInTheDocument();expect(screen.getAllByText('Missing',{exact:true}).length).toBeGreaterThan(0);expect(screen.getAllByText('Excluded',{exact:true}).length).toBeGreaterThan(0);});
 it('filters record-level classifications without inserting invented records',async()=>{render(<SourcesPage {...pageProps} openProfile={openProfile}/>);await screen.findByLabelText('Provenance category filter');fireEvent.change(screen.getByLabelText('Provenance category filter'),{target:{value:'real_clinical'}});expect(screen.getByText('No records in this classification for the current selection. Missing data are not fabricated.')).toBeInTheDocument();});
 it('renders bounded validation field errors rather than echoing input payloads',async()=>{fetchMock.mockResolvedValueOnce(response({detail:[{loc:['body','age'],msg:'Input should be greater than or equal to18',input:'must-not-echo-input'}]},422));await expect(api('/validation-test')).rejects.toThrow('age: Input should be greater than or equal to18');});
});
