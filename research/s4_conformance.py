"""S4 - does the system do what it publicly says it does?

The app ships a methodology page (``apps/web/app/science/page.tsx``) stating its
formulas, its guardrails, and its counts. Auditing a system against its own
published specification is cheap and it is the last link in the chain: it is what
a user actually reads. Each claim below is re-derived from the committed data or
checked against the code, and reported as conforms / diverges either way.

    ./.venv/bin/python -m research.s4_conformance
"""
from __future__ import annotations

import collections
import re
import statistics
from pathlib import Path
from typing import Any

import math

from research.common import (
    ENGINE_DIR,
    REPO_ROOT,
    banner,
    environment_snapshot,
    load_catalog,
    load_corpus,
    mean,
    write_csv,
    write_results,
)

SCIENCE_PAGE = REPO_ROOT / "apps" / "web" / "app" / "science" / "page.tsx"
PROTOCOL_DEMO = ENGINE_DIR / "protocol_engine" / "protocol_demo.py"
MAPPERS = ENGINE_DIR / "app" / "mappers.py"
README = REPO_ROOT / "README.md"


def claim(name: str, published: Any, measured: Any, source: str, note: str = "") -> dict[str, Any]:
    conforms = str(published) == str(measured)
    return {
        "claim": name,
        "published": published,
        "measured": measured,
        "conforms": conforms,
        "source": source,
        "note": note,
    }


def published_stat(label: str) -> str:
    """Read a published figure out of the methodology page's stat pairs.

    Parsed rather than hardcoded so this module reports what the page says today and
    keeps working as a regression check, instead of asserting against a snapshot.
    """
    match = re.search(r'\["([\d,]+)",\s*"%s"\]' % re.escape(label), SCIENCE_PAGE.read_text())
    return match.group(1).replace(",", "") if match else "not found"


def published_readme_exercise_count() -> str:
    match = re.search(r"filters ([\d,]+) exercises", README.read_text())
    return match.group(1).replace(",", "") if match else "not found"


def numeric_claims(catalog: dict, corpus: dict) -> list[dict[str, Any]]:
    exercises = catalog["exercises"]
    metadata = corpus["metadata"]
    evidenced = sum(1 for e in exercises if e["evidence"].get("direct_evidence_count", 0) > 0)
    test_count = sum(
        len(re.findall(r"^\s*def test_", (ENGINE_DIR / "tests" / name).read_text(), re.M))
        for name in ("test_protocol_demo.py", "test_catalog_quality.py", "test_api.py")
    )
    return [
        claim("exercises in catalog", published_stat("exercises"), len(exercises),
              "science/page.tsx"),
        claim("studies in corpus", 502, len(corpus["documents"]), "science/page.tsx:253"),
        claim("PubMed queries", 103, metadata.get("total_queries"), "science/page.tsx:254"),
        claim("studies flagged for review", 147, metadata.get("manual_review_documents"),
              "science/page.tsx:256"),
        claim("exercises with direct evidence", published_stat("exercises with direct evidence"),
              evidenced, "science/page.tsx"),
        claim("automated tests", 73, test_count, "science/page.tsx:460"),
        claim("exercises (README)", published_readme_exercise_count(), len(exercises),
              "README.md",
              "873 here would be the record count of the unused Free Exercise DB dump"),
    ]


