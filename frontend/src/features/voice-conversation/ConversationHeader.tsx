import { VOICE_DIFFICULTY_LABELS, type VoiceConversationSession } from "@/types/voiceConversation";

export function ConversationHeader({ session }: { session: VoiceConversationSession }) {
  const answered = session.user_turn_count;
  return (
    <header className="space-y-1">
      <h1 className="font-display text-xl font-semibold text-text-primary sm:text-2xl">{session.mode_label}</h1>
      <p className="text-sm text-text-secondary">
        {VOICE_DIFFICULTY_LABELS[session.difficulty]}
        {session.topic ? ` · ${session.topic}` : ""}
        {session.linked_session?.label ? ` · ${session.linked_session.label}` : ""}
        {" · "}
        {answered} {answered === 1 ? "answer" : "answers"} given
      </p>
    </header>
  );
}
