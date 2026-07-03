import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function MarkdownView({ markdown }: { markdown: string }) {
  if (!markdown) {
    return <p className="text-sm text-muted">No markdown available.</p>;
  }
  return (
    <div className="rounded-xl border border-border bg-surface p-6 shadow-card">
      <div
        className="text-sm leading-relaxed text-muted [&_a]:text-accent [&_a]:underline [&_code]:rounded [&_code]:bg-surface-muted [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[0.82em] [&_h1]:mb-2 [&_h1]:mt-0 [&_h1]:font-display [&_h1]:text-2xl [&_h1]:font-medium [&_h1]:text-ink [&_h2]:mb-2 [&_h2]:mt-6 [&_h2]:font-display [&_h2]:text-lg [&_h2]:font-medium [&_h2]:text-ink [&_h3]:mb-1 [&_h3]:mt-4 [&_h3]:font-semibold [&_h3]:text-ink [&_li]:mt-1 [&_p]:mt-3 [&_strong]:font-semibold [&_strong]:text-ink [&_ul]:mt-2 [&_ul]:list-disc [&_ul]:pl-5"
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
      </div>
    </div>
  );
}
