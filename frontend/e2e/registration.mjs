// Mutates an explicitly provisioned disposable synthetic database only.
// Requires E2E_BASE, E2E_DOCTOR, E2E_DOCTOR_PASSWORD and E2E_CHROMIUM_PATH.
import {chromium} from 'playwright-core';
const {E2E_BASE:base,E2E_DOCTOR:doctor,E2E_DOCTOR_PASSWORD:password,E2E_CHROMIUM_PATH:exe}=process.env;
if(!base||!doctor||!password||!exe)throw new Error('Explicit disposable demo configuration required');
const browser=await chromium.launch({executablePath:exe,args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote','--single-process']});
const page=await browser.newPage({viewport:{width:1440,height:900}});page.setDefaultTimeout(15000);
try{
 await page.goto(`${base}/doctor/login`);await page.getByLabel('Username').fill(doctor);await page.getByLabel('Password',{exact:true}).fill(password);await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await page.getByRole('heading',{name:'Your patient cohort'}).waitFor();await page.getByRole('button',{name:'Patients',exact:true}).click();await page.getByRole('button',{name:'Add fictional patient'}).click();
 await page.getByLabel('Fictional alias',{exact:true}).fill('Integration Example');await page.getByLabel('Demo age (18–100)').fill('58');await page.getByRole('checkbox',{name:/I confirm that all identity/}).check();
 const response=page.waitForResponse(r=>r.url().endsWith('/api/enhanced/registry/patients')&&r.request().method()==='POST');await page.getByRole('button',{name:'Save fictional patient'}).click();
 const saved=await response;if(!saved.ok())throw Error(`Registration HTTP ${saved.status()}`);const {patient_id:pid}=await saved.json();
 await page.getByText('No 24/48/72h prediction is available for this registration.').waitFor();
 const token=await page.evaluate(()=>sessionStorage.getItem('pg-portal-token'));const headers={Authorization:`Bearer ${token}`};
 const overview=await page.request.get(`${base}/api/overview`,{headers});if(!overview.ok())throw Error('Registration locked out registering doctor');if((await overview.json()).patients.length!==120)throw Error('Original cohort changed');
 await page.getByRole('button',{name:'Care Action Centre'}).click();await page.getByLabel('Search assigned patients').fill(pid);await page.getByRole('button',{name:new RegExp(pid)}).click();await page.getByText(`Selected patient: ${pid}`).waitFor();await page.getByRole('heading',{name:'Fictional patient profile'}).waitFor();await page.getByText('No historical twin prediction is available for this record.').waitFor();await page.getByRole('heading',{name:'Environmental context · Pune'}).waitFor();
 await page.getByRole('button',{name:'Patient twins'}).click();await page.getByText(new RegExp(`Selected record ${pid} is outside the original historical model cohort`)).waitFor();
 if(await page.getByLabel('Selected synthetic twin').inputValue()!==pid)throw Error('Registration patient context lost');
 await page.getByRole('button',{name:'Open its fictional registry profile'}).click();await page.getByText('No 24/48/72h prediction is available for this registration.').waitFor();
 console.log('PASS: synthetic registration, atomic assignment, 120-patient preservation, care context and unsupported-prediction boundary');
}finally{await browser.close()}
