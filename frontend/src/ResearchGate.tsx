import {useEffect,useState} from 'react';
import App from './App';

type Gate = 'loading'|'ready'|'error';
/** The UI gate complements, but never replaces, server-side authorization. */
export default function ResearchGate(){
 const [state,setState]=useState<Gate>('loading');
 useEffect(()=>{
  const token=sessionStorage.getItem('pg-portal-token');
  if(!token){location.replace('/doctor/login');return;}
  let active=true;
  fetch('/api/portal/me',{headers:{Authorization:`Bearer ${token}`}}).then(async r=>{
   if(r.status===401){sessionStorage.removeItem('pg-portal-token');location.replace('/doctor/login');return;}
   if(!r.ok)throw new Error('Unable to check the session');
   const user=await r.json();if(!active)return;
   if(user.role!=='doctor'){location.replace('/doctor/login');return;}
   if(user.must_change_password){location.replace('/doctor/care');return;}
   setState('ready');
  }).catch(()=>{if(active)setState('error')});
  return ()=>{active=false};
 },[]);
 if(state==='ready')return <App/>;
 return <main className="auth-page"><div className="auth-card">{state==='loading'?<p>Checking your session…</p>:<><h1>Unable to check your session</h1><p>Check your connection and try again.</p><button className="portal-button" onClick={()=>location.reload()}>Retry</button></>}</div></main>;
}
