import {render,screen,waitFor} from '@testing-library/react';
import {afterEach,describe,expect,it,vi} from 'vitest';
import ResearchGate from './ResearchGate';
vi.mock('./App',()=>({default:()=> <div>Research workspace content</div>}));
describe('doctor research session gate',()=>{
 afterEach(()=>{sessionStorage.clear();vi.unstubAllGlobals()});
 it('checks a doctor session before rendering the workspace',async()=>{
  sessionStorage.setItem('pg-portal-token','test-token');
  const fetchMock=vi.fn(async(_url:string,_options?:RequestInit)=>new Response(JSON.stringify({role:'doctor',must_change_password:false}),{status:200}));
  vi.stubGlobal('fetch',fetchMock);render(<ResearchGate/>);
  expect(screen.getByText('Checking your session…')).toBeInTheDocument();
  expect(await screen.findByText('Research workspace content')).toBeInTheDocument();
  expect(fetchMock.mock.calls[0][1]).toEqual({headers:{Authorization:'Bearer test-token'}});
 });
 it('does not show research data if the session check fails',async()=>{
  sessionStorage.setItem('pg-portal-token','test-token');
  vi.stubGlobal('fetch',vi.fn(async()=>{throw new Error('Offline')}));
  render(<ResearchGate/>);
  await waitFor(()=>expect(screen.getByText('Unable to check your session')).toBeInTheDocument());
  expect(screen.queryByText('Research workspace content')).not.toBeInTheDocument();
 });
});
