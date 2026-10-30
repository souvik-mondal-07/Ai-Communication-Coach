import { useAptitudeStore } from "@/store/aptitudeStore";
import { useDbmsSqlStore } from "@/store/dbmsSqlStore";
import { useDsaStore } from "@/store/dsaStore";
import { useAuthStore } from "@/store/authStore";
import { useChatStore } from "@/store/chatStore";
import { useCommunicationStore } from "@/store/communicationStore";
import { useCtfStore } from "@/store/ctfStore";
import { useDailyPracticeStore } from "@/store/dailyPracticeStore";
import { useInterviewStore } from "@/store/interviewStore";
import { useNotificationStore } from "@/store/notificationStore";
import { usePracticeStore } from "@/store/practiceStore";
import { usePressureStore } from "@/store/pressureStore";
import { usePythonPracticeStore } from "@/store/pythonPracticeStore";
import { useProfileStore } from "@/store/profileStore";
import { useVoiceConversationStore } from "@/store/voiceConversationStore";

/**
 * Every store that holds data belonging to the signed-in user. Add new per-user stores here —
 * otherwise their contents would still be on screen after someone else signs in on the same tab.
 */
export function resetAllUserState(): void {
  useAptitudeStore.getState().reset();
  useDbmsSqlStore.getState().reset();
  usePythonPracticeStore.getState().reset();
  useDsaStore.getState().reset();
  useChatStore.getState().reset();
  useCommunicationStore.getState().reset();
  useCtfStore.getState().reset();
  useDailyPracticeStore.getState().reset();
  useInterviewStore.getState().reset();
  useNotificationStore.getState().reset();
  usePracticeStore.getState().reset();
  usePressureStore.getState().reset();
  useProfileStore.getState().reset();
  useVoiceConversationStore.getState().reset();
}

let installed = false;

/**
 * Clears all user-specific state whenever the signed-in user goes away or becomes a different
 * user — manual logout, an expired session (401), or signing in as someone else. The page isn't
 * reloaded on logout, so without this a second user could see the first user's conversations,
 * practice, notifications and profile. Idempotent; call once at startup.
 */
export function installSessionReset(): void {
  if (installed) return;
  installed = true;
  useAuthStore.subscribe((state, previous) => {
    const before = previous.user?.id ?? null;
    const after = state.user?.id ?? null;
    if (before !== null && before !== after) {
      resetAllUserState();
    }
  });
}
