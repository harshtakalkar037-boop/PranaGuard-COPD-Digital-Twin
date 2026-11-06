import {render,screen,renderHook,waitFor,act} from '@testing-library/react';
import {describe,it,expect,vi,afterEach} from 'vitest';
import Portal, {usePortal} from './Portal';

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
