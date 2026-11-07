// Read-only against a deliberately populated disposable synthetic fixture.
import {chromium} from 'playwright-core';
import {createRequire} from 'node:module';
const {E2E_BASE:base,E2E_DOCTOR:doctor,E2E_DOCTOR_PASSWORD:password,E2E_CHROMIUM_PATH:exe}=process.env;
const expected=Number(process.env.E2E_EXPECTED_QUEUE_TOTAL),pid=process.env.E2E_PATIENT_ID||'PG-0001';
if(!base||!doctor||!password||!exe||!Number.isInteger(expected)||expected<51)throw Error('Explicit disposable, populated synthetic queue configuration required');
const browser=await chromium.launch({executablePath:exe,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote','--single-process']});
const page=await browser.newPage({viewport:{width:1440,height:900}});page.setDefaultTimeout(20000);
const check=(value,message)=>{if(!value)throw Error(message)};
try{
 await page.goto(base+'/doctor/login');await page.getByLabel('Username').fill(doctor);await page.getByLabel('Password',{exact:true}).fill(password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.getByRole('heading',{name:'Your patient cohort'}).waitFor();
 await page.getByRole('button',{name:'Care Action Centre',exact:true}).click();const queue=page.locator('section.portal-card').filter({has:page.getByRole('heading',{name:'Review queue',exact:true})});await queue.getByLabel('Queue item type').selectOption('checkin');
 await queue.getByText(`Showing 1–25 of ${expected} items`).waitFor();check(await queue.getByRole('button',{name:'Previous queue page'}).isDisabled(),'Previous unexpectedly enabled');
 await queue.getByRole('button',{name:'Next queue page'}).click();await queue.getByText(`Showing 26–50 of ${expected} items`).waitFor();await queue.getByRole('button',{name:'Next queue page'}).click();await queue.getByText(`Showing 51–${Math.min(75,expected)} of ${expected} items`).waitFor();
 await queue.getByLabel('Queue order').selectOption('oldest');await queue.getByText(`Showing 1–25 of ${expected} items`).waitFor();check(await queue.getByText(/Under Review/).count()>0&&await queue.getByText(/Follow-up Required/).count()>0,'Open review states missing');
 await queue.getByRole('button',{name:new RegExp(`Symptom check-in.*${pid}`)}).first().click();await page.getByText(`Selected patient: ${pid}`).waitFor();
 await page.addScriptTag({path:createRequire(import.meta.url).resolve('axe-core/axe.min.js')});
 for(const width of [390,768,1440]){await page.setViewportSize({width,height:900});await page.waitForTimeout(250);const result=await page.evaluate(async()=>({violations:(await window.axe.run(document)).violations.map(v=>`${v.id}: ${v.nodes.map(n=>`${n.target.join(' ')} ${n.failureSummary}`).join('; ')}`),overflow:document.documentElement.scrollWidth>innerWidth+1}));check(!result.violations.length&&!result.overflow,`Width ${width}: ${JSON.stringify(result)}`);}
 await queue.getByLabel('Queue item type').selectOption('upload');await queue.getByText('No open items or due follow-ups.').waitFor();check(await queue.getByRole('button',{name:'Next queue page'}).isDisabled(),'Empty queue has next page');
 console.log('PASS: scoped queue pagination, sort, open review states, selection, empty filter and three axe/overflow scans');
}finally{await browser.close()}
