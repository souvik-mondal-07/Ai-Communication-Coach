import { create } from "zustand";
import { launchTask } from "@/features/dailyPractice/dailyPracticeLauncher";
import * as dailyPracticeService from "@/services/dailyPracticeService";
import { useNotificationStore } from "@/store/notificationStore";
import type { DailyPracticeState, DailyTask } from "@/types/dailyPractice";
import { getApiErrorMessage } from "@/utils/apiError";

interface DailyPracticeStoreState {
  data: DailyPracticeState | null;
  isLoading: boolean;
  isActing: boolean;
  error: string | null;
  actionError: string | null;

  load: (opts?: { silent?: boolean }) => Promise<void>;
  /** Marks the plan started and opens the first unfinished task. Resolves to the route to open. */
  start: () => Promise<string | null>;
  openTask: (task: DailyTask) => Promise<string>;
  regenerate: () => Promise<void>;
  complete: () => Promise<void>;
  reset: () => void;
}

const initial = { data: null, isLoading: false, isActing: false, error: null, actionError: null };

function apply(state: DailyPracticeState) {
  useNotificationStore.getState().setUnreadCount(state.unread_notifications);
  return { data: state };
}

export const useDailyPracticeStore = create<DailyPracticeStoreState>((set, get) => ({
  ...initial,

  load: async ({ silent = false } = {}) => {
    if (!silent) set({ isLoading: true, error: null });
    try {
      set({ ...apply(await dailyPracticeService.getDailyPractice()), isLoading: false, error: null });
    } catch (err) {
      set({ isLoading: false, error: getApiErrorMessage(err, "Unable to load today's practice.") });
    }
  },

  start: async () => {
    set({ isActing: true, actionError: null });
    try {
      const state = await dailyPracticeService.startDailyPractice();
      set({ ...apply(state), isActing: false });
      const next = state.plan?.tasks.find((t) => t.status !== "completed");
      return next ? await get().openTask(next) : null;
    } catch (err) {
      set({ isActing: false, actionError: getApiErrorMessage(err, "Unable to start today's practice.") });
      return null;
    }
  },

  openTask: async (task) => {
    set({ isActing: true, actionError: null });
    try {
      const route = await launchTask(task);
      set({ isActing: false });
      return route;
    } catch (err) {
      set({ isActing: false, actionError: getApiErrorMessage(err, "Unable to start this task. Please try again.") });
      throw err;
    }
  },

  regenerate: async () => {
    set({ isActing: true, actionError: null });
    try {
      set({ ...apply(await dailyPracticeService.regenerateDailyPractice()), isActing: false });
    } catch (err) {
      set({ isActing: false, actionError: getApiErrorMessage(err, "Unable to create a new practice right now.") });
    }
  },

  complete: async () => {
    set({ isActing: true, actionError: null });
    try {
      set({ ...apply(await dailyPracticeService.completeDailyPractice()), isActing: false });
    } catch (err) {
      set({ isActing: false, actionError: getApiErrorMessage(err, "Unable to finish today's practice.") });
    }
  },

  reset: () => set({ ...initial }),
}));
