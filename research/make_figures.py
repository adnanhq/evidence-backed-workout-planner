"""Render every figure in the paper from results/*.json.

Figures are written to research/figures/ as PNG (300 dpi) and PDF. Each one has a
matching CSV in results/, which is also what satisfies the relief rule for the
palette slots that sit below 3:1 contrast on a light surface.

    ./.venv/bin/python -m research.make_figures
"""
from __future__ import annotations

from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import PercentFormatter

from research.common import FIGURES_DIR, banner, read_results

# Validated categorical slots (light mode, adjacent pairlist) from the reference
# palette; the contrast WARN on aqua/yellow/magenta is relieved by direct labels.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e5e2dc"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 9, "axes.titlesize": 10.5, "axes.labelsize": 9,
    "axes.edgecolor": GRID, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7,
    "legend.frameon": False, "figure.dpi": 130,
})

ARM_LABELS = {
    "baseline_minilm": "MiniLM-L6 (shipped)\n22M · general",
    "general_small": "bge-small\n33M · general",
    "general_base": "bge-base\n110M · general",
    "biomed_base": "PubMedBERT\n110M · biomedical",
    "biomed_retrieval": "S-PubMedBERT-MS-MARCO\n110M · biomedical+IR",
}
ARM_SHORT = {
    "baseline_minilm": "MiniLM-L6 (shipped)", "general_small": "bge-small",
    "general_base": "bge-base", "biomed_base": "PubMedBERT",
    "biomed_retrieval": "S-PubMedBERT-MS-MARCO",
}


def finish(fig: Any, name: str, title: str, subtitle: str = "") -> None:
    for axis in fig.axes:
        axis.set_axisbelow(True)
        for side in ("top", "right"):
            axis.spines[side].set_visible(False)
    fig.suptitle(title, x=0.012, ha="left", fontsize=12, fontweight="600", y=0.985)
    if subtitle:
        fig.text(0.012, 0.938, subtitle, ha="left", fontsize=8.8, color=MUTED)
    fig.savefig(FIGURES_DIR / ("%s.png" % name), dpi=300, bbox_inches="tight")
    fig.savefig(FIGURES_DIR / ("%s.pdf" % name), bbox_inches="tight")
    plt.close(fig)
    print("  wrote figures/%s.png" % name)


# --- F1 ------------------------------------------------------------------------------

def figure_tier() -> None:
    data = read_results("s1_tier_audit")
    tiers = ["meta_analysis", "systematic_review", "rct", "controlled_trial",
             "observational", "narrative_review", "other"]
    short = ["meta-analysis", "systematic rev.", "RCT", "controlled trial",
             "observational", "narrative rev.", "other"]
    matrix = data["comparisons"]["pt_full"]["confusion"]
    grid = np.array([[matrix[p][a] for a in tiers] for p in tiers], dtype=float)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.6, 4.5),
                                   gridspec_kw={"width_ratios": [1.15, 1]})
    normalised = grid / grid.sum(axis=1, keepdims=True).clip(min=1)
    ax1.imshow(normalised, cmap=matplotlib.colors.LinearSegmentedColormap.from_list("b", SEQ),
               vmin=0, vmax=1, aspect="auto")
    ax1.set_xticks(range(7), short, rotation=38, ha="right")
    ax1.set_yticks(range(7), short)
    ax1.set_xlabel("MEDLINE publication types only (reference)")
    ax1.set_ylabel("shipped grader (reads the abstract body)")
    ax1.grid(False)
    for row in range(7):
        for col in range(7):
            if grid[row, col]:
                ax1.text(col, row, "%d" % grid[row, col], ha="center", va="center",
                         fontsize=8.5, fontweight="600",
                         color="#ffffff" if normalised[row, col] > 0.55 else INK)
    ax1.set_title("Every disagreement sits above the diagonal", loc="left", pad=9)

    conditions = [("pt_only", "publication types only", SERIES[0]),
                  ("pt_title", "+ title", SERIES[1]),
                  ("pt_full", "+ abstract body (shipped)", SERIES[2])]
    width, positions = 0.26, np.arange(7)
    for index, (key, label, colour) in enumerate(conditions):
        counts = [data["tier_distribution"][key].get(t, 0) for t in tiers]
        offset = (index - 1) * width
        bars = ax2.bar(positions + offset, counts, width * 0.88, label=label, color=colour,
                       linewidth=0)
        for rect, value in zip(bars, counts):
            if value:
                ax2.text(rect.get_x() + rect.get_width() / 2, value + 4, "%d" % value,
                         ha="center", fontsize=7.4, color=MUTED)
    ax2.set_xticks(positions, short, rotation=38, ha="right")
    ax2.set_ylabel("studies (n = 502)")
    ax2.legend(loc="upper left", fontsize=8.5)
    ax2.xaxis.grid(False)
    ax2.set_title("Widening the text only ever promotes a study", loc="left", pad=9)

    stronger = data["comparisons"]["pt_full"]["graded_stronger_rate"]
    kappa = data["comparisons"]["pt_full"]["cohen_kappa"]
    finish(fig, "f1_tier_grading",
           "The study-design grader inflates evidence tiers, and only upward",
           "n=502. Reference is the engine's own classifier restricted to MEDLINE tags. "
           "Agreement %.1f%%, kappa %.3f; %.1f%% of studies graded stronger, 0.0%% weaker."
           % (100 * data["comparisons"]["pt_full"]["exact_agreement"], kappa, 100 * stronger))


