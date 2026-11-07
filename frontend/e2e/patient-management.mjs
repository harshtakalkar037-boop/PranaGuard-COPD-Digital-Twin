// Mutates only an explicitly configured disposable synthetic database.
import {chromium} from 'playwright-core';
import {createRequire} from 'node:module';
const {E2E_BASE:base,E2E_DOCTOR:doctor,E2E_DOCTOR_PASSWORD:password,E2E_CHROMIUM_PATH:exe}=process.env;
if(!base||!doctor||!password||!exe)throw new Error('Explicit disposable synthetic demo and Chromium configuration required');
const pid=process.env.E2E_PATIENT_ID||'PG-0001',unassigned=process.env.E2E_UNASSIGNED_PATIENT||'PG-0002';
const browser=await chromium.launch({executablePath:exe,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote','--single-process']});
const page=await browser.newPage({viewport:{width:1440,height:900}});page.setDefaultTimeout(20000);
const check=(condition,message)=>{if(!condition)throw Error(message)};
try{
 await page.goto(base+'/doctor/login');await page.getByLabel('Username').fill(doctor);await page.getByLabel('Password',{exact:true}).fill(password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.getByRole('heading',{name:'Your patient cohort'}).waitFor();
 const token=await page.evaluate(()=>sessionStorage.getItem('pg-portal-token'));const headers={Authorization:`Bearer ${token}`};
 await page.getByLabel('Global patient search').fill(pid);await page.getByLabel('Search registry by patient ID').waitFor();await page.getByRole('button',{name:`Open profile ${pid}`}).click();await page.getByRole('heading',{name:'Care and account access'}).waitFor();
 await page.reload();await page.getByRole('heading',{name:'Care and account access'}).waitFor();
 const axe=createRequire(import.meta.url).resolve('axe-core/axe.min.js');await page.addScriptTag({path:axe});
 for(const width of [390,768,1440]){await page.setViewportSize({width,height:900});await page.waitForTimeout(300);check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`Patient profile overflow at ${width}`);const violations=await page.evaluate(async()=>{const a=await window.axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}});return a.violations.map(v=>`${v.id}: ${v.nodes.map(n=>`${n.target.join(' ')} ${n.failureSummary}`).join('; ')}`)});check(!violations.length,`Patient profile accessibility violations at ${width}: ${violations.join(', ')}`);}
 await page.getByRole('button',{name:'Provision assigned patient'}).click();await page.getByText('One-time onboarding details').waitFor();const credential=await page.locator('.portal-success p').filter({hasText:'Temporary password:'}).locator('strong').innerText();check(credential.length>=20,'Temporary credential missing');await page.getByRole('button',{name:'Dismiss credential'}).click();check(await page.getByText('One-time onboarding details').count()===0,'Credential not dismissed');
 const review=await page.request.post(`${base}/api/portal/patients/${pid}/reviews`,{headers,data:{status:'Follow-up Required',notes:'Synthetic follow-up verification',follow_up:'Research test only',follow_up_date:'2000-01-01',shared:false}});check(review.status()===201,'Could not create synthetic review');const rid=(await review.json()).id;
 let queue=await (await page.request.get(base+'/api/portal/care-queue',{headers})).json();check(queue.items.some(i=>i.kind==='followup'&&i.id===rid),'Dated follow-up missing from queue');
 await page.getByRole('button',{name:'Open care record'}).click();await page.getByText(`Selected patient: ${pid}`).waitFor();await page.reload();await page.getByText(`Selected patient: ${pid}`).waitFor();
 const entry=page.locator('section.portal-card').filter({has:page.getByRole('heading',{name:'Review history',exact:true})}).locator('.portal-item').filter({hasText:'Synthetic follow-up verification'});await entry.getByText('Complete dated follow-up').click();await entry.getByLabel('Completion note').fill('Synthetic completion recorded');await entry.getByRole('button',{name:'Record follow-up completion'}).click();await entry.getByText(/Follow-up completion recorded/).waitFor();
 queue=await (await page.request.get(base+'/api/portal/care-queue',{headers})).json();check(!queue.items.some(i=>i.kind==='followup'&&i.id===rid),'Completed follow-up remained in queue');
 check((await page.request.post(`${base}/api/portal/patients/${unassigned}/reviews/${rid}/complete-followup`,{headers,data:{notes:'Not authorized'}})).status()===404,'Cross-patient completion allowed');
 await page.getByRole('button',{name:'Patients',exact:true}).click();await page.getByRole('button',{name:'All synthetic patients'}).click();await page.getByRole('button',{name:'Add fictional patient'}).click();
 await page.getByLabel('Fictional alias',{exact:true}).fill('Research Example');await page.getByLabel('Demo age (18–100)').fill('58');await page.getByRole('checkbox',{name:/I confirm that all identity/}).check();
 const save=page.waitForResponse(r=>r.url().endsWith('/api/enhanced/registry/patients')&&r.request().method()==='POST');await page.getByRole('button',{name:'Save fictional patient'}).click();const saved=await save;check(saved.ok(),'Registration failed');const newId=(await saved.json()).patient_id;
 await page.getByText('No 24/48/72h prediction is available for this registration.').waitFor();await page.getByRole('button',{name:'Open care record'}).click();await page.getByText(`Selected patient: ${newId}`).waitFor();await page.getByRole('heading',{name:'Fictional patient profile'}).waitFor();
 console.log('PASS: global patient search, profile reload, provisioning, care navigation, private follow-up completion, queue update, cross-patient denial, fictional registration and three axe/overflow scans');
}finally{await browser.close()}
