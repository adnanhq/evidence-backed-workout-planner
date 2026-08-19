"""S3e - do the model's judgments agree with a person's?

An LLM adjudicator is only usable evidence if its agreement with a human rater is
measured rather than assumed. This reads the annotations exported by the local
task page and reports raw agreement and Cohen's kappa per question, plus the
human-only support rates so the paper can quote figures that rest on no model at
all. It also reports whether the model is systematically more lenient, which is
the failure mode that would matter here.

Run after completing research/annotate/index.html:
    ./.venv/bin/python -m research.s3e_agreement
"""
from __future__ import annotations

import json
from typing import Any

from research.common import ANNOTATE_DIR, banner, environment_snapshot, mean, read_results, write_results

CITATION_QUESTIONS = ["movement_involved", "goal_supported", "variant_exact"]


def kappa(a: list[str], b: list[str]) -> float:
    from sklearn.metrics import cohen_kappa_score

    if len(set(a)) < 2 and len(set(b)) < 2 and a == b:
        return 1.0  # both raters constant and identical; kappa is undefined, agreement perfect
    return float(cohen_kappa_score(a, b))


def main() -> None:
    path = ANNOTATE_DIR / "human_annotations.json"
    banner("S3e - human vs model agreement")
    if not path.exists():
        print("No human annotations yet.")
        print("  1. open %s" % (ANNOTATE_DIR / "index.html"))
        print("  2. work through the 39 items")
        print("  3. click 'Export answers' and save it as %s" % path)
        print("  4. re-run this module")
        return

    human = json.loads(path.read_text())
    model = {v["pair_id"]: v for v in read_results("s3c_judgments")["verdicts"] if "error" not in v}
    items = {i["id"]: i for i in read_results("s3d_annotation_items")["items"]}

    per_question: dict[str, Any] = {}
    for question in CITATION_QUESTIONS:
        pairs = [
            (human[item_id][question], model[item_id][question])
            for item_id in sorted(human)
            if items.get(item_id, {}).get("kind") == "citation"
            and question in human.get(item_id, {}) and item_id in model
        ]
        if not pairs:
            continue
        human_yes = mean([h == "yes" for h, _ in pairs])
        model_yes = mean([m == "yes" for _, m in pairs])
        per_question[question] = {
            "n": len(pairs),
            "raw_agreement": mean([h == m for h, m in pairs]),
            "cohen_kappa": kappa([h for h, _ in pairs], [m for _, m in pairs]),
            "human_yes_rate": human_yes,
            "model_yes_rate": model_yes,
            "model_leniency": model_yes - human_yes,
        }

    tier = [
        (item_id, human[item_id]["promotion_justified"])
        for item_id in sorted(human)
        if items.get(item_id, {}).get("kind") == "tier"
        and "promotion_justified" in human.get(item_id, {})
    ]
    tier_block = {
        "n": len(tier),
        "promotions_judged_justified": sum(1 for _, v in tier if v == "yes"),
        "justified_rate": mean([v == "yes" for _, v in tier]) if tier else float("nan"),
    }

    print("citation support - human vs model (n per question)")
    print("%-22s %5s %11s %9s %11s %11s" % (
        "question", "n", "agreement", "kappa", "human yes", "model yes"))
    for question, row in per_question.items():
        print("%-22s %5d %10.1f%% %9.3f %10.1f%% %10.1f%%" % (
            question, row["n"], 100 * row["raw_agreement"], row["cohen_kappa"],
            100 * row["human_yes_rate"], 100 * row["model_yes_rate"]))

    if tier:
        print("\ntier promotions judged justified by a human: %d / %d (%.0f%%)" % (
            tier_block["promotions_judged_justified"], tier_block["n"],
            100 * tier_block["justified_rate"]))
        print("  the complement is heuristic error; the rest is incomplete MEDLINE indexing")

    write_results("s3e_agreement", {
        "environment": environment_snapshot(),
        "citation_questions": per_question,
        "tier_promotions": tier_block,
        "note": "Human labels are the reference. model_leniency > 0 means the model "
                "credits support more often than the person did.",
    })
    print("\nwrote results/s3e_agreement.json")


if __name__ == "__main__":
    main()
