// Locks one explicitly configured disposable synthetic account. Never run on production.
import {chromium} from 'playwright-core';
const {E2E_BASE:base,E2E_DOCTOR:doctor,E2E_DOCTOR_PASSWORD:password,E2E_CHROMIUM_PATH:exe}=process.env;
if(!base||!doctor||!password||!exe)throw new Error('Explicit disposable synthetic demo and Chromium configuration required');
const browser=await chromium.launch({executablePath:exe,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--no-zygote','--single-process']});
const page=await browser.newPage();page.setDefaultTimeout(15000);
try{
 await page.goto(base+'/doctor/login');await page.getByLabel('Username').fill(doctor);await page.getByLabel('Password',{exact:true}).fill('intentionally-invalid-test-password');
 for(let i=0;i<5;i++){
  const response=page.waitForResponse(r=>r.url().endsWith('/api/portal/login')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();if((await response).status()!==401)throw Error('Expected generic invalid-credential response');
  await page.getByText(/Invalid credentials/).waitFor();
 }
 await page.getByLabel('Password',{exact:true}).fill(password);
 const response=page.waitForResponse(r=>r.url().endsWith('/api/portal/login')&&r.request().method()==='POST');await page.getByRole('button',{name:'Sign in',exact:true}).click();
 const blocked=await response;if(blocked.status()!==429||!Number(blocked.headers()['retry-after']))throw Error('Expected bounded retry response');
 await page.getByText(/Too many sign-in attempts/).waitFor();
 if(await page.evaluate(()=>sessionStorage.getItem('pg-portal-token')))throw Error('Blocked login created a session');
 console.log('PASS: five invalid logins, blocked correct login, retry header and accessible throttle error');
}finally{await browser.close()}
