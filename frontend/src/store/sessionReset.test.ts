import { beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "@/store/authStore";
import { useChatStore } from "@/store/chatStore";
import { useNotificationStore } from "@/store/notificationStore";
import { useProfileStore } from "@/store/profileStore";
import { installSessionReset } from "@/store/sessionReset";
import type { UserProfile } from "@/types/profile";

const userA = { id: "a", name: "A", email: "a@example.com" };
const userB = { id: "b", name: "B", email: "b@example.com" };

function fillUserData() {
  useChatStore.setState({ messages: [{ id: "1", role: "user", content: "secret-of-A", timestamp: new Date().toISOString() }] as never });
  useProfileStore.setState({ profile: { name: "A" } as unknown as UserProfile });
}

describe("per-user state is wiped when the signed-in user changes", () => {
  beforeEach(() => {
    installSessionReset();
    useAuthStore.setState({ user: null, accessToken: null, isAuthenticated: false });
    useChatStore.getState().reset();
    useProfileStore.getState().reset();
    useNotificationStore.getState().reset();
  });

  it("clears everything on logout", () => {
    useAuthStore.setState({ user: userA, isAuthenticated: true });
    fillUserData();
    useAuthStore.setState({ user: null, accessToken: null, isAuthenticated: false });
    expect(useChatStore.getState().messages).toHaveLength(0);
    expect(useProfileStore.getState().profile).toBeNull();
  });

  it("clears everything when a 401 drops the session (same state transition as logout)", () => {
    useAuthStore.setState({ user: userA, isAuthenticated: true });
    fillUserData();
    useAuthStore.setState({ user: null, accessToken: null, isAuthenticated: false });
    expect(useChatStore.getState().messages).toHaveLength(0);
  });

  it("clears everything when a different user signs in without a logout in between", () => {
    useAuthStore.setState({ user: userA, isAuthenticated: true });
    fillUserData();
    useAuthStore.setState({ user: userB, isAuthenticated: true });
    expect(useChatStore.getState().messages).toHaveLength(0);
    expect(useProfileStore.getState().profile).toBeNull();
  });

  it("does not wipe state on the first sign-in, or when only the display name changes", () => {
    useAuthStore.setState({ user: userA, isAuthenticated: true });
    fillUserData();
    useAuthStore.getState().patchUser({ name: "Renamed" });
    expect(useChatStore.getState().messages).toHaveLength(1);
    expect(useProfileStore.getState().profile).not.toBeNull();
  });
});
