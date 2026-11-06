import {afterEach,describe,expect,it,vi} from 'vitest';
import {handleExpiredSession} from './session';
afterEach(()=>sessionStorage.clear());
describe('expired session handling',()=>{
 it('clears the matching expired token and signals a redirect',()=>{
  const listener=vi.fn();window.addEventListener('pg-session-expired',listener);
  sessionStorage.setItem('pg-portal-token','old-token');
  expect(handleExpiredSession('old-token','Session expired or invalid')).toBe(true);
  expect(sessionStorage.getItem('pg-portal-token')).toBeNull();expect(sessionStorage.getItem('pg-session-expired')).toBe('1');expect(listener).toHaveBeenCalledTimes(1);
  window.removeEventListener('pg-session-expired',listener);
 });
 it('does not invalidate a newer session or a rejected demo write token',()=>{
  sessionStorage.setItem('pg-portal-token','new-token');
  expect(handleExpiredSession('old-token','Session expired or invalid')).toBe(false);
  expect(handleExpiredSession('new-token','Demo admin token required (X-Demo-Token).')).toBe(false);
  expect(sessionStorage.getItem('pg-portal-token')).toBe('new-token');
 });
});
