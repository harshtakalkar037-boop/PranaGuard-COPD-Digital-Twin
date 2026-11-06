import {render,screen,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {describe,expect,it,vi} from 'vitest';
import {CohortRegistry} from './CohortRegistry';
import overview from './__fixtures__/overview.json';
import type {Patient} from './types';

const template=overview.patients[0] as Patient;
const records:Patient[]=[
 {...template,patient_id:'PG-A',display_name:'Synthetic A',city:'Pune',prediction_supported:true,risk_category:'elevated',risks:{'24':.1,'48':.3,'72':.2}},
 {...template,patient_id:'PG-B',display_name:'Synthetic B',city:'Delhi',prediction_supported:true,risk_category:'low',risks:{'24':.2,'48':.1,'72':.1}},
 {...template,patient_id:'PG-C',display_name:'Synthetic C',city:'Pune',prediction_supported:false,risk_category:'high',risks:{'24':.99,'48':.99,'72':.99}},
];
const renderRegistry=()=>render(<CohortRegistry patients={records} query="" setQuery={vi.fn()} onOpen={vi.fn()}/>);
const rowIds=()=>screen.getAllByRole('row').slice(1).map(r=>r.textContent);
describe('historical cohort registry',()=>{
 it('displays the three backend horizons and keeps unsupported estimates unavailable',()=>{
  renderRegistry();const rows=rowIds();expect(rows[0]).toContain('PG-A');expect(rows[1]).toContain('PG-B');expect(rows[2]).toContain('PG-C');
  expect(rows[0]).toContain('10.0%');expect(rows[0]).toContain('30.0%');expect(rows[0]).toContain('20.0%');
  expect(within(screen.getAllByRole('row')[3]).getAllByText('Unavailable')).toHaveLength(3);
 });
 it('names its action column and supports keyboard activation',async()=>{
  const onOpen=vi.fn();render(<CohortRegistry patients={records} query="" setQuery={vi.fn()} onOpen={onOpen}/>);
  expect(screen.getByRole('columnheader',{name:'Actions'})).toBeInTheDocument();const action=screen.getByRole('button',{name:'Open PG-A'});action.focus();await userEvent.keyboard('{Enter}');expect(onOpen).toHaveBeenCalledOnce();expect(onOpen).toHaveBeenCalledWith('PG-A');
 });
 it('sorts by the selected horizon and filters unsupported states separately',async()=>{
  renderRegistry();await userEvent.selectOptions(screen.getByLabelText('Sort historical cohort'),'risk24');expect(rowIds()[0]).toContain('PG-B');expect(rowIds()[2]).toContain('PG-C');
  await userEvent.click(screen.getByRole('button',{name:'High'}));expect(screen.getByText('No synthetic patients match these filters.')).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button',{name:'Unavailable'}));expect(rowIds()).toHaveLength(1);expect(rowIds()[0]).toContain('PG-C');
 });
});
