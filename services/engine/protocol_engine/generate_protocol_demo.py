from __future__ import annotations

import argparse
import sys

try:
    from .protocol_demo import (
        DEFAULT_MODEL,
        DemoConfigurationError,
        DemoRequestError,
        display_muscle_label,
        normalize_request,
        run_protocol_demo,
        run_protocol_dry_run,
    )
except ImportError:  # pragma: no cover
    from protocol_demo import (
        DEFAULT_MODEL,
        DemoConfigurationError,
        DemoRequestError,
        display_muscle_label,
        normalize_request,
        run_protocol_demo,
        run_protocol_dry_run,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a 1-week science-backed demo protocol from the existing catalog, "
            "science corpus, and an LLM-planned weekly split."
        )
    )
    parser.add_argument(
        "--goal",
        default="hypertrophy",
        help="Training goal. Supported values: hypertrophy, strength.",
    )
    parser.add_argument(
        "--muscles",
        required=True,
        help="Comma-separated target muscles, for example: biceps or quads,glutes",
    )
    parser.add_argument(
        "--sessions",
        type=int,
        default=2,
        help="Number of sessions in the 1-week demo protocol.",
    )
    parser.add_argument(
        "--session-minutes",
        type=int,
        default=45,
        help="Approximate minutes available per session.",
    )
    parser.add_argument(
        "--exercises-per-session",
        type=int,
        default=None,
        help="Optional exact exercise count per session. Overrides the session-minutes default.",
    )
    parser.add_argument(
        "--equipment",
        default="",
        help="Optional comma-separated equipment filter, for example: gym or dumbbell,cable",
    )
    parser.add_argument(
        "--experience",
        default="intermediate",
        help="Training experience level: beginner, intermediate, or advanced.",
    )
    parser.add_argument(
        "--avoid-joints",
        default="",
        help="Optional comma-separated joints to avoid high stress on, for example: knee,shoulder",
    )
    parser.add_argument(
        "--notes",
        default="",
        help="Optional free-text notes to inject into retrieval and prompting.",
    )
    parser.add_argument(
        "--split-template",
        default="auto",
        help="Workout split guideline: auto, full_body, push_pull, push_pull_legs, or upper_lower.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Gemma model name. Defaults to {DEFAULT_MODEL}.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Optional Gemini API key. If omitted, GEMINI_API_KEY is used.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Preview the shortlisted candidates and the deterministic protocol without "
            "calling the LLM (no API key or vector store required)."
        ),
    )
    return parser.parse_args()


def print_dry_run(result: dict) -> None:
    request = result["request"]
    pool = result["candidate_pool"]

    print(f"=== Dry run: {request.goal} / {', '.join(request.muscles)} · {request.sessions} session(s) ===")
    print(
        "Request: "
        + " | ".join(
            [
                f"equipment={','.join(request.equipment) if request.equipment else 'any'}",
                f"experience={request.experience}",
                f"split={request.split_template}",
                f"avoid_joints={','.join(request.avoid_joints) if request.avoid_joints else 'none'}",
            ]
        )
    )
    print(f"\nShortlisted candidates the planner chooses from ({result['filtered_candidate_count']} passed filters):\n")
    for muscle in request.muscles:
        items = pool.get("by_target", {}).get(muscle, [])
        print(f"  {display_muscle_label(muscle)} — {len(items)} shortlisted")
        if not items:
            print("    (none matched the equipment / joint / difficulty filters)")
        for item in items:
            rank = item.get("rank_display") or "unranked"
            studies = ", ".join(str(s.get("pmid")) for s in item.get("top_studies", []) if s.get("pmid"))
            detail = f"{rank} · score={item.get('final_score', 0):.3f} · ev={item.get('direct_evidence_count', 0)}"
            if studies:
                detail += f" · PMID {studies}"
            print(f"    • {item['name']}  [{item.get('equipment', '?')}]")
            print(f"        {detail}")
        print()

    print("Deterministic protocol (no LLM — the engine's fallback placement):\n")
    protocol = result["markdown_text"].split("## Evidence Appendix", 1)[0].strip()
    body = protocol.split("## 1-Week Protocol", 1)
    print(body[1].strip() if len(body) > 1 else protocol)

    print("\nNotes:")
    # The "no semantic findings" warning is expected here — dry run skips vector
    # retrieval by design — so replace it with a clear statement instead.
    for warning in result.get("warnings", []):
        if "vector store" not in warning:
            print(f"  - {warning}")
    print("  - Dry run skips semantic vector-store retrieval; direct exercise-study PMIDs are")
    print("    shown above. Run without --dry-run for the full LLM-planned, fully-cited protocol.")


def main() -> int:
    args = parse_args()
    try:
        request = normalize_request(
            goal=args.goal,
            muscles=args.muscles,
            sessions=args.sessions,
            session_minutes=args.session_minutes,
            exercises_per_session=args.exercises_per_session,
            equipment=args.equipment,
            experience=args.experience,
            avoid_joints=args.avoid_joints,
            notes=args.notes,
            split_template=args.split_template,
        )
        if args.dry_run:
            print_dry_run(run_protocol_dry_run(request))
            return 0
        result = run_protocol_demo(request=request, model=args.model, api_key=args.api_key)
    except (DemoRequestError, DemoConfigurationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(result["markdown_text"], end="")
    print(
        f"\nSaved Markdown to {result['output_paths']['markdown_path']}\n"
        f"Saved debug JSON to {result['output_paths']['debug_path']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
