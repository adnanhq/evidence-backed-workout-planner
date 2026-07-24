"use client";

import { useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ChevronDown, Library } from "lucide-react";
import { cn } from "@/lib/utils";
import { TIER_ORDER, EVIDENCE_TIERS, tierRank } from "@/lib/evidence";
import type { EvidenceItem, EvidenceTier } from "@/types/protocol";
import { EvidenceCard } from "@/components/evidence/evidence-card";

/**
 * The full bibliography, collapsed by default. The always-visible part is a
 * one-glance summary: study count + tier distribution. Expanding reveals
 * every study, strongest evidence first.
 */
export function EvidenceAppendix({ items }: { items: EvidenceItem[] }) {
  const [open, setOpen] = useState(false);
  const reduced = useReducedMotion();

  const sorted = useMemo(
    () => [...items].sort((a, b) => tierRank(a.tier) - tierRank(b.tier)),
    [items],
  );
  const segments = useMemo(() => {
    const counts = new Map<EvidenceTier, number>();
    for (const item of items) {
      const tier = (item.tier in EVIDENCE_TIERS ? item.tier : "other") as EvidenceTier;
      counts.set(tier, (counts.get(tier) ?? 0) + 1);
    }
    return TIER_ORDER.filter((t) => counts.has(t)).map((t) => ({
      ...EVIDENCE_TIERS[t],
      count: counts.get(t)!,
    }));
  }, [items]);

  if (!items.length) return null;

  return (
    <section className="overflow-hidden rounded-2xl border border-border bg-surface shadow-card">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full flex-wrap items-center gap-x-4 gap-y-2 px-5 py-4 text-left transition-colors hover:bg-surface-muted/40 sm:px-6"
      >
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent-subtle">
          <Library className="h-4 w-4 text-accent" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block font-heading text-base font-semibold text-ink">
            The science behind this protocol
          </span>
          <span className="mt-0.5 block text-[0.78rem] text-subtle">
            <span className="tnum">{items.length}</span> peer-reviewed{" "}
            {items.length === 1 ? "study" : "studies"} · strongest evidence first
          </span>
        </span>
        <span className="inline-flex shrink-0 items-center gap-1 text-[0.8rem] font-medium text-accent">
          {open ? "Hide studies" : "Browse studies"}
          <ChevronDown
            className={cn("h-4 w-4 transition-transform duration-200", open && "rotate-180")}
          />
        </span>
      </button>

      <div className="px-5 pb-4 sm:px-6">
        <div className="flex h-1.5 gap-px overflow-hidden rounded-full bg-surface-muted">
          {segments.map((seg) => (
            <div
              key={seg.label}
              title={`${seg.label} × ${seg.count}`}
              className={seg.dot}
              style={{ width: `${(seg.count / items.length) * 100}%` }}
            />
          ))}
        </div>
        <div className="mt-2.5 flex flex-wrap gap-x-4 gap-y-1">
          {segments.map((seg) => (
            <span
              key={seg.label}
              className="inline-flex items-center gap-1.5 text-[0.72rem] text-subtle"
            >
              <span className={cn("h-1.5 w-1.5 rounded-full", seg.dot)} aria-hidden />
              {seg.label} <span className="tnum text-muted">×{seg.count}</span>
            </span>
          ))}
        </div>
      </div>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={
              reduced ? { duration: 0 } : { duration: 0.3, ease: [0.22, 1, 0.36, 1] }
            }
            className="overflow-hidden"
          >
            <div className="grid gap-2.5 border-t border-border bg-surface-muted/40 p-5 sm:grid-cols-2 sm:p-6">
              {sorted.map((item, i) => (
                <EvidenceCard key={(item.pmid ?? "a") + i} item={item} />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
