import '@testing-library/jest-dom/vitest';
import {cleanup} from '@testing-library/react';
import {afterEach,vi} from 'vitest';
afterEach(()=>{cleanup();vi.restoreAllMocks();sessionStorage.clear();location.hash='';});
class ResizeObserverMock {observe(){}unobserve(){}disconnect(){}}
vi.stubGlobal('ResizeObserver',ResizeObserverMock);
class SocketMock {onopen:((e:Event)=>void)|null=null;onclose:((e:Event)=>void)|null=null;onmessage:((e:MessageEvent)=>void)|null=null;close(){}send(){}}
vi.stubGlobal('WebSocket',SocketMock);
