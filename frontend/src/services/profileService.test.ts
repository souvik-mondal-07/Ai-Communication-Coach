import { beforeEach, describe, expect, it, vi } from "vitest";

const post = vi.fn();
vi.mock("@/services/api", () => ({ api: { post: (...args: unknown[]) => post(...args), get: vi.fn(), patch: vi.fn() } }));

import { changePassword } from "@/services/profileService";
import { getStoredToken, setStoredToken } from "@/services/tokenStorage";

const payload = { current_password: "old-Password1", new_password: "new-Password2", confirm_new_password: "new-Password2" };

// The suite runs in a plain node environment, so provide a minimal in-memory localStorage.
const memory = new Map<string, string>();
vi.stubGlobal("localStorage", {
  getItem: (key: string) => memory.get(key) ?? null,
  setItem: (key: string, value: string) => void memory.set(key, value),
  removeItem: (key: string) => void memory.delete(key),
});

describe("changePassword", () => {
  beforeEach(() => {
    post.mockReset();
    memory.clear();
  });

  it("stores the fresh token so this device stays signed in", async () => {
    setStoredToken("old-token");
    post.mockResolvedValue({ data: { success: true, message: "ok", data: { access_token: "fresh-token", token_type: "bearer" } } });
    await expect(changePassword(payload)).resolves.toBe("fresh-token");
    expect(getStoredToken()).toBe("fresh-token");
  });

  it("keeps the existing token when the response carries none", async () => {
    setStoredToken("old-token");
    post.mockResolvedValue({ data: { success: true, message: "ok" } });
    await expect(changePassword(payload)).resolves.toBeNull();
    expect(getStoredToken()).toBe("old-token");
  });

  it("does not touch the stored token when the request fails", async () => {
    setStoredToken("old-token");
    post.mockRejectedValue(new Error("400"));
    await expect(changePassword(payload)).rejects.toThrow();
    expect(getStoredToken()).toBe("old-token");
  });
});
