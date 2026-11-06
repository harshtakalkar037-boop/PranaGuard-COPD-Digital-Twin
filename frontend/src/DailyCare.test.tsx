import {render,screen,waitFor,within} from '@testing-library/react';
import {afterEach,describe,it,expect,vi} from 'vitest';
import {DailyPatient} from './DailyCare';

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
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>({ok:true,json:async()=>input.includes('care-plan')?{current:null,history:[]}:{logs:[]}})));
  render(<DailyPatient pid="PG-0001" doctor={false} revision={0} refresh={()=>{}}/>);
  await waitFor(()=>expect(screen.getByText("No personal hydration target has been set. Please follow your doctor's advice.")).toBeVisible());
 });
 it('shows errors rather than false zero progress or an absent target',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>({ok:false,json:async()=>({detail:'Unable to load'})})));
  render(<DailyPatient pid="PG-0001" doctor={false} revision={0} refresh={()=>{}}/>);
  await waitFor(()=>expect(screen.getAllByText('Unable to load').length).toBeGreaterThan(0));
  expect(screen.queryByText(/No personal hydration target has been set/)).not.toBeInTheDocument();
  expect(screen.queryByText(/0 meals recorded/)).not.toBeInTheDocument();
 });
});
