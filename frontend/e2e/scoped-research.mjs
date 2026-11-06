// Read-only checks against a disposable synthetic database containing the
// assigned historical cohort and a different doctor's unassigned fiction.
import {chromium} from 'playwright-core';
import {createRequire} from 'node:module';
const {E2E_BASE:base,E2E_DOCTOR:doctor,E2E_DOCTOR_PASSWORD:password,E2E_CHROMIUM_PATH:executablePath,E2E_UNASSIGNED_PATIENT:foreignId}=process.env;
if(!base||!doctor||!password||!executablePath||!foreignId)throw new Error('Explicit disposable scoped research configuration required');
const browser=await chromium.launch({executablePath,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote','--single-process']});
const page=await browser.newPage();
const check=(ok,message)=>{if(!ok)throw new Error(message)};
try{
 await page.goto(base+'/doctor/login');await page.getByLabel('Username').fill(doctor);await page.getByLabel('Password',{exact:true}).fill(password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.waitForURL('**/doctor/dashboard');
 const token=await page.evaluate(()=>sessionStorage.getItem('pg-portal-token'));check(token,'No doctor session');
 const headers={Authorization:`Bearer ${token}`};
 const overview=await page.request.get(base+'/api/overview',{headers});check(overview.status()===200,'Historical cohort unavailable');
 const cohort=await overview.json();check(cohort.patients.length===120,'Historical cohort count changed');check(cohort.patients.every(p=>p.patient_id!==foreignId),'Unassigned record appeared in cohort');
 const registryResponse=await page.request.get(base+'/api/enhanced/registry/patients',{headers});
 check(registryResponse.status()===200,'Assigned registry unavailable');
 const registry=await registryResponse.json();check(registry.patients.some(p=>p.patient_id==='PG-0001')&&registry.patients.every(p=>p.patient_id!==foreignId),'Registry assignment isolation failed');
 check((await page.request.get(base+`/api/enhanced/registry/patients/${encodeURIComponent(foreignId)}`,{headers})).status()===404,'Unassigned registry record must be denied');
 const alertsResponse=await page.request.get(base+'/api/alerts',{headers});check(alertsResponse.status()===200,'Scoped alerts unavailable');
 const alerts=await alertsResponse.json();check(alerts.alerts.every(a=>a.patient_id!==foreignId),'Unassigned alert appeared');
 check((await page.request.get(base+'/api/alerts?patient_id='+encodeURIComponent(foreignId),{headers})).status()===404,'Unassigned alert filter must be denied');
 check((await page.request.get(base+`/api/patients/${encodeURIComponent(foreignId)}`,{headers})).status()===404,'Unassigned historical lookup must be denied');
 check((await page.request.get(base+`/api/portal/patients/${encodeURIComponent(foreignId)}`,{headers})).status()===404,'Unassigned portal record must be denied');
 await page.getByRole('heading',{name:'Your patient cohort'}).waitFor();
 const context=await page.request.get(base+'/api/enhanced/environment/Pune',{headers});check(context.status()===200,'City context unavailable to assigned research doctor');
 const contextBody=await context.json();check(contextBody.scope.includes('not station observation or personal exposure'),'City context scope missing');
 const noticesResponse=await page.request.get(base+'/api/enhanced/notifications?limit=500',{headers});check(noticesResponse.status()===200,'Scoped notifications unavailable');
 const notices=await noticesResponse.json();check(notices.notifications.every(n=>n.patient_id!==foreignId),'Unassigned notification appeared');
 check((await page.request.get(base+'/api/enhanced/notifications?patient_id='+encodeURIComponent(foreignId),{headers})).status()===404,'Unassigned notification filter must be denied');
 if(process.env.E2E_FOREIGN_NOTIFICATION&&process.env.E2E_ASSIGNED_NOTIFICATION){
  const foreign=process.env.E2E_FOREIGN_NOTIFICATION,assigned=process.env.E2E_ASSIGNED_NOTIFICATION;
  check((await page.request.get(base+`/api/enhanced/notifications/${foreign}`,{headers})).status()===404,'Unassigned notification detail must be denied');
  check((await page.request.patch(base+`/api/enhanced/notifications/${foreign}`,{headers,data:{status:'resolved'}})).status()===404,'Unassigned notification review must be denied');
  await page.getByRole('button',{name:'Notifications',exact:true}).click();
  await page.getByRole('button',{name:`Open notification ${assigned}`}).waitFor();
  if(process.env.E2E_SCAN_A11Y==='1'){
   await page.addScriptTag({path:createRequire(import.meta.url).resolve('axe-core/axe.min.js')});
   for(const width of [390,768,1440]){
    await page.setViewportSize({width,height:900});await page.waitForTimeout(250);
    const result=await page.evaluate(async()=>({violations:(await window.axe.run(document)).violations.map(v=>v.id),overflow:document.documentElement.scrollWidth>innerWidth+1}));
    check(!result.violations.length&&!result.overflow,`Notification UI at ${width}px: ${JSON.stringify(result)}`);
   }
   console.log('PASS: scoped notification screen axe/overflow checks at 390, 768 and 1440px.');
  }
  check(!(await page.getByRole('button',{name:`Open notification ${foreign}`}).count()),'Unassigned notification appeared in UI');
  await page.getByRole('button',{name:`Open notification ${assigned}`}).click();
  const acknowledge=page.getByRole('button',{name:'Acknowledge notification'});
  if(await acknowledge.count()){await acknowledge.click();check((await (await page.request.get(base+`/api/enhanced/notifications/${assigned}`,{headers})).json()).status==='acknowledged','Assigned notification review failed');}
  else{await page.getByRole('button',{name:'Mark unread'}).click();check((await (await page.request.get(base+`/api/enhanced/notifications/${assigned}`,{headers})).json()).unread,'Assigned notification read-state update failed');}
 }
 const validation=await page.request.get(base+'/api/validation',{headers});check(validation.status()===200,'Historical validation unavailable');
 check(!await page.getByText(foreignId,{exact:false}).count(),'Unassigned ID appeared in workspace');
 console.log('PASS: original 120-twin view and assigned notifications remain available without exposing another doctor’s record; unscoped operations remain gated and city context is explicitly labelled.');
}finally{await browser.close()}
