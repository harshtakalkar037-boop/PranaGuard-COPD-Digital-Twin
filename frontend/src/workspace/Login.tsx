import {useState} from 'react';
import {Activity,ArrowDown,ArrowRight,ArrowUpRight,CheckCircle2,HeartPulse,Leaf,LockKeyhole,Mic,ShieldCheck,Sparkles,Wind,Waves} from 'lucide-react';
import {api,explainError} from '../api';
import type {SessionUser} from './types';

const DEMO_ACCOUNTS=[
 {username:'dr-atlas',password:'prana-atlas-demo',label:'Dr. Asha Atlas',role:'Clinician workspace',detail:'Explore the full 120-patient demonstration cohort',initials:'AA'},
 {username:'dr-nova',password:'prana-nova-demo',label:'Dr. Neil Nova',role:'Clinician workspace',detail:'Explore onboarding and patient assignment flows',initials:'NN'},
 {username:'pat-pg0071',password:'prana-patient-demo',label:'Patient 071',role:'Patient workspace',detail:'View a connected patient-side experience',initials:'P7'},
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
 return <div className="pg-landing">
  <header className="landing-nav">
   <a className="landing-brand" href="#top" aria-label="PranaGuard home"><span className="landing-brand-mark"><Waves size={23}/></span><span>prana<span>guard</span><small>BODY × ENVIRONMENT</small></span></a>
   <nav aria-label="Main navigation"><a href="#platform">Platform</a><a href="#approach">Our approach</a><a href="#team">Team</a></nav>
   <a className="landing-nav-cta" href="#sign-in">Launch workspace <ArrowUpRight size={15}/></a>
  </header>

  <main className="landing-main" id="top">
   <section className="landing-hero">
    <div className="landing-hero-copy">
     <div className="landing-kicker"><span className="landing-live-dot"/> DIGITAL TWIN CHALLENGE 2026 <span className="kicker-line"/></div>
     <h1>See the whole picture.<br/><em>Understand every change.</em></h1>
     <p className="landing-lead">A connected respiratory health experience bringing patient observations, personal baselines and environmental context into one clearer view.</p>
     <div className="landing-actions"><a className="landing-primary" href="#sign-in">Explore PranaGuard <ArrowRight size={17}/></a><a className="landing-secondary" href="#approach">Discover the approach <ArrowDown size={15}/></a></div>
     <div className="landing-proof"><span><CheckCircle2 size={15}/> Longitudinal context</span><span><CheckCircle2 size={15}/> Explainable research</span><span><CheckCircle2 size={15}/> Connected care workflow</span></div>
    </div>
    <div className="landing-visual" aria-label="Abstract respiratory digital twin illustration">
     <div className="visual-orbit orbit-one"/><div className="visual-orbit orbit-two"/>
     <div className="visual-glow"/>
     <div className="visual-core"><div className="core-ring"><HeartPulse size={54} strokeWidth={1.15}/></div><span>RESPIRATORY<br/>DIGITAL TWIN</span></div>
     <div className="visual-node node-a"><Activity size={17}/><span>Daily signals</span></div>
     <div className="visual-node node-b"><Wind size={17}/><span>Environment</span></div>
     <div className="visual-node node-c"><ShieldCheck size={17}/><span>Care context</span></div>
     <div className="visual-caption">BODY <b>×</b> ENVIRONMENT <span>CONNECTED INSIGHT</span></div>
    </div>
    <a className="scroll-cue" href="#platform"><span>SCROLL TO EXPLORE</span><ArrowDown size={14}/></a>
   </section>

   <section className="landing-marquee" aria-label="Platform principles"><span>PERSONAL BASELINES</span><i/> <span>LONGITUDINAL SIGNALS</span><i/> <span>ENVIRONMENTAL CONTEXT</span><i/> <span>CLINICIAN REVIEW</span></section>

   <section className="landing-section" id="platform">
    <div className="landing-section-heading"><div><span className="section-eyebrow">A MORE CONNECTED VIEW</span><h2>From scattered signals<br/>to <em>meaningful context.</em></h2></div><p>PranaGuard brings multiple dimensions of respiratory health together, so changes can be explored over time rather than viewed in isolation.</p></div>
    <div className="landing-feature-grid">
     <article className="landing-feature feature-dark"><span className="feature-icon"><Activity size={21}/></span><small>01 / LONGITUDINAL VIEW</small><h3>Follow the story<br/>over time.</h3><p>Explore changing observations, historical states and personal baselines in one continuous view.</p><div className="feature-art feature-chart"><span/><span/><span/><span/><span/><span/><span/></div></article>
     <article className="landing-feature feature-light"><span className="feature-icon"><Leaf size={21}/></span><small>02 / ENVIRONMENTAL CONTEXT</small><h3>Look beyond<br/>the individual signal.</h3><p>Bring city-level ambient context alongside respiratory observations, with source and freshness made visible.</p><div className="feature-art feature-waves"><Wind size={78} strokeWidth={.8}/></div></article>
     <article className="landing-feature feature-sage"><span className="feature-icon"><ShieldCheck size={21}/></span><small>03 / CONNECTED WORKFLOW</small><h3>Keep people<br/>in the loop.</h3><p>Connect patient-entered records with clinician review, shared documents and follow-up workflows.</p><div className="feature-art feature-pulse"><HeartPulse size={78} strokeWidth={.8}/></div></article>
    </div>
   </section>

   <section className="landing-approach" id="approach">
    <div className="approach-copy"><span className="section-eyebrow">THE PRANAGUARD APPROACH</span><h2>One journey.<br/><em>Connected perspectives.</em></h2><p>Designed to make the path from everyday observations to informed review easier to follow.</p></div>
    <div className="approach-steps"><div><b>01</b><span><strong>Observe</strong><small>Patient-entered signals and records</small></span></div><div><b>02</b><span><strong>Understand</strong><small>Baselines, trends and environmental context</small></span></div><div><b>03</b><span><strong>Review</strong><small>Explainable research and clinician workspace</small></span></div><div><b>04</b><span><strong>Follow through</strong><small>Connected records and care conversations</small></span></div></div>
   </section>

   <section className="landing-team" id="team"><div><span className="section-eyebrow">BUILT FOR DIGITAL TWIN CHALLENGE 2026</span><h2>Meet the <em>team.</em></h2><p>Exploring how connected digital experiences can bring more context to respiratory health.</p></div><div className="team-members"><div className="team-member"><span>HT</span><strong>Harsh Takalkar</strong><small>TEAM MEMBER</small></div><div className="team-plus">×</div><div className="team-member"><span>AN</span><strong>Anuja Naik</strong><small>TEAM MEMBER</small></div></div></section>

   <section className="landing-login-section" id="sign-in">
    <div className="login-section-copy"><span className="section-eyebrow">STEP INSIDE PRANAGUARD</span><h2>Your workspace<br/>is <em>ready.</em></h2><p>Choose a demonstration role or sign in with your workspace credentials to explore the platform.</p><div className="login-assurance"><LockKeyhole size={16}/><span>Secure session-based demo access<br/><small>Role-specific clinician and patient experiences</small></span></div></div>
    <div className="login-panel landing-login-panel">
     <div className="login-panel-heading"><span className="login-panel-icon"><Sparkles size={18}/></span><div><h2>Welcome back</h2><p>Sign in to your PranaGuard workspace</p></div></div>
     <div className="login-demo-list"><span className="login-list-label">QUICK ACCESS · SELECT A DEMO ROLE</span>
      {DEMO_ACCOUNTS.map(a=><button key={a.username} className="login-demo landing-demo" disabled={busy} onClick={()=>{setUsername(a.username);setPassword(a.password);submit(a.username,a.password);}}>
       <span className="demo-avatar">{a.initials}</span><span className="demo-copy"><strong>{a.label}</strong><small>{a.role} · {a.detail}</small></span><ArrowUpRight size={16} className="demo-arrow"/>
      </button>)}
     </div>
     <div className="login-divider"><span>OR SIGN IN WITH CREDENTIALS</span></div>
     <form onSubmit={e=>{e.preventDefault();submit();}}>
      <label className="field-label" htmlFor="login-username">Username</label><input id="login-username" className="form-input" autoComplete="username" value={username} onChange={e=>setUsername(e.target.value)} placeholder="Enter your username"/>
      <label className="field-label" htmlFor="login-password">Password</label><input id="login-password" className="form-input" type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Enter your password"/>
      {error&&<div className="error-banner" role="alert">{error}</div>}
      <button className="button primary w-full landing-submit" disabled={busy||username.length<3||password.length<6}>{busy?'Signing in…':'Sign in to workspace'}<ArrowRight size={16}/></button>
     </form>
     <p className="login-footnote">Demonstration accounts use generated sample records. This research prototype is not intended for clinical decision-making.</p>
    </div>
   </section>
  </main>
  <footer className="landing-footer"><a className="landing-brand footer-brand" href="#top"><span className="landing-brand-mark"><Waves size={20}/></span><span>prana<span>guard</span><small>BODY × ENVIRONMENT</small></span></a><div>Digital Twin Challenge 2026 <b>·</b> Harsh Takalkar &amp; Anuja Naik</div><a href="#top">Back to top ↑</a></footer>
 </div>;
}
