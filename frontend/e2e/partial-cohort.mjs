// Disposable synthetic database only; creates and revokes test sessions.
import {chromium} from 'playwright-core';
import {createRequire} from 'node:module';
const {E2E_BASE:base,E2E_DOCTOR:doctor,E2E_EMPTY_DOCTOR:empty,E2E_DOCTOR_PASSWORD:password,E2E_CHROMIUM_PATH:executablePath}=process.env;
if(!base||!doctor||!empty||!password||!executablePath)throw new Error('Explicit disposable partial-cohort configuration required');
const browser=await chromium.launch({executablePath,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote','--single-process']});
const page=await browser.newPage({viewport:{width:1440,height:900}});const failures=[];
page.on('pageerror',err=>failures.push(err.message));
const check=(ok,message)=>{if(!ok)throw Error(message)};
async function login(user){await page.goto(base+'/doctor/login');await page.getByLabel('Username').fill(user);await page.getByLabel('Password',{exact:true}).fill(password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.waitForURL('**/doctor/dashboard');}
try{
 await login(doctor);await page.getByRole('heading',{name:'Your patient cohort'}).waitFor();
 const token=await page.evaluate(()=>sessionStorage.getItem('pg-portal-token'));const headers={Authorization:`Bearer ${token}`};
 const overview=await (await page.request.get(base+'/api/overview',{headers})).json();
 check(overview.patients.length===1&&overview.patients[0].patient_id==='PG-0001','Overview population incorrect');
 check(overview.replay.demo===null,'Global demo metadata exposed');
 check((await page.request.get(base+'/api/patients/PG-0002',{headers})).status()===404,'Cross-doctor twin not denied');
 check((await page.request.get(base+'/api/validation',{headers})).status()===403,'Full validation not denied');
 check((await page.request.get(base+'/api/portal/validation',{headers})).status()===403,'Portal validation not denied');
 await page.getByRole('button',{name:'Patient twins',exact:true}).click();await page.getByRole('heading',{name:'Personal baseline vs current'}).waitFor();
 check(await page.getByLabel('Selected synthetic twin').inputValue()==='PG-0001','Default patient not assigned twin');
 check(await page.getByRole('button',{name:'1h'}).isDisabled(),'Global replay not disabled');
 await page.goto(base+'/doctor/dashboard?patient=PG-0002#patient');
 await page.getByRole('heading',{name:'Personal baseline vs current'}).waitFor();
 check(await page.getByLabel('Selected synthetic twin').inputValue()==='PG-0001','Unassigned URL patient was not cleared');
 await page.reload();await page.getByRole('heading',{name:'Personal baseline vs current'}).waitFor();check(await page.getByLabel('Selected synthetic twin').inputValue()==='PG-0001','Selection incorrect after refresh');
 await page.addScriptTag({path:createRequire(import.meta.url).resolve('axe-core/axe.min.js')});
 for(const width of [390,768,1440]){await page.setViewportSize({width,height:900});await page.waitForTimeout(250);const result=await page.evaluate(async()=>({violations:(await window.axe.run(document)).violations.map(v=>v.id),overflow:document.documentElement.scrollWidth>innerWidth+1}));check(!result.violations.length&&!result.overflow,`Width ${width}: ${JSON.stringify(result)}`);}
 await page.setViewportSize({width:1440,height:900});await page.getByRole('button',{name:'Model validation'}).click();await page.getByText(/Permission denied \(HTTP 403\)/).waitFor();
 await page.getByRole('button',{name:'Sign out'}).click();await page.waitForURL(base+'/');await login(empty);await page.getByRole('heading',{name:'Your patient cohort'}).waitFor();await page.getByRole('button',{name:'Patient twins'}).click();await page.getByText(/No historical synthetic twins are assigned/).waitFor();
 check((await page.getByLabel('Selected synthetic twin').inputValue())==='','Empty doctor selected an unassigned twin');
 check(failures.length===0,`Browser errors: ${failures.join('; ')}`);console.log('PASS: partial-cohort and empty-doctor browser journeys; access isolation, refresh, validation denial, disabled replay, and three axe/overflow scans.');
}finally{await browser.close()}
