import { type RefObject, useEffect } from "react";

/**
 * Closes a popover when the user presses Escape or clicks/taps outside `ref`.
 * Replaces the full-screen invisible overlay the menus used before, which
 * blocked scrolling and could not be reached by keyboard.
 */
export function useDismiss(ref: RefObject<HTMLElement | null>, isOpen: boolean, onClose: () => void): void {
  useEffect(() => {
    if (!isOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    function onPointer(e: PointerEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [ref, isOpen, onClose]);
}
