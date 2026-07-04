"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";
import { useHydrated } from "@/lib/use-hydrated";

export function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  const hydrated = useHydrated();
  const reduced = useReducedMotion();

  // Server HTML, no-JS, and reduced-motion clients all get a plain, fully
  // visible div — a hidden initial state must never reach server markup,
  // because nothing would be around to clear it. The motion element mounts
  // only after hydration on motion-friendly clients (below the fold, so the
  // element swap is never seen).
  if (!hydrated || reduced) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
