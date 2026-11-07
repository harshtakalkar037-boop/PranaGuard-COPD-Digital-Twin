const preview = process.env.VERCEL_ENV === 'preview';
if (!preview) {
  console.log('Preview API smoke checks skipped outside Vercel Preview.');
  process.exit(0);
}

const base = (process.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');
if (!base) throw new Error('VITE_API_BASE_URL is required for the preview API smoke test.');
const origin = process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'https://prana-guard-copd-digital-twin.vercel.app';

async function request(path, options = {}, expected = 200) {
  const response = await fetch(`${base}/api${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  });
  const text = await response.text();
  if (response.status !== expected) {
    throw new Error(`${options.method || 'GET'} ${path}: expected HTTP ${expected}, received ${response.status}: ${text.slice(0, 400)}`);
  }
  if (!text) return null;
  try { return JSON.parse(text); } catch { return text; }
}

async function login(username, password) {
  const result = await request('/workspace/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  if (!result?.token) throw new Error(`Workspace login did not return a session for ${username}.`);
  return result.token;
}
const auth = token => ({ Authorization: `Bearer ${token}` });

async function run() {
  let health;
  for (let attempt = 0; attempt < 8; attempt++) {
    try { health = await request('/health'); break; }
    catch (error) {
      if (attempt === 7) throw error;
      await new Promise(resolve => setTimeout(resolve, 5000));
    }
  }
  if (health?.status !== 'ok' || health?.synthetic !== true) throw new Error('Preview API health response is not the expected synthetic service.');

  const preflight = await fetch(`${base}/api/workspace/me`, {
    method: 'OPTIONS',
    headers: {
      Origin: origin,
      'Access-Control-Request-Method': 'GET',
      'Access-Control-Request-Headers': 'authorization,content-type',
    },
  });
  const allowed = (preflight.headers.get('access-control-allow-headers') || '').toLowerCase();
  if (preflight.status !== 200 || !allowed.includes('authorization')) {
    throw new Error(`CORS preflight failed: HTTP ${preflight.status}; allowed headers: ${allowed}`);
  }

  await request('/overview', {}, 401);

  const doctor = await login('dr-atlas', 'prana-atlas-demo');
  const me = await request('/workspace/me', { headers: auth(doctor) });
  if (me?.user?.role !== 'doctor' || me.user.assigned_patients !== 120) throw new Error('Doctor session/assignment scope is incorrect.');
  const overview = await request('/overview', { headers: auth(doctor) });
  if (overview?.summary?.total !== 120) throw new Error('Doctor research overview is not scoped to the 120 historical twins.');
  await request('/workspace/patients?page=1&page_size=5', { headers: auth(doctor) });
  await request('/enhanced/notifications/counts', { headers: auth(doctor) });
  await request('/workspace/logout', { method: 'POST', headers: auth(doctor), body: '{}' });

  const emptyDoctor = await login('dr-nova', 'prana-nova-demo');
  const emptyOverview = await request('/overview', { headers: auth(emptyDoctor) });
  if (emptyOverview?.summary?.total !== 0) throw new Error('Empty doctor account can see records outside its assignments.');
  await request('/enhanced/notifications/counts', { headers: auth(emptyDoctor) }, 403);
  await request('/workspace/logout', { method: 'POST', headers: auth(emptyDoctor), body: '{}' });

  const patient = await login('pat-pg0071', 'prana-patient-demo');
  const patientOverview = await request('/overview', { headers: auth(patient) });
  if (patientOverview?.summary?.total !== 1) throw new Error('Patient account is not limited to its own synthetic twin.');
  await request('/patients/PG-0072', { headers: auth(patient) }, 404);
  await request('/patients/PG-0071/interventions', {
    method: 'POST',
    headers: auth(patient),
    body: JSON.stringify({ kind: 'clinical_review', note: 'Must be blocked in patient role.' }),
  }, 403);
  await request('/workspace/logout', { method: 'POST', headers: auth(patient), body: '{}' });

  console.log('Preview API smoke checks passed: health, CORS, unauthenticated denial, doctor scope, empty-doctor isolation, patient isolation, and patient write denial.');
}

await run();
