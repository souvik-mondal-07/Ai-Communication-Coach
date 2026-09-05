/**
 * Authenticated user, as returned by the backend's /auth endpoints.
 * Never includes a password or password hash — the backend never sends those.
 */
export interface User {
  id: string;
  name: string;
  email: string;
}
