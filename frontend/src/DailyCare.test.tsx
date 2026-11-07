import {render,screen,waitFor,within} from '@testing-library/react';
import {afterEach,describe,it,expect,vi} from 'vitest';
import {DailyPatient,DailySummary,Provision,Sputum,LogHistory,PlanManagement} from './DailyCare';
import userEvent from '@testing-library/user-event';

describe('daily care safety and loading states',()=>{
 afterEach(()=>vi.unstubAllGlobals());
 it('shows the specified notices and does not claim there is no target while loading',async()=>{
  vi.stubGlobal('fetch',vi.fn(()=>new Promise(()=>{})));
  render(<DailyPatient pid="PG-0001" doctor={false} revision={0} refresh={()=>{}}/>);
  expect(screen.getByText("General food suggestions are for informational purposes only. Please follow your doctor's and dietitian's recommendations and check your prescribed dietary plan before making changes.")).toBeVisible();
  expect(screen.getByText('Hydration suggestions are general information. If your doctor has advised you to restrict fluids or follow a specific fluid plan, follow that prescription instead.')).toBeVisible();
  expect(screen.getByText("Only perform activities that are appropriate for you and approved by your healthcare professional. Stop if you feel unwell and follow your doctor's advice.")).toBeVisible();
  const water=screen.getByRole('heading',{name:'Water and hydration'}).closest('section')!;
  expect(within(water).getByText('Loading plan…')).toBeVisible();
  expect(screen.queryByText(/No personal hydration target has been set/)).not.toBeInTheDocument();
  expect(screen.getAllByText('Loading daily activity…').length).toBeGreaterThan(0);
 });
 it('shows the no-target notice only after a successful empty plan',async()=>{
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>({ok:true,json:async()=>input.includes('care-plan')?{current:null,history:[]}:input.includes('/history/')?{items:[],limit:25,offset:0,total:0,has_more:false}:{meals_recorded:0,water_ml:0,activities_completed:0}})));
  render(<DailyPatient pid="PG-0001" doctor={false} revision={0} refresh={()=>{}}/>);
  await waitFor(()=>expect(screen.getByText("No personal hydration target has been set. Please follow your doctor's advice.")).toBeVisible());
 });
 it('shows errors rather than false zero progress or an absent target',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>({ok:false,status:503,json:async()=>({detail:'Unable to load'})})));
  render(<DailyPatient pid="PG-0001" doctor={false} revision={0} refresh={()=>{}}/>);
  await waitFor(()=>expect(screen.getAllByText('Server error (HTTP 503): Unable to load').length).toBeGreaterThan(0));
  expect(screen.queryByText(/No personal hydration target has been set/)).not.toBeInTheDocument();
  expect(screen.queryByText(/0 meals recorded/)).not.toBeInTheDocument();
 });
});


it('does not display a late one-time credential after changing patient',async()=>{
 let resolve!: (value:unknown)=>void;vi.stubGlobal('fetch',vi.fn(()=>new Promise(r=>{resolve=r})));
 const {rerender}=render(<Provision key="one" pid="PG-0001"/>);
 await userEvent.click(screen.getByRole('button',{name:'Provision assigned patient'}));
 rerender(<Provision key="two" pid="PG-0002"/>);
 resolve({ok:true,json:async()=>({login_id:'PG-0001',patient_id:'PG-0001',assigned_doctor:'doc',status:'pending',temporary_password:'ephemeral-example-password',temporary_password_expires_at:'2099-01-01T00:00:00Z'})});
 await new Promise(r=>setTimeout(r,0));
 expect(screen.queryByText('One-time onboarding details')).not.toBeInTheDocument();expect(screen.getByText('PG-0002')).toBeInTheDocument();
});

describe('diary, activity and plan history pagination',()=>{
 it.each(['sputum','daily','plans'] as const)('requests older %s records and returns to the first page when filtered',async(kind)=>{
  const fetcher=vi.fn(async(input:string)=>{const url=new URL(input,'http://localhost'),offset=Number(url.searchParams.get('offset')),id=offset?1:26;
   const item=kind==='sputum'?{id,observed_at:'2020-01-01T00:00:00Z',colour:'clear',amount:'small',consistency:'thin',cough:'mild',description:offset?'Old diary record':'New diary record',review_status:'Pending Review',photos:[],reviews:[],edit_history:[]}:kind==='daily'?{id,kind:'meal',occurred_at:'2020-01-01T00:00:00Z',item:'Breakfast',status:'Completed',amount_ml:null,duration_minutes:null,effort:'',comments:offset?'Old activity record':'New activity record',review_status:'Pending Review',reviews:[]}:{id,title:offset?'Old version':'New version',created_at:'2020-01-01T00:00:00Z',active:1,start_date:'2020-01-01'};
   return new Response(JSON.stringify(url.pathname.endsWith('/care-plan')?{current:null,history:[]}:{items:[item],offset,limit:25,total:26,has_more:offset===0}));
  });vi.stubGlobal('fetch',fetcher);const props={pid:'PG-0001',doctor:true,revision:0,refresh:()=>{}};
  const {unmount}=render(kind==='sputum'?<Sputum {...props}/>:kind==='daily'?<LogHistory {...props}/>:<PlanManagement {...props}/>);
  const label=kind==='sputum'?'diary entries':kind==='daily'?'activities':'plan versions';
  await screen.findByRole('button',{name:`Next ${label} page`});await userEvent.click(screen.getByRole('button',{name:`Next ${label} page`}));
  expect(await screen.findByText(kind==='sputum'?'Old diary record':kind==='daily'?'Old activity record':/Old version · Active at this version/)).toBeVisible();
  if(kind==='sputum')await userEvent.selectOptions(screen.getByLabelText('Diary review status'),'Reviewed');
  if(kind==='daily')await userEvent.selectOptions(screen.getByLabelText('Activity type'),'hydration');
  if(kind!=='plans')await waitFor(()=>expect(fetcher.mock.calls.some(([url])=>String(url).includes('offset=0')&&String(url).includes(kind==='sputum'?'review_status=Reviewed':'activity_kind=hydration'))).toBe(true));
  unmount();
 });
});


it('uses complete server totals and sends a bounded local-day interval',async()=>{
 const fetcher=vi.fn(async(_input:string)=>new Response(JSON.stringify({meals_recorded:501,water_ml:200,activities_completed:1}))); vi.stubGlobal('fetch',fetcher);render(<DailySummary pid="PG-0001" revision={0} checkinToday={false}/>);
 expect(await screen.findByText(/501 meals recorded · 200 mL water recorded · 1 activities completed/)).toBeVisible();
 const u=new URL(fetcher.mock.calls[0][0] as string,'http://localhost');expect(u.pathname).toBe('/api/portal/patients/PG-0001/daily-summary');
 const start=new Date(u.searchParams.get('start')!).getTime(),end=new Date(u.searchParams.get('end')!).getTime();expect(end-start).toBeGreaterThanOrEqual(23*3600000);expect(end-start).toBeLessThanOrEqual(25*3600000);
});


it('shows invalid daily totals as an error rather than inventing progress',async()=>{
 vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({water_ml:200}))));render(<DailySummary pid="PG-0001" revision={0} checkinToday={false}/>);
 expect(await screen.findByRole('alert')).toHaveTextContent('Invalid daily summary response');expect(screen.queryByText(/meals recorded/)).not.toBeInTheDocument();
});
