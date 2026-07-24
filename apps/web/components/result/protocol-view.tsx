"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, FlaskConical } from "lucide-react";
import { buttonClasses } from "@/components/ui/button";
import { Section } from "@/components/layout/section";
import { ProtocolResult } from "./protocol-result";
import { LoadingProtocol } from "./loading-protocol";
import { ProtocolErrorState } from "./states";
import { useGenerateProtocol } from "@/lib/queries";
import {
  echoToRequest,
  loadProtocol,
  PROTOCOL_QUERY_KEY,
  saveProtocol,
  type StashedProtocol,
} from "@/lib/protocol-store";
import type { ApiError } from "@/lib/api";
import type { GenerateResponse } from "@/types/protocol";

export function ProtocolView() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const gen = useGenerateProtocol();
  const [stash, setStash] = useState<StashedProtocol | null>(null);
  const [hydrated, setHydrated] = useState(false);

  // sessionStorage is client-only — read after mount and gate render on
  // `hydrated` so the server HTML matches the first client paint.
  useEffect(() => {
    const fromStore = loadProtocol();
    /* eslint-disable react-hooks/set-state-in-effect -- one-time hydration read from sessionStorage/cache; must run after mount to avoid an SSR/client mismatch */
    if (fromStore) {
      setStash(fromStore);
    } else {
      const fromCache =
        queryClient.getQueryData<GenerateResponse>(PROTOCOL_QUERY_KEY);
      if (fromCache) {
        setStash({
          request: echoToRequest(fromCache.request),
          response: fromCache,
          savedAt: Date.now(),
        });
      }
    }
    setHydrated(true);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [queryClient]);

  function regenerate() {
    if (!stash) return;
    gen.mutate(stash.request, {
      onSuccess: (response) => {
        saveProtocol(stash.request, response);
        queryClient.setQueryData(PROTOCOL_QUERY_KEY, response);
        setStash({ request: stash.request, response, savedAt: Date.now() });
      },
    });
  }

  function editInputs() {
    router.push("/build");
  }

  if (!hydrated) return null;

  if (gen.isPending) {
    return (
      <Section className="py-10 sm:py-14">
        <div className="mx-auto w-full max-w-4xl">
          <BackRow onClick={editInputs} />
          <div className="mt-5">
            <LoadingProtocol />
          </div>
        </div>
      </Section>
    );
  }

  if (gen.isError) {
    return (
      <Section className="py-10 sm:py-14">
        <div className="mx-auto w-full max-w-4xl">
          <BackRow onClick={editInputs} />
          <div className="mt-5">
            <ProtocolErrorState
              message={(gen.error as ApiError)?.message ?? "Something went wrong."}
              onRetry={regenerate}
              retrying={gen.isPending}
            />
          </div>
        </div>
      </Section>
    );
  }

  if (!stash) {
    return (
      <Section className="py-16 sm:py-24">
        <div className="mx-auto flex min-h-[18rem] max-w-lg flex-col items-center justify-center rounded-2xl border border-dashed border-border-strong bg-surface/60 p-10 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent-subtle">
            <FlaskConical className="h-6 w-6 text-accent" />
          </div>
          <h1 className="mt-4 font-heading text-2xl font-semibold text-ink">
            No protocol to show yet
          </h1>
          <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted">
            Build a protocol and it&apos;ll open here — every exercise ranked and
            cited to the studies behind it.
          </p>
          <Link href="/build" className={buttonClasses("primary", "md", "mt-6")}>
            Build a protocol <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </Section>
    );
  }

  return (
    <Section className="py-10 sm:py-14">
      <div className="mx-auto w-full max-w-4xl">
        <BackRow onClick={editInputs} />
        <div className="mt-5">
          <ProtocolResult
            data={stash.response}
            onRegenerate={regenerate}
            onTweak={editInputs}
            regenerating={gen.isPending}
          />
        </div>
      </div>
    </Section>
  );
}

function BackRow({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1.5 text-sm font-medium text-muted transition-colors hover:text-ink"
    >
      <ArrowLeft className="h-4 w-4" /> Back to builder
    </button>
  );
}
