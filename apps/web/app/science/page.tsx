import "katex/dist/katex.min.css";
import katex from "katex";
import type { Metadata } from "next";
import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  Bot,
  Database,
  FlaskConical,
  Link2,
  Search,
} from "lucide-react";
import { Eyebrow, Section } from "@/components/layout/section";
import { Reveal } from "@/components/layout/reveal";
import { TierLegend } from "@/components/evidence/tier-legend";

export const metadata: Metadata = {
  title: "The science",
  description:
    "The full Protocol pipeline — how exercises are collected, how evidence is graded and attached, how retrieval and ranking work, and the guardrails around the AI planner.",
};

/* ---------------------------------------------------------------- helpers */

function TeX({ tex, block = false }: { tex: string; block?: boolean }) {
  const html = katex.renderToString(tex, {
    throwOnError: false,
    displayMode: block,
  });
  if (block) {
    return (
      <div
        className="overflow-x-auto py-1 text-[0.95rem] text-ink"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    );
  }
  return (
    <span
      className="text-[0.92em] text-ink"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

function EquationCard({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mt-5 rounded-xl border border-border bg-surface p-5 shadow-xs">
      <p className="text-[0.72rem] font-semibold uppercase tracking-[0.12em] text-subtle">
        {label}
      </p>
      <div className="mt-3 space-y-2">{children}</div>
    </div>
  );
}

function Terms({ items }: { items: [React.ReactNode, string][] }) {
  return (
    <dl className="mt-3 grid gap-x-6 gap-y-1.5 border-t border-border pt-3 sm:grid-cols-2">
      {items.map(([term, def], i) => (
        <div key={i} className="flex items-baseline gap-2.5 text-[0.84rem]">
          <dt className="shrink-0">{term}</dt>
          <dd className="leading-relaxed text-subtle">{def}</dd>
        </div>
      ))}
    </dl>
  );
}

function Facts({ items }: { items: [string, string][] }) {
  return (
    <div className="mt-5 flex flex-wrap gap-2">
      {items.map(([value, label]) => (
        <span
          key={label}
          className="inline-flex items-baseline gap-1.5 rounded-lg border border-border bg-surface-muted px-3 py-1.5 text-[0.8rem]"
        >
          <span className="tnum font-mono font-semibold text-ink">{value}</span>
          <span className="text-subtle">{label}</span>
        </span>
      ))}
    </div>
  );
}

function Stage({
  n,
  id,
  icon: Icon,
  title,
  children,
}: {
  n: string;
  id: string;
  icon: LucideIcon;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <article id={id} className="scroll-mt-24">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent-subtle text-accent">
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="tnum font-mono text-xs font-medium text-subtle">
            Stage {n}
          </p>
          <h2 className="font-display text-2xl font-semibold text-ink sm:text-[1.65rem]">
            {title}
          </h2>
        </div>
      </div>
      <div className="mt-4 space-y-3">{children}</div>
    </article>
  );
}

function P({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[0.98rem] leading-relaxed text-muted">{children}</p>
  );
}

/* ------------------------------------------------------------------ page */

const STAGES = [
  { n: "01", id: "catalog", label: "Exercise catalog" },
  { n: "02", id: "corpus", label: "Evidence corpus" },
  { n: "03", id: "attachment", label: "Study attachment" },
  { n: "04", id: "ranking", label: "Confidence & ranking" },
  { n: "05", id: "retrieval", label: "Semantic retrieval" },
  { n: "06", id: "planner", label: "AI planner & guardrails" },
];

export default function SciencePage() {
  return (
    <div className="pb-10">
      <Section className="pt-12 sm:pt-16">
        <div className="max-w-3xl">
          <Eyebrow>Methodology</Eyebrow>
          <h1 className="mt-3 font-display text-[2.3rem] font-semibold leading-tight text-ink sm:text-5xl">
            The science behind Protocol
          </h1>
          <p className="mt-5 text-lg leading-relaxed text-muted">
            Every recommendation is produced by a six-stage pipeline that turns raw
            datasets and peer-reviewed research into a plan you can verify line by
            line. This page documents each stage — including the actual scoring
            functions the engine runs.
          </p>
          <nav className="mt-7 flex flex-wrap gap-2">
            {STAGES.map((s) => (
              <a
                key={s.id}
                href={`#${s.id}`}
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-[0.8rem] font-medium text-muted transition-colors hover:border-accent hover:text-accent"
              >
                <span className="tnum font-mono text-xs text-subtle">{s.n}</span>
                {s.label}
              </a>
            ))}
          </nav>
        </div>
      </Section>

      <Section className="mt-14">
        <div className="mx-auto max-w-3xl space-y-16">
          {/* ------------------------------------------------ 01 · catalog */}
          <Reveal>
            <Stage n="01" id="catalog" icon={Database} title="The exercise catalog">
              <P>
                The movement library starts from the open ExerciseDB dataset — 1,324
                exercises with images and video — and is normalized into a single
                canonical taxonomy: every exercise carries its equipment, difficulty,
                mechanic (compound vs. isolation), force vector, and most importantly a
                strict split between <em>primary movers</em> and <em>secondary
                synergists</em>.
              </P>
              <P>
                That split is enforced everywhere. A shoulder press recruits the
                mid-back as a stabilizer, so the dataset lists it as a synergist — but
                the engine never treats it as a mid-back exercise. Filters, rankings,
                and the planner all target primary movers only, which keeps every
                muscle&apos;s exercise list clean instead of flooded with incidental
                overlap.
              </P>
              <Facts
                items={[
                  ["1,324", "exercises"],
                  ["16", "muscle groups"],
                  ["19", "equipment types"],
                  ["700 / 624", "compound / isolation"],
                ]}
              />
            </Stage>
          </Reveal>

          {/* ------------------------------------------------- 02 · corpus */}
          <Reveal>
            <Stage n="02" id="corpus" icon={FlaskConical} title="The evidence corpus">
              <P>
                The research library is pulled from PubMed/NCBI with 103 targeted
                queries across resistance-training topics — frequency, volume, exercise
                selection, rep ranges, regional hypertrophy, recovery — restricted to
                studies published in 2018 or later. Each study is parsed for its
                publication type and graded into an evidence tier, from meta-analyses
                (
                <TeX tex="s_{\text{tier}} = 1.0" />) down to unclassified reports (
                <TeX tex="s_{\text{tier}} = 0.4" />
                ).
              </P>
              <P>
                A study&apos;s overall retrieval weight blends how strong it is, how
                recent it is, and how squarely it sits on the requested topic:
              </P>
              <EquationCard label="Study retrieval weight">
                <TeX
                  block
                  tex="w \;=\; 0.55\, s_{\text{tier}} \;+\; 0.25\, s_{\text{recency}} \;+\; 0.20\, s_{\text{topic}}"
                />
                <TeX
                  block
                  tex="s_{\text{recency}} \;=\; \operatorname{clip}\!\Bigl(1 - \tfrac{Y_{\text{now}} - Y_{\text{pub}}}{10},\; 0,\; 1\Bigr)"
                />
                <Terms
                  items={[
                    [<TeX key="t" tex="s_{\text{tier}}" />, "evidence-tier score (1.0 meta-analysis … 0.4 other)"],
                    [<TeX key="r" tex="s_{\text{recency}}" />, "linear decay over 10 years since publication"],
                    [<TeX key="p" tex="s_{\text{topic}}" />, "keyword overlap with the topic cluster that fetched it"],
                  ]}
                />
              </EquationCard>
              <P>
                Studies with missing abstracts, weak grading signals, or low topical
                relevance are flagged for manual review — 147 of the 502 carry that
                flag, and it follows them through the product as a visible
                &ldquo;lower-trust&rdquo; badge rather than being silently dropped.
              </P>
              <div className="mt-5 rounded-xl border border-border bg-surface p-6 shadow-xs">
                <p className="text-[0.76rem] font-semibold uppercase tracking-[0.1em] text-subtle">
                  Evidence tiers — strongest first
                </p>
                <TierLegend className="mt-4" />
              </div>
              <Facts
                items={[
                  ["502", "studies"],
                  ["103", "PubMed queries"],
                  ["2018+", "publication window"],
                  ["147", "flagged for review"],
                ]}
              />
            </Stage>
          </Reveal>

          {/* --------------------------------------------- 03 · attachment */}
          <Reveal>
            <Stage n="03" id="attachment" icon={Link2} title="Linking studies to exercises">
              <P>
                Direct evidence links are built offline by scanning every study&apos;s
                title and abstract for an exercise&apos;s name phrases, using
                word-boundary matching. A match alone is not enough to create a link —
                it must survive two gates:
              </P>
              <ul className="list-disc space-y-2 pl-5 text-[0.98rem] leading-relaxed text-muted">
                <li>
                  <span className="font-medium text-ink">Program-list exclusion.</span>{" "}
                  If an exercise only appears inside a long list of a study&apos;s
                  training program (&ldquo;…squat, bench press, curl, and shoulder
                  press&rdquo;), the study is about the program, not the exercise — no
                  link is created.
                </li>
                <li>
                  <span className="font-medium text-ink">Muscle-context gate.</span>{" "}
                  The matched phrase must contain a recognized movement term or a token
                  of the exercise&apos;s own muscles. A quadriceps paper that merely
                  shares the words &ldquo;full range&rdquo; with a lat pulldown&apos;s
                  name can never attach to it.
                </li>
              </ul>
              <P>
                Attribution is deliberately movement-level: a bench-press study supports
                every bench-press variant, because abstracts rarely distinguish flat
                from incline. Variants share their movement&apos;s evidence rather than
                each pretending to own a private slice of it — and the tie flags in
                Stage 04 make that sharing visible.
              </P>
              <Facts
                items={[
                  ["1,915", "study–exercise links"],
                  ["345", "exercises with direct evidence"],
                ]}
              />
            </Stage>
          </Reveal>

          {/* ------------------------------------------------ 04 · ranking */}
          <Reveal>
            <Stage n="04" id="ranking" icon={BarChart3} title="Confidence & ranking">
              <P>
                Every exercise gets an evidence-confidence score. With direct studies
                attached, confidence is computed from the best study&apos;s quality,
                the average retrieval weight, and a bonus that saturates with the
                number of independent studies:
              </P>
              <EquationCard label="Evidence confidence (direct studies attached)">
                <TeX
                  block
                  tex="c \;=\; \operatorname{clip}\bigl(\, 0.35\, q_{\max} + 0.35\, \bar{w} + 0.20 + \min(0.2,\; 0.04\, n) \,\bigr)"
                />
                <Terms
                  items={[
                    [<TeX key="q" tex="q_{\max}" />, "quality score of the strongest attached study"],
                    [<TeX key="w" tex="\bar{w}" />, "mean retrieval weight across attached studies"],
                    [<TeX key="n" tex="n" />, "number of attached studies (bonus caps at 5)"],
                  ]}
                />
              </EquationCard>
              <P>
                Exercises without direct studies fall back to a biomechanical heuristic
                (category and mechanic based) that is hard-capped at{" "}
                <TeX tex="c \le 0.72" /> — below the 0.75 threshold for a
                &ldquo;high&rdquo; confidence label. No exercise can look
                highly-evidenced without actual evidence.
              </P>
              <P>
                Ranking then blends goal fit with evidence, and at request time the
                score is adjusted for how well each candidate matches what you asked
                for:
              </P>
              <EquationCard label="Ranking score & request-time adjustment">
                <TeX
                  block
                  tex="r_{\text{goal}} \;=\; 0.65\, f_{\text{goal}} \;+\; 0.35\, e_{\text{evidence}}"
                />
                <TeX
                  block
                  tex="S \;=\; \operatorname{clip}\bigl(\, r_{\text{goal}} + b_{\text{prim}} + b_{\text{direct}} + b_{\text{conf}} - p_{\text{var}} - p_{\text{rev}} \,\bigr)"
                />
                <Terms
                  items={[
                    [<TeX key="f" tex="f_{\text{goal}}" />, "fit for the chosen goal (hypertrophy / strength)"],
                    [<TeX key="bp" tex="b_{\text{prim}}" />, "+0.05 primary-mover match, +0.02 secondary"],
                    [<TeX key="bd" tex="b_{\text{direct}}" />, "min(0.06, 0.03 × unflagged direct studies)"],
                    [<TeX key="bc" tex="b_{\text{conf}}" />, "0.05 × max(0, c − 0.55)"],
                    [<TeX key="pv" tex="p_{\text{var}}" />, "small penalty for obscure variations"],
                    [<TeX key="pr" tex="p_{\text{rev}}" />, "penalty when evidence is review-flagged"],
                  ]}
                />
              </EquationCard>
              <P>
                Within each muscle and goal, exercises are ordered by the tuple{" "}
                <TeX tex="\bigl(r_{\text{goal}},\; n_{\text{direct}},\; c\bigr)" /> —
                better-evidenced exercises win where the evidence actually differs.
                Where it doesn&apos;t, the rank is shown honestly as a tie (e.g.{" "}
                <span className="tnum font-mono text-[0.85em] text-ink">
                  #1/88 · tied×12
                </span>
                ) instead of implying a precision the data can&apos;t support.
              </P>
            </Stage>
          </Reveal>

          {/* ---------------------------------------------- 05 · retrieval */}
          <Reveal>
            <Stage n="05" id="retrieval" icon={Search} title="Semantic retrieval">
              <P>
                General findings — the studies cited in your plan&apos;s evidence
                appendix — are retrieved by meaning, not keywords. Every study is
                chunked and embedded with the <span className="font-mono text-[0.85em] text-ink">all-MiniLM-L6-v2</span>{" "}
                sentence transformer into a 384-dimensional vector store (1,264 chunks).
                Your request is compiled into a structured query — goal, muscles,
                session count, equipment, and the top candidate exercises — and matched
                by cosine distance:
              </P>
              <EquationCard label="Acceptance rule for retrieved studies">
                <TeX
                  block
                  tex="d(\mathbf{q}, \mathbf{c}) \;=\; 1 - \frac{\mathbf{q} \cdot \mathbf{c}}{\lVert \mathbf{q} \rVert\, \lVert \mathbf{c} \rVert} \;\le\; 0.50"
                />
                <TeX
                  block
                  tex="\rho \;=\; 2\,\rho_{\text{exercise}} \;+\; \rho_{\text{request}}"
                />
                <Terms
                  items={[
                    [<TeX key="d" tex="d(\mathbf{q}, \mathbf{c})" />, "cosine distance between query and study chunk"],
                    [<TeX key="re" tex="\rho_{\text{exercise}}" />, "keyword overlap with your candidate exercises"],
                    [<TeX key="rr" tex="\rho_{\text{request}}" />, "keyword overlap with your requested muscles & goal"],
                  ]}
                />
              </EquationCard>
              <P>
                The 0.50 distance ceiling isn&apos;t arbitrary — it was calibrated
                against this corpus: legitimate builder queries measure 0.23–0.45,
                while off-topic probes (yoga, nutrition, swimming) measure 0.51 and
                above. Results inside the ceiling are re-ranked by the relevance score{" "}
                <TeX tex="\rho" />, with retrieval weight breaking ties.
              </P>
              <P>
                Crucially, there is no &ldquo;best effort&rdquo; padding: if nothing
                passes both the distance ceiling and the relevance bar, the appendix
                says so instead of citing weakly related studies. An honest gap beats a
                confident-looking citation.
              </P>
            </Stage>
          </Reveal>

          {/* ------------------------------------------------ 06 · planner */}
          <Reveal>
            <Stage n="06" id="planner" icon={Bot} title="The AI planner & its guardrails">
              <P>
                Only after all of the above does an LLM enter the picture — and it
                plans, it doesn&apos;t pick facts. The engine hands it the top three
                evidence-ranked candidates per muscle (per deltoid head for shoulders),
                each with its rank, mechanic, and study support. The model decides the
                weekly split, places exercises compound-first across sessions, and
                prescribes sets, reps, and rest.
              </P>
              <P>Its output is constrained, not trusted:</P>
              <ul className="list-disc space-y-2 pl-5 text-[0.98rem] leading-relaxed text-muted">
                <li>
                  <span className="font-medium text-ink">Structured output.</span> The
                  response schema enum-locks exercise IDs to the shortlist — the model
                  is mathematically unable to cite an exercise (or study) that
                  isn&apos;t in its brief.
                </li>
                <li>
                  <span className="font-medium text-ink">Clamped prescriptions.</span>{" "}
                  Hypertrophy: <TeX tex="s \in [2,5]" /> sets,{" "}
                  <TeX tex="r \in [5,30]" /> reps, <TeX tex="[45,180]" /> s rest.
                  Strength: <TeX tex="s \in [3,6]" />, <TeX tex="r \in [3,8]" />,{" "}
                  <TeX tex="[120,300]" /> s. Out-of-range values are clamped; unusable
                  ones fall back to evidence-neutral defaults.
                </li>
                <li>
                  <span className="font-medium text-ink">Plan validation.</span> Every
                  session must satisfy size bounds, every requested muscle must be
                  scheduled, and no muscle may appear in every session of a
                  multi-muscle week. Invalid plans are retried with the errors, then
                  rejected.
                </li>
                <li>
                  <span className="font-medium text-ink">Model redundancy.</span> A
                  primary model is backed by fallback models on API failure; if every
                  model fails, a deterministic evidence-ranked planner produces the
                  plan — and the result is clearly labeled as such, never passed off
                  as AI-planned.
                </li>
              </ul>
              <P>
                Citations are attached by the engine after validation, from the
                evidence computed in stages 02–05 — the model never writes a PMID. The
                whole pipeline is covered by 73 automated tests, including regression
                tests for every guardrail above.
              </P>
            </Stage>
          </Reveal>

          {/* --------------------------------------------------- limitations */}
          <Reveal>
            <div className="rounded-xl border border-[#f0dcb8] bg-warning-subtle p-6">
              <h2 className="font-display text-xl font-medium text-ink">
                Limitations &amp; not medical advice
              </h2>
              <div className="mt-3 space-y-2.5 text-[0.95rem] leading-relaxed text-[#7a5518]">
                <p>
                  Evidence is movement-level, not per-variant: a bench-press study
                  supports every bench-press variant, and choosing between
                  equally-evidenced variants is an equipment and preference decision,
                  not an evidence ranking. Tier grading and topic matching are
                  automated heuristics and can misclassify individual studies — which
                  is why flags and tiers stay visible on every citation.
                </p>
                <p>
                  Protocol surfaces published research to inform your training — it is
                  an educational tool, not a substitute for professional medical or
                  coaching advice. Evidence in exercise science evolves, sample sizes
                  are often small, and individual response varies. Always consult a
                  qualified professional before starting a new program, especially if
                  you have an injury or medical condition.
                </p>
              </div>
            </div>
          </Reveal>
        </div>
      </Section>
    </div>
  );
}
