/**
 * Basic email format check. Placeholder for Step 1 - full validation
 * (password strength, etc.) arrives with the authentication feature.
 */
export function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}
