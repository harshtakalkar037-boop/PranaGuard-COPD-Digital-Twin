import {render,screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {Model48Study} from './Study';
import fixture from './__fixtures__/study.json';
// Captured actual synthetic-study API response; controlled request doubles only.
let fetchMock:ReturnType<typeof vi.fn>;
beforeEach(()=>{fetchMock=vi.fn(async()=>new Response(JSON.stringify(fixture),{status:200}));vi.stubGlobal('fetch',fetchMock);});
describe('completed48h improvement study',()=>{
 it('shows rejection rather than falsely advertising an improved active model',async()=>{render(<Model48Study/>);await screen.findByText('NOT PROMOTED');expect(screen.getByText('Candidate not promoted — original 48h model retained.')).toBeInTheDocument();expect(screen.queryByRole('button',{name:/activate|deploy/i})).not.toBeInTheDocument();expect(screen.getByText('0.5539')).toBeInTheDocument();expect(screen.getByText('0.5494')).toBeInTheDocument();});
 it('reports both metric directions, cohort size and acceptance failures',async()=>{render(<Model48Study/>);await screen.findByRole('table',{name:'Fresh cohort 48h model comparison'});expect(screen.getByText('0.1485')).toBeInTheDocument();expect(screen.getByText('0.1099')).toBeInTheDocument();expect(screen.getAllByText('NOT MET')).toHaveLength(3);expect(screen.getByText(/23278 eligible hourly forecasts/)).toBeInTheDocument();});
 it('makes all eight development candidates inspectable without test tuning',async()=>{render(<Model48Study/>);await screen.findByText('Development candidates and uncertainty');await userEvent.click(screen.getByText('Development candidates and uncertainty'));expect(screen.getByText('core_linear_C0.3 · selected')).toBeVisible();for(const c of fixture.candidates)expect(screen.getByText(c.candidate,{exact:c.candidate!==fixture.study.selected_candidate})).toBeInTheDocument();});
 it('does not fabricate metrics when the study request fails',async()=>{fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({detail:'Controlled unavailable study'}),{status:503}));render(<Model48Study/>);await screen.findByRole('alert');expect(screen.getByText(/Controlled unavailable study/)).toBeInTheDocument();expect(screen.queryByText('0.5494')).not.toBeInTheDocument();});
});
