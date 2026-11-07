import {useState} from 'react';
import {FileText,HeartPulse,Home,LogOut,Menu,ShieldCheck,Waves} from 'lucide-react';
import {PatientHomePage} from './PatientHome';
import {PatientRecordsPage} from './Records';
import {PatientDocumentsPage} from './Documents';
import type {SessionUser} from './types';

type PatientView='patient-home'|'patient-records'|'patient-docs';
const items:{id:PatientView;label:string;icon:typeof Home;sub:string}[]=[
 {id:'patient-home',label:'Patient Home',icon:Home,sub:'Your day at a glance'},
 {id:'patient-records',label:'My Health Records',icon:HeartPulse,sub:'Daily entries & history'},
 {id:'patient-docs',label:'Clinical Documents',icon:FileText,sub:'Records shared by your doctor'}];
const titles:Record<PatientView,[string,string]>={
 'patient-home':['Patient Home','A simple view of your fictional demo record and what your doctor has shared.'],
 'patient-records':['My Health Records','Log daily wellbeing, sputum diary and medication adherence. Your doctor sees the same entries.'],
 'patient-docs':['Clinical Documents','Prescriptions and records your doctor has shared with you. Read-only.']};

export function PatientShell({user,logout}:{user:SessionUser;logout:()=>void}){
 const [view,setView]=useState<PatientView>(()=>{const v=location.hash.slice(1)as PatientView;return items.some(i=>i.id===v)?v:'patient-home';});
 const [menu,setMenu]=useState(false);
 const navigate=(v:PatientView)=>{setView(v);location.hash=v;setMenu(false);};
 return <div className="app-shell pg-enhanced"><aside className={`sidebar patient-side ${menu?'mobile-open':''}`}>
  <a className="brand" href="#patient-home" onClick={()=>navigate('patient-home')}><span className="brand-mark"><Waves size={25}/></span><div>prana<span>guard</span><small>BODY × ENVIRONMENT</small></div></a>
  <div className="workspace-label">MY RECORD <span>DEMO</span></div>
  <nav>{items.map(({id,label,icon:Icon})=><button key={id} aria-label={label} onClick={()=>navigate(id)} className={view===id?'active':''}><Icon size={18}/><span>{label}</span>{view===id&&<span className="nav-active-dot"/>}</button>)}</nav>
  <div className="sidebar-lower"><div className="safety-side"><ShieldCheck size={16}/><div>SYNTHETIC DEMO RECORD<p>Not medical advice. Emergencies: follow your real action plan.</p></div></div>
   <div className="workspace-user"><div className="user-avatar">{user.display_name.split(' ').slice(0,2).map(w=>w[0].replace('.','')).join('')}</div><div><strong>{user.display_name}</strong><small>Patient demo · linked to Dr. Asha Atlas</small></div></div>
   <button className="button secondary w-full" onClick={logout}><LogOut size={14}/>Sign out</button></div></aside>
 <div className="main-shell"><header className="topbar"><div className="breadcrumb"><button className="mobile-menu icon-button" aria-label="Open navigation" onClick={()=>setMenu(!menu)}><Menu size={20}/></button><span>My record</span><strong>{items.find(n=>n.id===view)?.label}</strong></div>
  <div className="topbar-right"><button className="icon-button" aria-label={`Sign out (${user.display_name})`} onClick={logout}><LogOut size={16}/></button></div></header>
 <main><div className="page-heading"><div><h1>{titles[view][0]}</h1><p>{titles[view][1]}</p></div></div>
  {view==='patient-home'&&<PatientHomePage navigate={navigate}/>}
  {view==='patient-records'&&<PatientRecordsPage/>}
  {view==='patient-docs'&&<PatientDocumentsPage/>}
 <footer className="main-footer"><span>PranaGuard · synthetic proof of concept</span><span>Shared with Dr. Asha Atlas (demo)</span></footer></main></div></div>;
}
