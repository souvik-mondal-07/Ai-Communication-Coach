/**
 * Placeholder chat types. Populated fully when the AI Mentor chat feature is implemented.
 */
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
}