# --- F2 ------------------------------------------------------------------------------

def figure_retrieval() -> None:
    data = read_results("s2_retrieval_eval")
    formulations = ["boolean", "topic", "question", "production_template"]
    labels = ["the boolean PubMed\nquery (ceiling)", "the bare topic", "the topic as\na question",
              "the production\nquery template"]
    arms = [a for a in ARM_LABELS if a in data["stage1"]]

    fig, ax = plt.subplots(figsize=(11.2, 4.9))
    width, positions = 0.15, np.arange(len(formulations))
    for index, arm in enumerate(arms):
        values = [data["stage1"][arm][f]["ndcg_at_10"] for f in formulations]
        lows = [data["stage1"][arm][f]["ndcg_at_10_ci"][0] for f in formulations]
        highs = [data["stage1"][arm][f]["ndcg_at_10_ci"][1] for f in formulations]
        offset = (index - (len(arms) - 1) / 2) * width
        ax.bar(positions + offset, values, width * 0.86, color=SERIES[index], linewidth=0,
               label=ARM_SHORT[arm])
        ax.errorbar(positions + offset, values,
                    yerr=[np.array(values) - np.array(lows), np.array(highs) - np.array(values)],
                    fmt="none", ecolor=MUTED, elinewidth=0.9, capsize=2.2)
    shipped = data["stage1"]["baseline_minilm"]
    left = shipped["boolean"]["ndcg_at_10"]
    right = shipped["production_template"]["ndcg_at_10"]
    edge = -(len(arms) - 1) / 2 * width
    ax.annotate("", xy=(3 + edge, right + 0.02), xytext=(0 + edge, left + 0.02),
                arrowprops=dict(arrowstyle="->", color=MUTED, linewidth=1.1,
                                connectionstyle="arc3,rad=-0.12"))
    ax.text(1.5, 0.556, "the shipped model loses %.0f%% of its nDCG between\nthe raw query and "
            "the production query template" % (100 * (1 - right / left)),
            ha="center", fontsize=9, color=INK)
    ax.text(0 + edge, left + 0.055, "%.2f" % left, ha="center", fontsize=9,
            fontweight="600", color=SERIES[0])
    ax.text(3 + edge, right + 0.055, "%.2f" % right, ha="center", fontsize=9,
            fontweight="600", color=SERIES[0])
    ax.set_xticks(positions, labels)
    ax.set_ylabel("nDCG@10  (95% CI, n = 49 queries)")
    ax.set_ylim(0, 0.63)
    ax.xaxis.grid(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=5, fontsize=8.5)
    best = max(data["stage1"][a]["production_template"]["ndcg_at_10"] for a in arms)
    worst_boolean = min(data["stage1"][a]["boolean"]["ndcg_at_10"] for a in arms)
    finish(fig, "f2_retrieval_quality",
           "How the query is written matters far more than which embedding model is used",
           "Model choice spans %.3f nDCG and no arm differs significantly from the shipped one "
           "(Wilcoxon p >= %.2f). Query formulation spans %.3f. The best model on the production "
           "template (%.3f) still scores below the worst model on the raw boolean query (%.3f)."
           % (max(data["stage1"][a]["production_template"]["ndcg_at_10"] for a in arms)
              - min(data["stage1"][a]["production_template"]["ndcg_at_10"] for a in arms),
              min(v["wilcoxon_p"] for v in data["stage1_paired_vs_baseline"].values()),
              max(data["stage1"][a]["boolean"]["ndcg_at_10"] for a in arms)
              - min(data["stage1"][a]["production_template"]["ndcg_at_10"] for a in arms),
              best, worst_boolean))


