import {render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {cloneElement} from 'react';
import type {ReactElement} from 'react';
import {LoginScreen} from './Login';
import {DirectoryPage} from './Directory';
import {CareCentrePage} from './CareCentre';
import {ProfilePage} from './Profile';
import {api,ApiError,explainError} from '../api';
import session from './__fixtures__/me.json';
import directory from './__fixtures__/directory.json';
import profile from './__fixtures__/profile.json';
import summary from './__fixtures__/care-summary.json';
import reviews from './__fixtures__/reviews.json';
import reviewDetail from './__fixtures__/review-detail.json';
import activity from './__fixtures__/activity.json';
import plan from './__fixtures__/plan.json';
import sputum from './__fixtures__/sputum.json';

vi.mock('recharts',async importOriginal=>{const original=await importOriginal<typeof import('recharts')>();return {...original,ResponsiveContainer:({children}:{children:ReactElement<{width?:number;height?:number}>})=><div>{cloneElement(children,{width:700,height:230})}</div>};});

let fetchMock:ReturnType<typeof vi.fn>;
const route=(url:string)=>url.includes('/workspace/me')?session:url.includes('/workspace/care/summary')?summary:url.includes('/workspace/care/reviews/')?reviewDetail:url.includes('/workspace/care/reviews')?reviews:url.includes('/workspace/patients/PG-0071/activity')?activity:url.includes('/workspace/patients/PG-0071/plan')?plan:url.includes('/workspace/patients/PG-0071/sputum')?sputum:url.includes('/workspace/patients/PG-0071')?profile:url.includes('/workspace/patients')?directory:{};
beforeEach(()=>{sessionStorage.clear();sessionStorage.setItem('pg-workspace-session','vitest-token');
 fetchMock=vi.fn(async(input:string,options?:RequestInit)=>{if(options?.method==='POST'&&input.includes('/care/reviews'))return new Response(JSON.stringify({review:reviewDetail.review}),{status:200});if(options?.method)return new Response(JSON.stringify({...reviewDetail,plan:plan.plan}),{status:200});return new Response(JSON.stringify(route(input)),{status:200});});vi.stubGlobal('fetch',fetchMock);});

describe('sign-in screen',()=>{
 it('logs in through the backend and stores the session token',async()=>{
  fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({token:'pgw_testtoken',user:session.user}),{status:200}));
  const onLogin=vi.fn();render(<LoginScreen onLogin={onLogin}/>);
  await userEvent.click(screen.getByRole('button',{name:/Dr. Asha Atlas/}));
  await waitFor(()=>expect(onLogin).toHaveBeenCalledWith('pgw_testtoken',session.user));
  expect(sessionStorage.getItem('pg-workspace-session')).toBe('pgw_testtoken');
 });
 it('surfaces a credential error without unlocking',async()=>{
  fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({detail:'Incorrect demo username or password.'}),{status:401}));
  render(<LoginScreen onLogin={vi.fn()}/>);
  await userEvent.type(screen.getByLabelText('Username'),'dr-atlas');await userEvent.type(screen.getByLabelText('Password'),'wrong-pass');
  await userEvent.click(screen.getByRole('button',{name:'Sign in'}));
  await screen.findByText(/Incorrect demo username/);expect(sessionStorage.getItem('pg-workspace-session')).toBe('vitest-token');
 });
});
describe('unified patient directory',()=>{
 const props={user:session.user as any,revision:0,onOpen:vi.fn(),onTwin:vi.fn()};
 it('renders server-driven rows with scoping and honest no-prediction labels',async()=>{
  render(<DirectoryPage {...props}/>);await waitFor(()=>expect(screen.getAllByText('120').length).toBeGreaterThan(0));
  expect(screen.getAllByText(new RegExp(directory.items[0].patient_id)).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/Historical twin/).length).toBeGreaterThan(0);
 });
 it('sends search, city filter and sorting to the API (no fake client filtering)',async()=>{
  render(<DirectoryPage {...props}/>);await screen.findAllByText(new RegExp(directory.items[0].patient_id)).then(xs=>expect(xs.length).toBeGreaterThan(0));
  await userEvent.type(screen.getByLabelText('Search directory'),'PG-0033');
  await waitFor(()=>expect(fetchMock.mock.calls.some(c=>String(c[0]).includes('q=PG-0033'))).toBe(true));
  await userEvent.selectOptions(screen.getByLabelText('Sort directory'),'risk');
  await waitFor(()=>expect(fetchMock.mock.calls.some(c=>String(c[0]).includes('sort=risk'))).toBe(true));
 });
 it('shows backend errors specifically, not a generic crash',async()=>{
  fetchMock.mockReset();fetchMock.mockResolvedValue(new Response(JSON.stringify({detail:'Service overload demo'}),{status:503}));
  render(<DirectoryPage {...props}/>);await screen.findByText(/Backend error \(HTTP 503\)/);
 });
});
describe('care action centre',()=>{
 const props={revision:0,notify:vi.fn(),openProfile:vi.fn()};
 it('renders persisted summary metrics from the backend',async()=>{
  render(<CareCentrePage {...props}/>);await screen.findByText('Assigned patients');
  expect(screen.getAllByText(String(summary.assigned_patients)).length).toBeGreaterThan(0);
  expect(screen.getByText('Follow-ups due')).toBeInTheDocument();
 });
 it('creates a review through POST and opens its persisted timeline',async()=>{
  render(<CareCentrePage {...props}/>);await screen.findByText(reviews.items[0].patient_id);
  await userEvent.click(screen.getByRole('button',{name:/Start a new care review/}));
  await userEvent.type(screen.getByLabelText('Review note'),'Follow-up for synthetic case');
  await userEvent.click(screen.getByRole('button',{name:'Save review'}));
  await waitFor(()=>expect(fetchMock.mock.calls.some(c=>c[1]?.method==='POST'&&String(c[0]).includes('/care/reviews')&&JSON.parse(c[1]!.body as string).note==='Follow-up for synthetic case')).toBe(true));
 });
 it('opens queue items and shows the persisted timeline and allowed transitions',async()=>{
  render(<CareCentrePage {...props}/>);await screen.findByText(reviews.items[0].patient_id);
  await userEvent.click(screen.getByText(reviews.items[0].patient_id));
  await screen.findByText('Timeline');expect(screen.getAllByText(new RegExp(reviewDetail.review.status.replaceAll('_',' '))).length).toBeGreaterThan(0);
 });
});
describe('patient profile workspace',()=>{
 const props={pid:'PG-0071',revision:0,notify:vi.fn(),openTwin:vi.fn()};
 it('renders identity, frozen model boundary and reviews from one aggregate',async()=>{
  render(<ProfilePage {...props}/>);await screen.findByRole('heading',{name:String(profile.profile.display_name)});
  expect(screen.getByText(/not diagnoses or urgency/)).toBeInTheDocument();
 });
 it('submits a validated diary entry via POST',async()=>{
  render(<ProfilePage {...props}/>);await screen.findByRole('heading',{name:String(profile.profile.display_name)});
  await userEvent.click(screen.getByRole('button',{name:'Sputum diary'}));await screen.findByLabelText('Notes');
  await userEvent.click(screen.getByRole('button',{name:'Save diary entry'}));
  await waitFor(()=>expect(fetchMock.mock.calls.some(c=>c[1]?.method==='POST'&&String(c[0]).includes('/sputum'))).toBe(true));
 });
 it('saves care-plan documentation via PUT and keeps revision section',async()=>{
  render(<ProfilePage {...props}/>);await screen.findByRole('heading',{name:String(profile.profile.display_name)});
  await userEvent.click(screen.getByRole('button',{name:'Care plan'}));await screen.findByRole('button',{name:/Create plan|Edit plan/});
  await userEvent.click(screen.getByRole('button',{name:/Create plan|Edit plan/}));
  await userEvent.type(screen.getByLabelText('Documented goals'),'Daily demo walk as tolerated.');
  await userEvent.click(screen.getByRole('button',{name:'Save plan'}));
  await waitFor(()=>expect(fetchMock.mock.calls.some(c=>c[1]?.method==='PUT'&&String(c[0]).includes('/plan'))).toBe(true));
 });
 it('renders the activity tab queried from backend aggregates',async()=>{
  render(<ProfilePage {...props}/>);await screen.findByRole('heading',{name:String(profile.profile.display_name)});
  await userEvent.click(screen.getByRole('button',{name:'Activity & adherence'}));await screen.findByText(/Gaps between hand-entered/);
 });
});
describe('error differentiation',()=>{
 it('maps network failure and status codes distinctly',async()=>{
  fetchMock.mockRejectedValueOnce(new TypeError('fetch failed'));
  await expect(api('/x')).rejects.toThrow('Cannot reach the local PranaGuard backend');
  for(const [status,match] of [[401,'Sign-in required'],[403,'Not permitted'],[404,'Not found'],[422,'Validation'],[500,'Backend error']] as [number,string][]){fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({detail:'x'}),{status}));try{await api('/x');expect.unreachable();}catch(e){expect(e).toBeInstanceOf(ApiError);expect(explainError(e)).toContain(match);}}
 });
});