def guardrail_claims(catalog: dict) -> list[dict[str, Any]]:
    """Claims about mechanisms rather than counts. Checked empirically where possible."""
    exercises = catalog["exercises"]
    zero_evidence = [e for e in exercises
                     if e["evidence"].get("direct_evidence_count", 0) == 0]
    worst = max(e["evidence"]["confidence_score"] for e in zero_evidence)
    labels_at_zero = collections.Counter(e["evidence"]["confidence_level"] for e in zero_evidence)

    # "The model is mathematically unable to cite ... a study that isn't in its brief."
    demo_source = PROTOCOL_DEMO.read_text()
    schema_is_conditional = "def supports_structured_output" in demo_source
    schema_has_study_field = bool(re.search(r'"(pmid|study|citation)', demo_source.split(
        "PLAN_RESPONSE_SCHEMA = ")[1].split("\n\n\n")[0], re.I))

    # A guardrail that exists but is never reached at runtime is not a guardrail.
    # Count call sites, not the definition: a line matching "def validate_..." is
    # where the guardrail is written, not where it runs.
    validator_calls: dict[str, int] = {}
    for path in (list((ENGINE_DIR / "protocol_engine").glob("*.py"))
                 + list((ENGINE_DIR / "app").glob("*.py"))
                 + list((ENGINE_DIR / "tests").glob("*.py"))):
        hits = [
            line for line in path.read_text().splitlines()
            if "validate_generated_markdown(" in line and not line.lstrip().startswith("def ")
        ]
        if hits:
            validator_calls[path.name] = len(hits)
    runtime_callers = {n: c for n, c in validator_calls.items() if not n.startswith("test_")}

    # Do the two appendix constructions agree? The Markdown renderer merges corpus
    # findings with each exercise's reference_evidence; check whether the API mapper does.
    mapper_source = MAPPERS.read_text()
    appendix_aligned = "reference_evidence" in mapper_source.split(
        "appendix: list[dict[str, Any]] = []", 1)[-1].split("return {", 1)[0]

    return [
        {
            "claim": "no exercise can look highly-evidenced without actual evidence",
            "published": "confidence hard-capped at c <= 0.72, below the 0.75 'high' threshold",
            "measured": "max confidence among %d zero-evidence exercises = %.4f; labels: %s"
                        % (len(zero_evidence), worst, dict(labels_at_zero)),
            "conforms": worst <= 0.72 and "high" not in labels_at_zero,
            "source": "science/page.tsx:326-331",
            "note": "Holds with margin. The residual question is calibration of the "
                    "'moderate' label, not conformance of this guardrail.",
        },
        {
            "claim": "the model is mathematically unable to cite an exercise (or study) "
                     "that isn't in its brief",
            "published": "enum-locked response schema",
            "measured": "exercise ids are enum-locked only when supports_structured_output(model) "
                        "is true (gemma fallbacks receive no schema); the plan schema has no "
                        "study field at all (%s), so citations are never model-emitted"
                        % ("study field present" if schema_has_study_field else "no study field"),
            "conforms": None,
            "source": "science/page.tsx:429-433",
            "note": "The outcome is guaranteed - Python attaches every citation after "
                    "validation - but not by the mechanism the claim names. For studies the "
                    "claim is vacuously true rather than enforced. schema_is_conditional=%s"
                    % schema_is_conditional,
        },
        {
            "claim": "every cited PMID is checked to be in the allowed set and in the appendix",
            "published": "validate_generated_markdown guardrail",
            "measured": "call sites: %s; runtime (non-test) call sites: %s"
                        % (validator_calls, runtime_callers or "none"),
            "conforms": bool(runtime_callers),
            "source": "protocol_demo.py:2824-2919",
            "note": "The validator is exercised by the test suite only, so the containment "
                    "property is tested but not enforced on a live generation.",
        },
        {
            "claim": "the evidence appendix lists the studies behind the protocol",
            "published": "one appendix",
            "measured": "the Markdown renderer and the API mapper %s: both merge corpus "
                        "findings with each exercise's reference_evidence"
                        % ("agree" if appendix_aligned else "disagree"),
            "conforms": appendix_aligned,
            "source": "protocol_demo.py render_protocol_markdown vs app/mappers.py",
            "note": "When they disagree the web UI's study count omits PMIDs it displays "
                    "on its own exercise rows, while the Markdown export includes them.",
        },
    ]


def pearson(xs: list[float], ys: list[float]) -> float:
    """Pearson r. statistics.correlation is 3.10+ and this engine runs on 3.9."""
    mx, my = mean(xs), mean(ys)
    numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denominator = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return numerator / denominator if denominator else float("nan")


def confidence_calibration(catalog: dict) -> dict[str, Any]:
    """How well does the displayed confidence label predict actual evidence?

    The guardrail above stops zero-evidence exercises from being labelled "high".
    The question that remains is what "moderate" tells a reader, so we report the
    label's precision: given a label, how often is there any direct evidence?
    """
    exercises = catalog["exercises"]
    counts = collections.Counter(
        (e["evidence"]["confidence_level"], e["evidence"].get("direct_evidence_count", 0) > 0)
        for e in exercises
    )
    label_precision = {}
    for level in ("high", "moderate", "low"):
        with_evidence = counts[(level, True)]
        total = with_evidence + counts[(level, False)]
        label_precision[level] = {
            "n": total,
            "n_with_direct_evidence": with_evidence,
            "p_has_evidence_given_label": with_evidence / total if total else float("nan"),
        }

    zero = [e["evidence"]["confidence_score"] for e in exercises
            if e["evidence"].get("direct_evidence_count", 0) == 0]
    some = [e["evidence"]["confidence_score"] for e in exercises
            if e["evidence"].get("direct_evidence_count", 0) > 0]
    counts_x = [e["evidence"].get("direct_evidence_count", 0) for e in exercises]
    scores_y = [e["evidence"]["confidence_score"] for e in exercises]
    return {
        "label_precision": label_precision,
        "zero_evidence_score": {"n": len(zero), "min": min(zero), "max": max(zero),
                                "mean": mean(zero)},
        "has_evidence_score": {"n": len(some), "min": min(some), "max": max(some),
                               "mean": mean(some)},
        "pearson_r_count_vs_score": pearson(counts_x, scores_y),
        "score_floor_note": "The heuristic path starts at 0.42 and is capped at 0.72 "
                            "(build_exercise_catalog.py:845-862), so the score has a floor: "
                            "it ranks correctly but never reports the absence of evidence.",
    }


