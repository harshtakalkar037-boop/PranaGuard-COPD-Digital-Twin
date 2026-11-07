// Mutates ONLY a fresh, disposable local synthetic database. Never use production.
import {chromium} from 'playwright-core';
const {E2E_BASE:base,E2E_DOCTOR:doctor,E2E_OTHER_DOCTOR:other,E2E_DOCTOR_PASSWORD:password,E2E_CHROMIUM_PATH:executablePath,E2E_DISPOSABLE:disposable}=process.env;
if(disposable!=='1'||!base||!doctor||!other||!password||!executablePath||!/^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/.test(base))throw Error('Explicit loopback disposable research fixture required');
const browser=await chromium.launch({executablePath,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote','--single-process']});
const page=await browser.newPage({viewport:{width:1440,height:900}});const errors=[];
page.on('pageerror',e=>errors.push(e.message));
const check=(ok,message)=>{if(!ok)throw Error(message)};
async function login(user){await page.goto(`${base}/doctor/login`);await page.getByLabel('Username').fill(user);await page.getByLabel('Password',{exact:true}).fill(password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.waitForURL('**/doctor/dashboard');await page.getByRole('heading',{name:'Your patient cohort'}).waitFor();return await page.evaluate(()=>sessionStorage.getItem('pg-portal-token'));}
async function logout(){await page.getByRole('button',{name:'Sign out'}).click();await page.waitForURL(base+'/');}
try{
 const token=await login(doctor);const headers={Authorization:`Bearer ${token}`};
 const before=await (await page.request.get(`${base}/api/patients/PG-0001`,{headers})).json();
 await page.getByRole('button',{name:'Risk explainability'}).click();await page.getByRole('heading',{name:'Local model drivers'}).waitFor();await page.getByRole('button',{name:'24 hours'}).click();
 await page.getByRole('button',{name:'What-if studio'}).click();await page.getByRole('button',{name:'Run backend simulation'}).click();await page.getByText('Original twin preserved').waitFor();
 const saved=await (await page.request.get(`${base}/api/patients/PG-0001/scenarios`,{headers})).json();check(saved.scenarios.length===1,'Scenario was not persisted');
 const portalScenario=await page.request.post(`${base}/api/portal/patients/PG-0001/scenarios`,{headers,data:{}});check(portalScenario.status()===200,'Portal scenario failed');
 const explanation=await page.request.get(`${base}/api/portal/patients/PG-0001/explanation?horizon=24`,{headers});check(explanation.status()===200&&(await explanation.json()).patient_id==='PG-0001','Portal explanation failed');
 const intervention=await page.request.post(`${base}/api/patients/PG-0001/interventions`,{headers,data:{kind:'other',note:'Synthetic test observation'}});check(intervention.status()===200,'Intervention write failed');
 const after=await (await page.request.get(`${base}/api/patients/PG-0001`,{headers})).json();check(JSON.stringify(before)===JSON.stringify(after),'Research write modified original twin');
 await logout();check((await page.request.get(`${base}/api/patients/PG-0001`,{headers})).status()===401,'Logout did not revoke research access');
 const otherToken=await login(other);const otherHeaders={Authorization:`Bearer ${otherToken}`};
 for(const suffix of ['', '/history', '/versions', '/explanation', '/scenarios', '/interventions'])check((await page.request.get(`${base}/api/patients/PG-0001${suffix}`,{headers:otherHeaders})).status()===404,`Other doctor read ${suffix}`);
 for(const [path,data] of [['/api/patients/PG-0001/scenarios',{}],['/api/patients/PG-0001/interventions',{kind:'other',note:'Synthetic test'}],['/api/portal/patients/PG-0001/scenarios',{}]])check((await page.request.post(base+path,{headers:otherHeaders,data})).status()===404,`Other doctor wrote ${path}`);
 check((await page.request.get(`${base}/api/portal/patients/PG-0001/explanation`,{headers:otherHeaders})).status()===404,'Other doctor read portal explanation');
 await logout();check(!errors.length,`Page errors: ${errors.join('; ')}`);
 console.log('PASS: disposable research explanation, scenario persistence, portal scenario, intervention, unchanged twin, logout and two-doctor isolation.');
}finally{await browser.close()}
