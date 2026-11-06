// Navigation and session-revocation checks for an explicitly provisioned disposable synthetic cohort.
// The doctor must be assigned to every synthetic record, including PG-0001 and PG-0002.
// E2E_BASE, E2E_DOCTOR, E2E_DOCTOR_PASSWORD and E2E_CHROMIUM_PATH must be supplied.
import {chromium} from 'playwright-core';
const {E2E_BASE:base,E2E_DOCTOR:doctor,E2E_DOCTOR_PASSWORD:password,E2E_CHROMIUM_PATH:exe}=process.env;
if(!base||!doctor||!password||!exe)throw new Error('Explicit disposable demo configuration required');
const browser=await chromium.launch({executablePath:exe,args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote','--single-process']});
const page=await browser.newPage({viewport:{width:1440,height:900}});page.setDefaultTimeout(15000);
const errors=[];page.on('pageerror',e=>errors.push(e.message));
try{
 await page.goto(`${base}/doctor/login`);await page.getByLabel('Username').fill(doctor);await page.getByLabel('Password',{exact:true}).fill(password);await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await page.getByRole('heading',{name:'Your patient cohort'}).waitFor();
 const overviewToken=await page.evaluate(()=>sessionStorage.getItem('pg-portal-token'));
 const overview=await page.request.get(`${base}/api/overview`,{headers:{Authorization:`Bearer ${overviewToken}`}});if(!overview.ok())throw Error('Cohort API unavailable');
 const cohort=(await overview.json()).patients;const top24=cohort.filter(p=>p.prediction_supported&&p.risks['24']!==undefined).sort((a,b)=>b.risks['24']-a.risks['24']||a.patient_id.localeCompare(b.patient_id))[0];
 await page.getByLabel('Sort historical cohort').selectOption('risk24');
 if(top24){const first=page.locator('.cohort-table tbody tr').first();if(!(await first.innerText()).includes(top24.patient_id))throw Error('24h cohort sorting differs from API values')}
 await page.setViewportSize({width:390,height:844});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error('Mobile cohort overflow');await page.setViewportSize({width:1440,height:900});
 if(process.env.E2E_SCREENSHOT)await page.screenshot({path:process.env.E2E_SCREENSHOT,fullPage:true});
 await page.getByLabel('Search patients').fill('PG-0001');await page.getByRole('button',{name:'Open PG-0001'}).click();await page.getByRole('heading',{name:'Personal baseline vs current'}).waitFor();
 await page.getByRole('button',{name:'Care Action Centre'}).click();await page.getByRole('heading',{name:'Care Action Centre',level:1}).waitFor();await page.getByRole('heading',{name:'Patient digital twin'}).waitFor();
 await page.getByRole('heading',{name:'Review queue'}).waitFor();
 if(process.env.E2E_QUEUE_PATIENT){const queue=page.locator('section.portal-card').filter({has:page.getByRole('heading',{name:'Review queue'})});await queue.getByRole('button',{name:new RegExp(`Symptom check-in.*${process.env.E2E_QUEUE_PATIENT}`)}).click();await page.getByText(`Selected patient: ${process.env.E2E_QUEUE_PATIENT}`).waitFor()}
 await page.getByLabel('Search assigned patients').fill('PG-0002');await page.getByRole('button',{name:/Synthetic twin 002/}).click();await page.getByText('Selected patient: PG-0002').waitFor();
 if((await page.locator('aside:visible').count())!==1)throw Error('Duplicate visible sidebars');
 await page.getByRole('button',{name:'Patient twins'}).click();await page.getByRole('heading',{name:'Personal baseline vs current'}).waitFor();
 if(await page.getByLabel('Selected synthetic twin').inputValue()!=='PG-0002')throw Error('Selected patient not preserved');
 await page.goto(`${base}/doctor/dashboard?patient=PG-0001&view=Sputum%20Monitoring`);await page.getByRole('heading',{name:'Sputum Monitoring',level:1}).waitFor();await page.getByRole('heading',{name:'Sputum monitoring · patient-reported'}).waitFor();
 await page.setViewportSize({width:390,height:844});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error('Mobile overflow');
 // Revoke only this disposable browser session, then verify a subsequent portal
 // request returns the user to sign-in with an explanatory message.
 const token=await page.evaluate(()=>sessionStorage.getItem('pg-portal-token'));
 const revoked=await page.request.post(`${base}/api/portal/logout`,{headers:{Authorization:`Bearer ${token}`}});
 if(!revoked.ok())throw Error('Could not revoke disposable session');
 await page.getByRole('button',{name:'Open navigation'}).click();await page.getByRole('button',{name:'Care Action Centre'}).click();
 await page.waitForURL('**/doctor/login');await page.getByText('Your session expired. Please sign in again.').waitFor();
 if(errors.length)throw Error(errors.join('; '));console.log('PASS: cohort horizon sorting, unified sidebar, patient search and context, care deep link, mobile overflow, session revocation');
}finally{await browser.close()}
