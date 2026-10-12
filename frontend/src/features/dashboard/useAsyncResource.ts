import { useCallback, useEffect, useState } from "react";
import { getApiErrorMessage } from "@/utils/apiError";

export type Resource<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: T };

/** Loads once on mount, exposes a reload, and ignores results that arrive after unmount. */
export function useAsyncResource<T>(fetcher: () => Promise<T>, errorMessage: string): [Resource<T>, () => void] {
  const [state, setState] = useState<Resource<T>>({ status: "loading" });
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    fetcher()
      .then((data) => active && setState({ status: "ready", data }))
      .catch((err) => active && setState({ status: "error", message: getApiErrorMessage(err, errorMessage) }));
    return () => {
      active = false;
    };
    // The fetcher is a stable module function; re-running is driven by `nonce` only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return [state, reload];
}
