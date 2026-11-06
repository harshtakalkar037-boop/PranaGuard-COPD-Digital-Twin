import {render,screen} from '@testing-library/react';
import {describe,it,expect} from 'vitest';
import Portal from './Portal';

describe('portal entry points',()=>{
 it('renders the public landing page with separate access links',()=>{
  history.pushState({},'', '/');render(<Portal/>);
  expect(screen.getByRole('heading',{name:/Earlier awareness/})).toBeInTheDocument();
  expect(screen.getByRole('link',{name:/Enter Doctor Portal/})).toHaveAttribute('href','/doctor/login');
  expect(screen.getByRole('link',{name:/Enter Patient Portal/})).toHaveAttribute('href','/patient/login');
 });
 it('offers patient registration but not doctor self-registration',()=>{
  history.pushState({},'', '/patient/login');const {unmount}=render(<Portal/>);
  expect(screen.getByRole('button',{name:/Create a patient account/})).toBeInTheDocument();unmount();
  history.pushState({},'', '/doctor/login');render(<Portal/>);
  expect(screen.queryByRole('button',{name:/Create a patient account/})).not.toBeInTheDocument();
 });
});
