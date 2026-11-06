/** Invalidate only the session that actually produced a portal-authentication 401.
 * A demo write-token error or a late response from a previous session must not
 * sign out a newly authenticated user. */
export function handleExpiredSession(sentToken:string|null|undefined, detail:string):boolean {
 if(!sentToken || sessionStorage.getItem('pg-portal-token')!==sentToken ||
    !['Session expired or invalid','Authentication required'].includes(detail)) return false;
 sessionStorage.removeItem('pg-portal-token');
 sessionStorage.setItem('pg-session-expired','1');
 window.dispatchEvent(new Event('pg-session-expired'));
 return true;
}
