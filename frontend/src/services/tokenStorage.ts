/**
 * Centralized access-token storage.
 *
 * Everything that needs to read/write the stored token goes through this
 * module instead of touching `localStorage` directly, so the storage
 * strategy (e.g. upgrading to httpOnly cookies later) can change in one
 * place. Never store the password or password hash here — only the token.
 */

const TOKEN_KEY = "auth_token";

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    // Storage can throw in some environments (e.g. private browsing).
    return null;
  }
}

export function setStoredToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // Ignore storage errors — the session just won't persist across reloads.
  }
}

export function clearStoredToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Ignore storage errors.
  }
}
