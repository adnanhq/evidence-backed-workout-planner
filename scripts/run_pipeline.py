from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the full fitness data pipeline (science corpus + enriched exercise catalog)."
    )
    parser.add_argument(
        "--email",
        default=None,
        help="Entrez email. Required unless --skip-science is set.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Optional NCBI API key for higher PubMed rate limits.",
    )
    parser.add_argument(
        "--query-config",
        default="config/pubmed_queries.json",
        help="Path to PubMed topic cluster config JSON.",
    )
    parser.add_argument(
        "--exercise-input",
        default="data/raw/free-exercise-db/dist/exercises.json",
        help="Raw free-exercise-db input JSON path.",
    )
    parser.add_argument(
        "--science-output",
        default="data/processed/science_corpus.json",
        help="Science corpus output JSON path.",
    )
    parser.add_argument(
        "--science-review-output",
        default="data/processed/science_manual_review_queue.json",
        help="Manual review output for science corpus.",
    )
    parser.add_argument(
        "--exercise-output",
        default="data/processed/exercise_catalog_enriched.json",
        help="Enriched exercise output JSON path.",
    )
    parser.add_argument(
        "--exercise-review-output",
        default="data/processed/exercise_manual_review_queue.json",
        help="Manual review output for exercise catalog.",
    )
    parser.add_argument(
        "--retmax-per-query",
        type=int,
        default=None,
        help="Optional override for top N PubMed records per query (defaults to query config).",
    )
    parser.add_argument(
        "--from-year",
        type=int,
        default=2018,
        help="Minimum publication year for science corpus inclusion.",
    )
    parser.add_argument(
        "--skip-science",
        action="store_true",
        help="Skip science corpus rebuild and only generate exercise catalog.",
    )
    return parser.parse_args()


def run_command(command: list[str]) -> None:
    printable = " ".join(command)
    print(f"[run] {printable}", flush=True)
    subprocess.run(command, check=True)


def main() -> None:
    args = parse_args()
    scripts_dir = Path(__file__).resolve().parent
    science_script = str((scripts_dir / "build_science_corpus.py").resolve())
    exercise_script = str((scripts_dir / "build_exercise_catalog.py").resolve())

    if not args.skip_science:
        if not args.email:
            raise SystemExit("`--email` is required when running science corpus ingestion.")
        science_cmd = [
            sys.executable,
            science_script,
            "--email",
            args.email,
            "--query-config",
            args.query_config,
            "--from-year",
            str(args.from_year),
            "--output",
            args.science_output,
            "--manual-review-output",
            args.science_review_output,
        ]
        if args.retmax_per_query is not None:
            science_cmd.extend(["--retmax-per-query", str(args.retmax_per_query)])
        if args.api_key:
            science_cmd.extend(["--api-key", args.api_key])
        run_command(science_cmd)

    exercise_cmd = [
        sys.executable,
        exercise_script,
        "--input",
        args.exercise_input,
        "--science-corpus",
        args.science_output,
        "--output",
        args.exercise_output,
        "--manual-review-output",
        args.exercise_review_output,
    ]
    run_command(exercise_cmd)
    print("[done] Pipeline complete.", flush=True)


if __name__ == "__main__":
    main()