# --- F3 ------------------------------------------------------------------------------

def figure_threshold() -> None:
    data = read_results("s2b_threshold_roc")
    arms = [a for a in ARM_LABELS if a in data["arms"]]
    fig, axes = plt.subplots(1, len(arms), figsize=(13.4, 3.5), sharey=True)
    for axis, arm in zip(np.atleast_1d(axes), arms):
        block = data["arms"][arm]
        sweep = block["sweep"]
        thresholds = [row["threshold"] for row in sweep]
        admitted = [row["mean_corpus_fraction_admitted"] for row in sweep]
        axis.plot(thresholds, admitted, color=SERIES[0], linewidth=2.0)
        axis.axvline(0.50, color=SERIES[1], linewidth=1.6, linestyle="--")
        at50 = block["at_shipped_ceiling_0.50"]["mean_corpus_fraction_admitted"]
        axis.plot([0.50], [at50], "o", color=SERIES[1], markersize=8,
                  markeredgecolor=SURFACE, markeredgewidth=2)
        axis.annotate("%.0f%%" % (100 * at50), (0.50, at50), textcoords="offset points",
                      xytext=(7, 8), fontsize=9, fontweight="600", color=SERIES[1])
        axis.axvline(block["best_separating_ceiling_in_this_space"], color=SERIES[2],
                     linewidth=1.4, linestyle=":")
        axis.set_title(ARM_LABELS[arm], loc="left", fontsize=8.6, pad=7)
        axis.set_xlabel("cosine ceiling")
        axis.set_xlim(0.2, 0.8)
        axis.yaxis.set_major_formatter(PercentFormatter(1.0))
        axis.xaxis.grid(False)
    np.atleast_1d(axes)[0].set_ylabel("corpus admitted")
    handles = [
        plt.Line2D([], [], color=SERIES[0], lw=2, label="corpus admitted vs ceiling"),
        plt.Line2D([], [], color=SERIES[1], lw=1.6, ls="--", label="shipped ceiling (0.50)"),
        plt.Line2D([], [], color=SERIES[2], lw=1.4, ls=":", label="best ceiling in this space"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=8.5,
               bbox_to_anchor=(0.5, -0.10))
    finish(fig, "f3_threshold_calibration",
           "The one hard filter on semantic retrieval is calibrated to a single embedding model",
           "The shipped 0.50 cosine ceiling was tuned for MiniLM. In three of the other four "
           "spaces it admits 95-100%% of the corpus and rejects none of the off-topic probes; "
           "in the fourth it admits 1.5%%. The best ceiling ranges from 0.20 to 0.53.")


# --- F4 ------------------------------------------------------------------------------

def figure_attribution() -> None:
    data = read_results("s3_attribution_audit")
    per_muscle = data["b_muscle_disconnect"]["per_muscle"]
    order = sorted(per_muscle, key=lambda m: per_muscle[m]["coverage_rate"])
    positions = np.arange(len(order))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.4, 5.0), sharey=True,
                                   gridspec_kw={"width_ratios": [1, 1]})
    coverage = [per_muscle[m]["coverage_rate"] for m in order]
    ax1.barh(positions, coverage, 0.68, color=SERIES[0], linewidth=0)
    for pos, value, muscle in zip(positions, coverage, order):
        ax1.text(value + 0.012, pos, "%.0f%% of %d" % (100 * value, per_muscle[muscle]["n_exercises"]),
                 va="center", fontsize=7.6, color=MUTED)
    ax1.set_yticks(positions, [m.replace("_", " ") for m in order])
    ax1.set_xlim(0, 0.88)
    ax1.xaxis.set_major_formatter(PercentFormatter(1.0))
    ax1.set_xlabel("exercises carrying at least one citation")
    ax1.yaxis.grid(False)
    ax1.set_title("What reaches the catalog", loc="left", pad=9)

    supply = [per_muscle[m]["corpus_supply"] for m in order]
    ax2.barh(positions, supply, 0.68, color=SERIES[1], linewidth=0)
    for pos, value in zip(positions, supply):
        ax2.text(value + 0.9, pos, "%d" % value, va="center", fontsize=7.6, color=MUTED)
    ax2.set_xlabel("corpus studies mentioning the muscle")
    ax2.yaxis.grid(False)
    ax2.set_title("What the corpus holds", loc="left", pad=9)

    alias = data["c_alias_mechanism"]
    finish(fig, "f4_attribution_coverage",
           "The science is in the corpus; the name-matching step is where it is lost",
           "Coverage ranges from 0%% to 64%% and does not follow supply: forearms, traps and hip "
           "abductors have corpus coverage and cite nothing. Only %d of %d catalog aliases ever "
           "match a study, and %d of those %d are exactly two words long."
           % (alias["n_distinct_aliases_that_ever_match"], alias["n_distinct_aliases_in_catalog"],
              alias["matched_alias_word_count"]["histogram"].get("2",
                  alias["matched_alias_word_count"]["histogram"].get(2, 0)),
              alias["n_distinct_aliases_that_ever_match"]))


