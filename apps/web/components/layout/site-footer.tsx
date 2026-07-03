import Link from "next/link";
import { Wordmark } from "./logo";

export function SiteFooter() {
  return (
    <footer className="mt-24 border-t border-on-dark-border bg-ink-surface text-on-dark">
      <div className="mx-auto w-full max-w-[var(--container-page)] px-5 py-14 sm:px-8">
        <div className="flex flex-col justify-between gap-10 md:flex-row">
          <div className="max-w-xs">
            <Wordmark tone="inverted" />
            <p className="mt-4 text-sm leading-relaxed text-on-dark-muted">
              A science-backed training protocol builder. Every suggestion is ranked
              and cited to the peer-reviewed evidence behind it.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-10 sm:grid-cols-3">
            <FooterCol
              title="Product"
              links={[
                { href: "/build", label: "Build a protocol" },
                { href: "/exercises", label: "Exercise library" },
                { href: "/science", label: "Methodology" },
              ]}
            />
            <FooterCol
              title="Evidence"
              links={[
                { href: "/science#tiers", label: "Evidence tiers" },
                { href: "/science#retrieval", label: "How retrieval works" },
                { href: "/#how", label: "How it works" },
              ]}
            />
            <FooterCol
              title="Sources"
              links={[
                { href: "https://pubmed.ncbi.nlm.nih.gov/", label: "PubMed / NCBI", external: true },
                {
                  href: "https://github.com/yuhonas/free-exercise-db",
                  label: "Free Exercise DB",
                  external: true,
                },
              ]}
            />
          </div>
        </div>

        <div className="mt-12 flex flex-col gap-3 border-t border-on-dark-border pt-6 text-xs text-on-dark-subtle sm:flex-row sm:items-center sm:justify-between">
          <p>
            Evidence sourced from PubMed/NCBI · Exercise data from the Free Exercise DB.
          </p>
          <p>
            Protocol is an educational tool, not medical advice. Consult a professional
            before starting a new program.
          </p>
        </div>
      </div>
    </footer>
  );
}

function FooterCol({
  title,
  links,
}: {
  title: string;
  links: { href: string; label: string; external?: boolean }[];
}) {
  return (
    <div>
      <h4 className="text-[0.78rem] font-semibold uppercase tracking-[0.12em] text-on-dark-subtle">
        {title}
      </h4>
      <ul className="mt-4 space-y-2.5">
        {links.map((l) => (
          <li key={l.label}>
            {l.external ? (
              <a
                href={l.href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-on-dark-muted transition-colors hover:text-accent-on-dark"
              >
                {l.label}
              </a>
            ) : (
              <Link
                href={l.href}
                className="text-sm text-on-dark-muted transition-colors hover:text-accent-on-dark"
              >
                {l.label}
              </Link>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
