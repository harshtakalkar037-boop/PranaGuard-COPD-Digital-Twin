import {render,screen,renderHook,waitFor,act} from '@testing-library/react';
import {describe,it,expect,vi,afterEach} from 'vitest';
import Portal, {CareQueue,CompleteFollowup,usePortal} from './Portal';
import userEvent from '@testing-library/user-event';

afterEach(()=>vi.unstubAllGlobals());

describe('portal entry points',()=>{
 it('renders the public landing page with separate access links',()=>{
  history.pushState({},'', '/');render(<Portal/>);
  expect(screen.getByRole('heading',{name:/Understanding respiratory health/})).toBeInTheDocument();
  expect(screen.getByRole('link',{name:/Enter research workspace/})).toHaveAttribute('href','/doctor/login');
  expect(screen.getAllByRole('link',{name:/Patient access/})[0]).toHaveAttribute('href','/patient/login');
 });
 it('offers patient registration but not doctor self-registration',()=>{
  history.pushState({},'', '/patient/login');const {unmount}=render(<Portal/>);
  expect(screen.getByRole('button',{name:/Create a patient account/})).toBeInTheDocument();unmount();
  history.pushState({},'', '/doctor/login');render(<Portal/>);
  expect(screen.queryByRole('button',{name:/Create a patient account/})).not.toBeInTheDocument();
 });
});


describe('portal request isolation',()=>{
 it('clears loaded data when a refreshed authorization is denied',async()=>{
  const fetcher=vi.fn().mockResolvedValueOnce({ok:true,json:async()=>({patient:'one'})}).mockResolvedValueOnce({ok:false,status:403,json:async()=>({detail:'Denied'})});
  vi.stubGlobal('fetch',fetcher);
  const {result,rerender}=renderHook(({revision})=>usePortal<{patient:string}>('/patients/one',revision),{initialProps:{revision:0}});
  await waitFor(()=>expect(result.current.data).toEqual({patient:'one'}));
  rerender({revision:1});await waitFor(()=>expect(result.current.error).toBe('Permission denied (HTTP 403): Denied'));
  expect(result.current.data).toBeNull();
 });
 it('does not display late data from a previous or null patient path',async()=>{
  let resolve!: (value:unknown)=>void;const pending=new Promise(r=>{resolve=r});
  vi.stubGlobal('fetch',vi.fn().mockReturnValueOnce(pending));
  const {result,rerender}=renderHook(({path}:{path:string|null})=>usePortal<{patient:string}>(path,0),{initialProps:{path:'/patients/one' as string|null}});
  rerender({path:null});expect(result.current.data).toBeNull();
  await act(async()=>resolve({ok:true,json:async()=>({patient:'one'})}));expect(result.current.data).toBeNull();
 });
});


describe('follow-up completion',()=>{
 it('requires a private completion note and sends the selected review to the backend',async()=>{
  const fetcher=vi.fn().mockResolvedValue({ok:true,json:async()=>({message:'saved'})});vi.stubGlobal('fetch',fetcher);const refresh=vi.fn();
  render(<CompleteFollowup pid="PG-0001" reviewId={42} refresh={refresh}/>);
  await userEvent.click(screen.getByText('Complete dated follow-up'));
  expect(screen.getByRole('button',{name:'Record follow-up completion'})).toBeDisabled();
  await userEvent.type(screen.getByLabelText('Completion note'),'Recorded follow-up');
  await userEvent.click(screen.getByRole('button',{name:'Record follow-up completion'}));
  await waitFor(()=>expect(refresh).toHaveBeenCalledOnce());
  expect(fetcher).toHaveBeenCalledWith('/api/portal/patients/PG-0001/reviews/42/complete-followup',expect.objectContaining({method:'POST',body:JSON.stringify({notes:'Recorded follow-up'})}));
 });
 it('preserves the note and shows a server error if completion fails',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:409,json:async()=>({detail:'Follow-up is already completed'})}));const refresh=vi.fn();
  render(<CompleteFollowup pid="PG-0001" reviewId={42} refresh={refresh}/>);
  await userEvent.click(screen.getByText('Complete dated follow-up'));await userEvent.type(screen.getByLabelText('Completion note'),'Unsent note');await userEvent.click(screen.getByRole('button',{name:'Record follow-up completion'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('Follow-up is already completed');expect(refresh).not.toHaveBeenCalled();expect(screen.getByLabelText('Completion note')).toHaveValue('Unsent note');
 });
});


describe('assigned care queue',()=>{
 it('requests pages and filters from the server and selects a queue patient',async()=>{
  const fetcher=vi.fn(async(input:string)=>{
   const url=new URL(input,'http://localhost');const offset=Number(url.searchParams.get('offset'));const kind=url.searchParams.get('kind');
   const total=kind==='upload'?0:26;const items=kind==='upload'?[]:Array.from({length:offset?1:25},(_,i)=>({kind:'checkin',id:offset+i+1,patient_id:'PG-0001',timestamp:'2020-01-01T00:00:00Z',status:'Under Review'}));
   return new Response(JSON.stringify({items,limit:25,offset,total,has_more:offset+items.length<total,notice:'not urgency'}));
  });vi.stubGlobal('fetch',fetcher);const select=vi.fn();render(<CareQueue revision={0} selected="" select={select}/>);
  expect(await screen.findByText('Showing 1–25 of 26 items')).toBeVisible();expect(screen.getByRole('button',{name:'Previous queue page'})).toBeDisabled();
  await userEvent.click(screen.getByRole('button',{name:'Next queue page'}));await screen.findByText('Showing 26–26 of 26 items');expect(screen.getByRole('button',{name:'Next queue page'})).toBeDisabled();
  await userEvent.click(screen.getByRole('button',{name:/Symptom check-in.*PG-0001/}));expect(select).toHaveBeenCalledWith('PG-0001');
  await userEvent.selectOptions(screen.getByLabelText('Queue item type'),'upload');await screen.findByText('No open items or due follow-ups.');
  expect(fetcher.mock.calls.some(([url])=>String(url).includes('kind=upload')&&String(url).includes('offset=0'))).toBe(true);
  await userEvent.selectOptions(screen.getByLabelText('Queue order'),'oldest');await waitFor(()=>expect(fetcher.mock.calls.some(([url])=>String(url).includes('order=oldest'))).toBe(true));
 });
 it('shows permission failures rather than an empty queue',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:'Denied'}),{status:403})));
  render(<CareQueue revision={0} selected="" select={()=>{}}/>);expect(await screen.findByRole('alert')).toHaveTextContent('Permission denied');expect(screen.queryByText('No open items or due follow-ups.')).not.toBeInTheDocument();
 });
});