# --- F5 ------------------------------------------------------------------------------

def figure_specificity() -> None:
    try:
        data = read_results("s3c_judgments")
    except FileNotFoundError:
        print("  (skipping f5: judgments not available yet)")
        return
    summary = data["summary"]
    mechanisms = [(k, l) for k, l in (("alias_match", "attached by name (alias match)"),
                                      ("semantic_fallback", "attached by meaning (vector search)"))
                  if k in summary]
    levels = ["movement_involved_rate", "goal_supported_rate", "variant_exact_rate"]
    labels = ["study used\nthis movement", "and reports a\nrelevant outcome",
              "and used this\nexact variant"]

    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    width, positions = 0.3, np.arange(3)
    for index, (key, label) in enumerate(mechanisms):
        values = [summary[key][level] for level in levels]
        offset = (index - (len(mechanisms) - 1) / 2) * width
        ax.bar(positions + offset, values, width * 0.86, color=SERIES[index], linewidth=0,
               label="%s  (n=%d)" % (label, summary[key]["n"]))
        for pos, value in zip(positions + offset, values):
            ax.text(pos, value + 0.014, "%.0f%%" % (100 * value), ha="center", fontsize=8.6,
                    fontweight="600", color=MUTED)
    ax.set_xticks(positions, labels)
    ax.set_ylabel("share of cited pairs")
    ax.set_ylim(0, 1.05)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.xaxis.grid(False)
    ax.legend(loc="upper right", fontsize=8.6)
    finish(fig, "f5_citation_specificity",
           "A citation's support depends entirely on how specific a claim you read into it",
           "The same citations, judged at three increasing levels of specificity. Both attachment "
           "mechanisms are scored on one rubric by the same adjudicator.")


