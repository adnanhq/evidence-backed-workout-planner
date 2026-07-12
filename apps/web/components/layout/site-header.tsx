"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
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
  const [menuOpen, setMenuOpen] = useState(false);
  const pathname = usePathname();
  const [prevPathname, setPrevPathname] = useState(pathname);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Close the mobile menu when the route actually changes, so it never lingers
  // over the next page. Adjusted during render (not an effect) per React's
  // guidance for state derived from a prop change:
  // https://react.dev/learn/you-might-not-need-an-effect
  if (pathname !== prevPathname) {
    setPrevPathname(pathname);
    if (menuOpen) setMenuOpen(false);
  }

  // Lock background scroll while the mobile menu overlay is open.
  useEffect(() => {
    if (!menuOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [menuOpen]);

  // The landing page opens with a dark hero; while unscrolled the transparent
  // header sits over it and needs light text/logo to stay legible. The open
  // mobile menu always paints its own solid bar, so drop onDark once it's open.
  const onDark = pathname === "/" && !scrolled && !menuOpen;

  return (
    <header
      className={cn(
        "sticky top-0 z-50 transition-all duration-300 ease-soft",
        scrolled || menuOpen
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
          <Link
            href="/build"
            className={cn(buttonClasses("primary", "sm"), "hidden sm:inline-flex")}
          >
            Build a protocol
          </Link>
          <button
            type="button"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            aria-controls="mobile-nav"
            onClick={() => setMenuOpen((v) => !v)}
            className={cn(
              "inline-flex h-9 w-9 items-center justify-center rounded-md transition-colors md:hidden",
              onDark
                ? "text-on-dark hover:bg-white/10"
                : "text-ink hover:bg-surface-muted",
            )}
          >
            {menuOpen ? (
              <X className="h-5 w-5" aria-hidden="true" />
            ) : (
              <Menu className="h-5 w-5" aria-hidden="true" />
            )}
          </button>
        </div>
      </div>

      {menuOpen && (
        <nav
          id="mobile-nav"
          className="border-t border-border bg-bg px-5 py-3 md:hidden"
        >
          <ul className="flex flex-col">
            {NAV.map((item) => {
              const active =
                pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={cn(
                      "block py-3 text-base font-medium text-muted transition-colors",
                      active && "text-ink",
                    )}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
          <Link
            href="/build"
            className={cn(buttonClasses("primary", "md"), "mt-2 w-full")}
          >
            Build a protocol
          </Link>
        </nav>
      )}
    </header>
  );
}
