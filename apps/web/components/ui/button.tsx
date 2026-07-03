import { cn } from "@/lib/utils";
import type { ButtonHTMLAttributes } from "react";

export type ButtonVariant =
  | "primary"
  | "outline"
  | "ghost"
  | "subtle"
  | "danger";
export type ButtonSize = "sm" | "md" | "lg";

const SIZES: Record<ButtonSize, string> = {
  sm: "h-9 px-3.5 text-sm rounded-md gap-1.5",
  md: "h-11 px-5 text-[0.95rem] rounded-md gap-2",
  lg: "h-[3.25rem] px-7 text-base rounded-lg gap-2",
};

const VARIANTS: Record<ButtonVariant, string> = {
  primary:
    "bg-accent text-accent-fg shadow-sm hover:bg-accent-hover active:bg-accent-press",
  outline:
    "border border-border-strong bg-surface text-ink hover:border-accent hover:text-accent",
  ghost: "text-ink hover:bg-surface-muted",
  subtle: "bg-accent-subtle text-accent hover:bg-[#e0efec]",
  danger: "bg-danger text-white hover:opacity-90",
};

export function buttonClasses(
  variant: ButtonVariant = "primary",
  size: ButtonSize = "md",
  className?: string,
) {
  return cn(
    "inline-flex select-none items-center justify-center font-medium transition-all duration-200 ease-soft",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
    "disabled:pointer-events-none disabled:opacity-50",
    SIZES[size],
    VARIANTS[variant],
    className,
  );
}

export function Button({
  variant = "primary",
  size = "md",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
}) {
  return <button className={buttonClasses(variant, size, className)} {...props} />;
}
