import { AlertTriangle, FlaskConical } from "lucide-react";
import { buttonClasses } from "@/components/ui/button";

export function ProtocolEmptyState() {
  return (
    <div className="flex min-h-[20rem] flex-col items-center justify-center rounded-xl border border-dashed border-border-strong bg-surface/60 p-10 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent-subtle">
        <FlaskConical className="h-6 w-6 text-accent" />
      </div>
      <h3 className="mt-4 font-display text-xl font-medium text-ink">
        Your evidence-based protocol will appear here
      </h3>
      <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted">
        Choose your goal and target muscles, set your week, then generate. Every
        suggestion will arrive with the studies behind it.
      </p>
    </div>
  );
}

export function ProtocolErrorState({
  message,
  onRetry,
  retrying,
}: {
  message: string;
  onRetry: () => void;
  retrying?: boolean;
}) {
  return (
    <div className="flex min-h-[20rem] flex-col items-center justify-center rounded-xl border border-[#f0cfca] bg-[#fdf4f2] p-10 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#f7dad4]">
        <AlertTriangle className="h-6 w-6 text-danger" />
      </div>
      <h3 className="mt-4 font-display text-xl font-medium text-ink">
        We couldn&apos;t build your protocol
      </h3>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-muted">{message}</p>
      <button
        onClick={onRetry}
        disabled={retrying}
        className={buttonClasses("primary", "md", "mt-5")}
      >
        {retrying ? "Trying again…" : "Try again"}
      </button>
    </div>
  );
}