def dosage_provenance() -> dict[str, Any]:
    """Is the prescription (sets/reps/rest) derived from any study, or is it a constant?

    Demonstrated rather than asserted: call the engine's own seed function with
    deliberately dissimilar exercises and compare the output.
    """
    from protocol_engine.protocol_demo import PRESCRIPTION_BOUNDS, build_prescription_seed

    catalog = load_catalog()["exercises"]
    probes = [catalog[0], catalog[len(catalog) // 2], catalog[-1]]
    seeds = {
        goal: [build_prescription_seed(exercise, goal) for exercise in probes]
        for goal in ("hypertrophy", "strength")
    }
    identical = {goal: all(s == values[0] for s in values) for goal, values in seeds.items()}
    return {
        "probe_exercises": [e["name"] for e in probes],
        "seeds_by_goal": {goal: values[0] for goal, values in seeds.items()},
        "identical_across_dissimilar_exercises": identical,
        "prescription_bounds": {k: dict(v) if isinstance(v, dict) else v
                                for k, v in PRESCRIPTION_BOUNDS.items()},
        "note": "build_prescription_seed depends only on the goal, so every dosage a user "
                "reads originates from the planner model's parametric knowledge or from "
                "these two constants, clamped to author-chosen bounds. Citations attached "
                "to a recommendation support the exercise choice, never the dosage.",
    }


def main() -> None:
    catalog, corpus = load_catalog(), load_corpus()
    banner("S4 - conformance to the system's own published methodology")

    claims = numeric_claims(catalog, corpus) + guardrail_claims(catalog)
    print("%-58s %-10s %-10s %s" % ("claim", "published", "measured", "verdict"))
    for item in claims:
        verdict = {True: "conforms", False: "DIVERGES", None: "qualified"}[item["conforms"]]
        published = str(item["published"])[:10]
        measured = str(item["measured"])[:10]
        print("%-58s %-10s %-10s %s" % (item["claim"][:58], published, measured, verdict))

    calibration = confidence_calibration(catalog)
    print("\nconfidence label precision - given the label, is there any direct evidence?")
    for level, row in calibration["label_precision"].items():
        print("   %-9s n=%-5d with evidence=%-5d P(evidence | label) = %5.1f%%" % (
            level, row["n"], row["n_with_direct_evidence"],
            100 * row["p_has_evidence_given_label"]))
    print("   zero-evidence scores span %.2f-%.2f (mean %.2f); r(count, score) = %.3f" % (
        calibration["zero_evidence_score"]["min"], calibration["zero_evidence_score"]["max"],
        calibration["zero_evidence_score"]["mean"], calibration["pearson_r_count_vs_score"]))

    dosage = dosage_provenance()
    print("\ndosage provenance: identical seeds across dissimilar exercises? %s" %
          dosage["identical_across_dissimilar_exercises"])
    print("   probes: %s" % ", ".join(dosage["probe_exercises"]))
    print("   seeds : %s" % dosage["seeds_by_goal"])

    write_csv(
        "s4_conformance",
        ["claim", "published", "measured", "verdict", "source"],
        [[c["claim"], c["published"], c["measured"],
          {True: "conforms", False: "diverges", None: "qualified"}[c["conforms"]], c["source"]]
         for c in claims],
    )
    path = write_results("s4_conformance", {
        "environment": environment_snapshot(),
        "claims": claims,
        "n_conforming": sum(1 for c in claims if c["conforms"] is True),
        "n_diverging": sum(1 for c in claims if c["conforms"] is False),
        "n_qualified": sum(1 for c in claims if c["conforms"] is None),
        "confidence_calibration": calibration,
        "dosage_provenance": dosage,
    })
    print("\nwrote %s" % path)


if __name__ == "__main__":
    main()
