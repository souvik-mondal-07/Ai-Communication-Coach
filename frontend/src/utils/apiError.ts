import axios from "axios";

/**
 * Turn an Axios error into a short, user-facing message. Never surfaces raw
 * backend tracebacks — falls back to a generic message when the backend
 * didn't send a structured `{ message, error_code }` error body.
 */
export function getApiErrorMessage(
  error: unknown,
  fallback = "Something went wrong. Please try again."
): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) {
      return "Unable to connect to the server. Please try again.";
    }
    const message = (error.response.data as { message?: unknown } | undefined)?.message;
    if (typeof message === "string" && message.length > 0) {
      return message;
    }
  }
  return fallback;
}
