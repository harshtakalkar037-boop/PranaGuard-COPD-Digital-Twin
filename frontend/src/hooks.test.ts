import {act,renderHook,waitFor} from '@testing-library/react';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {api} from './api';
import {useRemote} from './hooks';

vi.mock('./api',()=>({api:vi.fn()}));
const mocked=vi.mocked(api);
function deferred<T>(){let resolve!:(value:T)=>void,reject!:(reason:Error)=>void;const promise=new Promise<T>((yes,no)=>{resolve=yes;reject=no});return {promise,resolve,reject}}
beforeEach(()=>mocked.mockReset());
describe('scoped remote data',()=>{
 it('clears the prior patient immediately on a path change and ignores late responses',async()=>{
  const first=deferred<{patient:string}>(),second=deferred<{patient:string}>();
  mocked.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
  const {result,rerender}=renderHook(({path})=>useRemote<{patient:string}>(path),{initialProps:{path:'/patients/one'}});
  rerender({path:'/patients/two'});expect(result.current.data).toBeNull();expect(result.current.loading).toBe(true);
  await act(async()=>first.resolve({patient:'one'}));expect(result.current.data).toBeNull();
  await act(async()=>second.resolve({patient:'two'}));await waitFor(()=>expect(result.current.data).toEqual({patient:'two'}));
 });
 it('does not show a loaded patient while the next patient is pending',async()=>{
  const next=deferred<{patient:string}>();mocked.mockResolvedValueOnce({patient:'one'}).mockReturnValueOnce(next.promise);
  const {result,rerender}=renderHook(({path})=>useRemote<{patient:string}>(path),{initialProps:{path:'/patients/one'}});
  await waitFor(()=>expect(result.current.data).toEqual({patient:'one'}));
  rerender({path:'/patients/two'});expect(result.current.data).toBeNull();expect(result.current.loading).toBe(true);
 });
 it('clears data and ignores late responses when the path becomes null',async()=>{
  const pending=deferred<{patient:string}>();mocked.mockReturnValueOnce(pending.promise);
  const {result,rerender}=renderHook(({path}:{path:string|null})=>useRemote<{patient:string}>(path),{initialProps:{path:'/patients/one' as string|null}});
  rerender({path:null});expect(result.current.data).toBeNull();expect(result.current.loading).toBe(false);
  await act(async()=>pending.resolve({patient:'one'}));expect(result.current.data).toBeNull();expect(mocked).toHaveBeenCalledTimes(1);
 });
 it('clears previously authorized data when a refresh is denied',async()=>{
  mocked.mockResolvedValueOnce({patient:'one'}).mockRejectedValueOnce(new Error('Record not found'));
  const {result,rerender}=renderHook(({revision})=>useRemote<{patient:string}>('/patients/one',revision),{initialProps:{revision:0}});
  await waitFor(()=>expect(result.current.data).toEqual({patient:'one'}));
  rerender({revision:1});await waitFor(()=>expect(result.current.error).toBe('Record not found'));
  expect(result.current.data).toBeNull();
 });
});
