"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { buttonClasses } from "@/components/ui/button";
import { Wordmark } from "./logo";

const NAV = [
  { href: "/build", label: "Build" },
  { href: "/exercises", label: "Exercises" },
  { href: "/science", label: "The science" },
];

export function SiteHeader() {
  const [scrolled, setScrolled] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // The landing page opens with a dark hero; while unscrolled the transparent
  // header sits over it and needs light text/logo to stay legible.
  const onDark = pathname === "/" && !scrolled;

  return (
    <header
      className={cn(
        "sticky top-0 z-50 transition-all duration-300 ease-soft",
        scrolled
          ? "border-b border-border bg-bg/80 backdrop-blur-md"
          : "border-b border-transparent bg-transparent",
      )}
    >
      <div className="mx-auto flex h-16 w-full max-w-[var(--container-page)] items-center justify-between px-5 sm:px-8">
        <Link href="/" aria-label="Protocol home" className="shrink-0">
          <Wordmark tone={onDark ? "inverted" : "default"} />
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {NAV.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "px-3.5 py-2 text-sm font-medium decoration-1 underline-offset-[10px] transition-colors",
                  onDark
                    ? "text-on-dark/75 decoration-on-dark-border-strong hover:text-on-dark hover:underline"
                    : "text-muted decoration-border-strong hover:text-ink hover:underline",
                  active &&
                    (onDark
                      ? "text-on-dark underline decoration-accent-on-dark"
                      : "text-ink underline decoration-accent"),
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
          <Link href="/build" className={buttonClasses("primary", "sm")}>
            Build a protocol
          </Link>
        </div>
      </div>
    </header>
  );
}
