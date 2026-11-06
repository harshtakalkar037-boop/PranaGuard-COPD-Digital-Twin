import {render,screen,waitFor,fireEvent} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {cloneElement} from 'react';
import type {ReactElement} from 'react';
import App from './App';
import {api} from './api';
import overview from './__fixtures__/overview.json';
import twin from './__fixtures__/twin.json';
import history from './__fixtures__/history.json';
import explanation from './__fixtures__/explanation.json';
import validation from './__fixtures__/validation.json';
import status from './__fixtures__/status.json';
import scenario from './__fixtures__/scenario.json';
vi.mock('recharts',async importOriginal=>{const original=await importOriginal<typeof import('recharts')>();return {...original,ResponsiveContainer:({children}:{children:ReactElement<{width?:number;height?:number}>})=><div>{cloneElement(children,{width:700,height:250})}</div>};});
let fetchMock:ReturnType<typeof vi.fn>;
beforeEach(()=>{
 const responses=(url:string)=>url.includes('/overview')?overview:url.includes('/history')?history:url.includes('/explanation')?explanation:url.includes('/validation')?validation:url.includes('/status')?status:url.includes('/interventions')?{interventions:[]}:url.includes('/alerts')?{alerts:[]}:url.includes('/scenarios')?{scenarios:[]}:url.includes('/replay')?overview.replay:twin;
 fetchMock=vi.fn(async(input:string,options?:RequestInit)=>new Response(JSON.stringify(options?.method==='POST'&&input.includes('/scenarios')?scenario:responses(input)),{status:200}));vi.stubGlobal('fetch',fetchMock);
});
const ready=async()=>{render(<App/>);await screen.findByRole('heading',{name:'Your patient cohort'});};
describe('backend-fed dashboard',()=>{
 it('renders the real captured cohort response and explicit synthetic labels',async()=>{await ready();expect(screen.getByText('120')).toBeInTheDocument();expect(screen.getByText('93')).toBeInTheDocument();expect(screen.getByText('SYNTHETIC PATIENTS ONLY')).toBeInTheDocument();});
 it('filters patient search without invented rows',async()=>{await ready();await userEvent.type(screen.getByLabelText('Search patients'),'PG-0071');expect(screen.getByRole('button',{name:'Open PG-0071'})).toBeInTheDocument();expect(screen.queryByRole('button',{name:'Open PG-0050'})).not.toBeInTheDocument();});
 it('shows an empty search result honestly',async()=>{await ready();await userEvent.type(screen.getByLabelText('Search patients'),'NOT-A-PATIENT');expect(screen.getByText('No synthetic patients match these filters.')).toBeInTheDocument();});
 it('paginates the complete backend cohort',async()=>{await ready();await userEvent.click(screen.getByRole('button',{name:'Next page'}));expect(screen.getByText('7–12 of 120 synthetic twins')).toBeInTheDocument();await userEvent.click(screen.getByRole('button',{name:'Previous page'}));expect(screen.getByText('1–6 of 120 synthetic twins')).toBeInTheDocument();});
 it('filters high risk accurately even when none exist',async()=>{await ready();await userEvent.click(screen.getByRole('button',{name:'High'}));expect(screen.getByText('No synthetic patients match these filters.')).toBeInTheDocument();});
 it('loads the patient state, baseline and persisted version control',async()=>{await ready();await userEvent.click(screen.getByRole('button',{name:'Patient twins'}));await screen.findByRole('heading',{name:'Personal baseline vs current'});expect(screen.getAllByText('PG-0071',{exact:false}).length).toBeGreaterThan(0);fireEvent.change(screen.getByLabelText('Twin state version'),{target:{value:'1'}});await waitFor(()=>expect(fetchMock.mock.calls.some(c=>String(c[0]).includes('?version=1'))).toBe(true));});
 it('loads real model drivers and switches prediction horizon',async()=>{await ready();await userEvent.click(screen.getByRole('button',{name:'Risk explainability'}));await screen.findByRole('heading',{name:'Local model drivers'});expect(screen.getByText('LightGBM native TreeSHAP')).toBeInTheDocument();await userEvent.click(screen.getByRole('button',{name:'24 hours'}));await waitFor(()=>expect(fetchMock.mock.calls.some(c=>String(c[0]).includes('horizon=24'))).toBe(true));});
 it('calls the scenario API and displays the saved calculated result',async()=>{await ready();await userEvent.click(screen.getByRole('button',{name:'What-if studio'}));await screen.findByRole('button',{name:'Run backend simulation'});fireEvent.change(screen.getByLabelText('PM2.5 change'),{target:{value:'-40'}});await userEvent.click(screen.getByRole('button',{name:'Run backend simulation'}));await screen.findByText('Original twin preserved');const call=fetchMock.mock.calls.find(c=>c[1]?.method==='POST'&&String(c[0]).includes('/scenarios'));expect(JSON.parse(call![1]!.body as string)).toEqual({pm25_change_pct:-40,adherence:.95,activity_multiplier:1});});
 it('displays executed validation results, including negative findings',async()=>{await ready();await userEvent.click(screen.getByRole('button',{name:'Model validation'}));await screen.findByRole('heading',{name:'Executed ablations'});expect(screen.getAllByText('0.3951')[0]).toBeInTheDocument();expect(screen.getByText(/below-chance discrimination/)).toBeInTheDocument();await userEvent.click(screen.getByRole('button',{name:'24-hour horizon'}));expect(screen.getAllByText('0.6916')[0]).toBeInTheDocument();});
 it('persists clinician notes using the backend endpoint',async()=>{await ready();await userEvent.click(screen.getByRole('button',{name:'Care activity'}));await screen.findByLabelText('Review note');expect(screen.getByRole('button',{name:'Save action'})).toBeDisabled();await userEvent.type(screen.getByLabelText('Review note'),'Reviewed synthetic case');await userEvent.click(screen.getByRole('button',{name:'Save action'}));await waitFor(()=>expect(fetchMock.mock.calls.some(c=>c[1]?.method==='POST'&&String(c[0]).includes('/interventions'))).toBe(true));});
 it('shows source provenance and saves an optional browser-session token',async()=>{await ready();await userEvent.click(screen.getByRole('button',{name:'System & data'}));await screen.findByRole('heading',{name:'Source freshness & provenance'});expect(screen.getByRole('link',{name:/interactive API docs/})).toHaveAttribute('href','/docs');await userEvent.type(screen.getByLabelText('Optional configured demo admin token'),'only-a-test');await userEvent.click(screen.getByRole('button',{name:'Save for this browser session'}));expect(sessionStorage.getItem('pg-demo-token')).toBe('only-a-test');});
 it('executes replay controls through POST, not fake local counters',async()=>{await ready();await userEvent.click(screen.getByRole('button',{name:'1h'}));await waitFor(()=>expect(fetchMock.mock.calls.some(c=>String(c[0]).includes('/replay/step')&&JSON.parse(c[1]!.body as string).hours===1)).toBe(true));});
});
describe('API error handling',()=>{
 it('reports backend validation errors',async()=>{fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({detail:'Assumption outside supported range'}),{status:422}));await expect(api('/test')).rejects.toThrow('Assumption outside supported range');});
 it('attaches only explicitly configured session authorization',async()=>{sessionStorage.setItem('pg-demo-token','test-token');await api('/health');expect(fetchMock.mock.calls[0][1]!.headers).toMatchObject({'X-Demo-Token':'test-token'});});
});