# --- F6 ------------------------------------------------------------------------------

def figure_confidence() -> None:
    from research.common import load_catalog

    data = read_results("s4_conformance")
    exercises = load_catalog()["exercises"]
    counts = np.array([e["evidence"].get("direct_evidence_count", 0) for e in exercises], float)
    scores = np.array([e["evidence"]["confidence_score"] for e in exercises], float)
    levels = [e["evidence"]["confidence_level"] for e in exercises]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 4.4),
                                   gridspec_kw={"width_ratios": [1.35, 1]})
    rng = np.random.default_rng(20260818)
    jitter = rng.uniform(-0.22, 0.22, len(counts))
    for index, level in enumerate(("high", "moderate", "low")):
        mask = np.array([lv == level for lv in levels])
        ax1.scatter(counts[mask] + jitter[mask], scores[mask], s=9, alpha=0.45,
                    color=SERIES[index], linewidths=0, label="%s (n=%d)" % (level, int(mask.sum())))
    ax1.axhline(0.75, color=MUTED, linewidth=1.0, linestyle="--")
    ax1.text(8.1, 0.757, "0.75 — 'high' threshold", fontsize=7.8, color=MUTED, ha="right")
    ax1.axhline(0.72, color=SERIES[1], linewidth=1.2, linestyle=":")
    ax1.text(8.1, 0.695, "0.72 — heuristic cap (guardrail holds)", fontsize=7.8,
             color=SERIES[1], ha="right")
    floor = data["confidence_calibration"]["zero_evidence_score"]["min"]
    ax1.annotate("floor %.2f: the score never\nreports 'no evidence'" % floor,
                 xy=(0, floor), xytext=(1.5, 0.30), fontsize=8.2, color=INK,
                 arrowprops=dict(arrowstyle="->", color=MUTED, linewidth=0.9))
    ax1.set_xlabel("directly linked studies")
    ax1.set_ylabel("displayed confidence score")
    ax1.legend(loc="lower right", fontsize=8.2)
    ax1.set_title("The score ranks correctly but has a floor", loc="left", pad=9)

    precision = data["confidence_calibration"]["label_precision"]
    order = ["high", "moderate", "low"]
    values = [precision[l]["p_has_evidence_given_label"] for l in order]
    bars = ax2.bar(range(3), values, 0.55,
                   color=[SERIES[0], SERIES[1], SERIES[2]], linewidth=0)
    for rect, value, level in zip(bars, values, order):
        ax2.text(rect.get_x() + rect.get_width() / 2, value + 0.02,
                 "%.0f%%" % (100 * value), ha="center", fontsize=10, fontweight="600", color=MUTED)
        ax2.text(rect.get_x() + rect.get_width() / 2, 0.03, "n=%d" % precision[level]["n"],
                 ha="center", fontsize=8, color="#ffffff")
    ax2.set_xticks(range(3), order)
    ax2.set_ylim(0, 1.12)
    ax2.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax2.set_ylabel("P(any direct evidence | label)")
    ax2.xaxis.grid(False)
    ax2.set_title("What each label actually predicts", loc="left", pad=9)

    finish(fig, "f6_confidence_calibration",
           "The published guardrail holds, but 'moderate' carries almost no evidential weight",
           "No zero-evidence exercise is ever labelled 'high', exactly as the methodology page "
           "claims. But 'moderate' is applied to 1,006 exercises of which only 5.9%% have any "
           "directly linked study at all.")


# --- F7 ------------------------------------------------------------------------------

