import { Minus, Plus } from "lucide-react";
import { cn } from "@/lib/utils";

export function Stepper({
  value,
  onChange,
  min,
  max,
  step = 1,
  suffix = "",
}: {
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step?: number;
  suffix?: string;
}) {
  const clamp = (v: number) => Math.max(min, Math.min(max, v));
  return (
    <div className="inline-flex items-center rounded-lg border border-border bg-surface">
      <StepButton
        label="decrease"
        disabled={value <= min}
        onClick={() => onChange(clamp(value - step))}
      >
        <Minus className="h-4 w-4" />
      </StepButton>
      <span className="tnum w-[4.5rem] text-center text-sm font-semibold text-ink">
        {value}
        {suffix}
      </span>
      <StepButton
        label="increase"
        disabled={value >= max}
        onClick={() => onChange(clamp(value + step))}
      >
        <Plus className="h-4 w-4" />
      </StepButton>
    </div>
  );
}

function StepButton({
  children,
  onClick,
  disabled,
  label,
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  label: string;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "flex h-10 w-10 items-center justify-center text-muted transition-colors first:rounded-l-lg last:rounded-r-lg hover:bg-surface-muted hover:text-ink disabled:opacity-30 disabled:hover:bg-transparent",
      )}
    >
      {children}
    </button>
  );
}
