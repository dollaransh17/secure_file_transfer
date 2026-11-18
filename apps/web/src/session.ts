import {api, ApiError, setCsrf} from './api';

// Confirm server-side revocation before discarding this browser's private state.
// A new document also discards active query observers and in-flight UI work.
export async function endSession(redirect: () => void = () => window.location.replace('/')) {
  try {
    await api('/auth/logout', {method: 'POST'});
  } catch (error) {
    // An expired/revoked session is already signed out. Other failures must be
    // shown to the user instead of presenting a false successful logout.
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
  }
  setCsrf('');
  redirect();
}
