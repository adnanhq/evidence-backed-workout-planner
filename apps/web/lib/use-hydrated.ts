"use client";

import { useSyncExternalStore } from "react";

const noopSubscribe = () => () => {};

/**
 * False during SSR and hydration, true immediately after. Lets motion
 * components ship fully visible server HTML (no stranded `opacity:0` for
 * no-JS/reduced-motion visitors) and start their entrance animations only
 * once the client can actually run them — usually via a keyed remount.
 */
export function useHydrated() {
  return useSyncExternalStore(
    noopSubscribe,
    () => true,
    () => false,
  );
}