def figure_repair() -> None:
    try:
        repair = read_results("s2c_query_repair")
        s2 = read_results("s2_retrieval_eval")
    except FileNotFoundError:
        print("  (skipping f7: repair results not available)")
        return

    order = ["current", "drop_scheduling", "lead_with_need", "minimal", "minimal_with_equipment"]
    order = [v for v in order if v in repair["variants"]]
    labels = ["shipped\n(as audited)", "drop\nscheduling", "lead with\nthe need",
              "minimal\n(chosen)", "minimal +\nequipment"]
    labels = labels[:len(order)]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 4.6),
                                   gridspec_kw={"width_ratios": [1.2, 1], "wspace": 0.28})

    width, positions = 0.36, np.arange(len(order))
    for index, split in enumerate(("dev", "heldout")):
        values = [repair["variants"][v][split]["ndcg_at_10"] for v in order]
        offset = (index - 0.5) * width
        ax1.bar(positions + offset, values, width * 0.88, color=SERIES[index], linewidth=0,
                label="selection half (n=%d)" % len(repair["dev_indices"]) if split == "dev"
                else "held-out half (n=%d)" % len(repair["heldout_indices"]))
    winner = repair["winner"]
    held = repair["variants"][winner]["heldout"]
    win_at = order.index(winner)
    ax1.text(win_at + 0.5 * width, held["ndcg_at_10"] + 0.012,
             "%.3f\np=%.4f" % (held["ndcg_at_10"], held["wilcoxon_p"]),
             ha="center", fontsize=8.4, fontweight="600", color=SERIES[1])
    ax1.text(0 - 0.5 * width, repair["variants"]["current"]["dev"]["ndcg_at_10"] + 0.012,
             "%.3f" % repair["variants"]["current"]["dev"]["ndcg_at_10"],
             ha="center", fontsize=8.4, fontweight="600", color=SERIES[0])
    ax1.set_xticks(positions, labels)
    ax1.set_ylabel("nDCG@10")
    ax1.set_ylim(0, 0.30)
    ax1.xaxis.grid(False)
    ax1.legend(loc="upper left", fontsize=8.4)
    ax1.set_title("The winner was chosen on one half, measured on the other",
                  loc="left", pad=9)

    arms = [a for a in ARM_LABELS if a in s2["stage1"]]
    before = [s2["stage1"][a]["production_template"]["ndcg_at_10"] for a in arms]
    after = [s2["stage1"][a]["production_template_fixed"]["ndcg_at_10"] for a in arms]
    ypos = np.arange(len(arms))
    for y, b, a in zip(ypos, before, after):
        ax2.plot([b, a], [y, y], color=GRID, linewidth=2.4, solid_capstyle="round", zorder=1)
    ax2.scatter(before, ypos, s=52, color=SERIES[0], zorder=3, label="as audited",
                edgecolors=SURFACE, linewidths=1.4)
    ax2.scatter(after, ypos, s=52, color=SERIES[1], zorder=3, label="after the repair",
                edgecolors=SURFACE, linewidths=1.4)
    for y, b, a in zip(ypos, before, after):
        ax2.text(a + 0.012, y, "+%.0f%%" % (100 * (a / b - 1)), va="center",
                 fontsize=8.4, fontweight="600", color=MUTED)
    compact = dict(ARM_SHORT, biomed_retrieval="S-PubMedBERT")
    ax2.set_yticks(ypos, [compact[a] for a in arms], fontsize=8.6)
    ax2.set_xlabel("nDCG@10 on the production query")
    ax2.set_xlim(0, 0.46)
    ax2.yaxis.grid(False)
    ax2.invert_yaxis()
    ax2.legend(loc="upper right", fontsize=8.4)
    ax2.set_title("It is not model-specific", loc="left", pad=9)

    finish(fig, "f7_query_repair",
           "The dominant lever, changed and re-measured",
           "Removing the session count, split template, equipment list and candidate exercise "
           "names from the query raises nDCG@10 by %.0f%% on held-out queries (p=%.4f), and "
           "improves every embedding model tested \u2014 without reducing how often a request "
           "yields any citation." % (100 * held["relative_gain"], held["wilcoxon_p"]))


def main() -> None:
    banner("rendering figures")
    figure_tier()
    figure_retrieval()
    figure_threshold()
    figure_attribution()
    figure_specificity()
    figure_confidence()
    figure_repair()
    print("\nfigures in %s" % FIGURES_DIR)


if __name__ == "__main__":
    main()
