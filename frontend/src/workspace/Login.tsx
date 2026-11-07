import {useState} from 'react';
import {HeartPulse,Leaf,ShieldCheck,Waves} from 'lucide-react';
import {api,explainError} from '../api';
import type {SessionUser} from './types';

const DEMO_ACCOUNTS=[
 {username:'dr-atlas',password:'prana-atlas-demo',label:'Dr. Asha Atlas',detail:'Demo clinician · full 120-twin synthetic panel'},
 {username:'dr-nova',password:'prana-nova-demo',label:'Dr. Neil Nova',detail:'Demo clinician · empty panel (assignment demo)'},
 {username:'pat-pg0071',password:'prana-patient-demo',label:'Twin 071 viewer',detail:'Demo patient view · own synthetic record only'},
];

export function LoginScreen({onLogin}:{onLogin:(token:string,user:SessionUser)=>void}){
 const [username,setUsername]=useState('');const [password,setPassword]=useState('');
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 async function submit(u=username,p=password){
  setBusy(true);setError('');
  try{
   const r=await api<{token:string;user:SessionUser}>('/workspace/login',{method:'POST',body:JSON.stringify({username:u,password:p})});
   sessionStorage.setItem('pg-workspace-session',r.token);onLogin(r.token,r.user);
  }catch(e){setError(explainError(e));}finally{setBusy(false);}
 }
 return <div className="login-shell"><div className="login-hero">
  <div className="login-brand"><span className="brand-mark"><Waves size={26}/></span><div>prana<span>guard</span><small>BODY × ENVIRONMENT</small></div></div>
  <h1>One workspace for every synthetic twin.</h1>
  <p>Digital-twin replay, model evidence, care review workflow, monitoring diaries and environmental context — unified behind a signed-in demo identity.</p>
  <div className="login-points"><div><HeartPulse size={16}/>Frozen research models & honest limitations</div><div><Leaf size={16}/>City ambient context, never personal exposure</div><div><ShieldCheck size={16}/>Synthetic patients only · demo authentication</div></div>
 </div>
 <div className="login-panel">
  <h2>Sign in</h2>
  <p className="input-help">This is a local synthetic demonstration. Accounts below are documented demo identities — no real credentials or patient data exist.</p>
  <div className="login-demo-list">
   {DEMO_ACCOUNTS.map(a=><button key={a.username} className="login-demo" disabled={busy} onClick={()=>{setUsername(a.username);setPassword(a.password);submit(a.username,a.password);}}>
    <strong>{a.label}</strong><span>{a.detail}</span><em>{a.username}</em></button>)}
  </div>
  <form onSubmit={e=>{e.preventDefault();submit();}}>
   <label className="field-label" htmlFor="login-username">Username</label>
   <input id="login-username" className="form-input" autoComplete="username" value={username} onChange={e=>setUsername(e.target.value)}/>
   <label className="field-label" htmlFor="login-password">Password</label>
   <input id="login-password" className="form-input" type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)}/>
   {error&&<div className="error-banner" role="alert">{error}</div>}
   <button className="button primary w-full" disabled={busy||username.length<3||password.length<6}>{busy?'Signing in…':'Sign in'}</button>
  </form>
  <p className="input-help">Demo passwords are in README.md and changeable via PRANAGUARD_DEMO_* environment variables on first boot. Sessions expire after 12 hours.</p>
 </div></div>;
}
