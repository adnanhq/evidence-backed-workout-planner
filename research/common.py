"""Shared plumbing for the stage-wise audit.

Every study module imports from here so that paths, seeds, and the results
format are identical across studies. Nothing in this package writes outside
``research/`` — the audit measures the committed capstone artefacts in place.
"""
from __future__ import annotations

import json
import platform
import random
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = REPO_ROOT / "services" / "engine"
RESEARCH_DIR = REPO_ROOT / "research"
RESULTS_DIR = RESEARCH_DIR / "results"
FIGURES_DIR = RESEARCH_DIR / "figures"
ANNOTATE_DIR = RESEARCH_DIR / "annotate"

# The engine is not an installed package; put its root on the path so that
# ``protocol_engine.*`` resolves and we audit the real code rather than a copy.
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

# One seed for every sampling decision in the paper. Changing this changes which
# items were annotated, so it is pinned and reported.
SEED = 20260818

for _directory in (RESULTS_DIR, FIGURES_DIR, ANNOTATE_DIR):
    _directory.mkdir(parents=True, exist_ok=True)


# --- Engine artefacts ----------------------------------------------------------------

def load_corpus() -> dict[str, Any]:
    """The committed science corpus: metadata / documents / chunks / pmid_to_doc_id."""
    from protocol_engine import settings

    with open(settings.SCIENCE_PATH) as handle:
        return json.load(handle)


def load_catalog() -> dict[str, Any]:
    """The committed enriched exercise catalog: metadata / taxonomies / exercises."""
    from protocol_engine import settings

    with open(settings.CATALOG_PATH) as handle:
        return json.load(handle)


def load_query_config() -> dict[str, Any]:
    """The two PubMed query configs merged the way ``build_science_corpus`` merges them.

    Clusters are keyed by id; the generated config's clusters are appended, and a
    duplicate id would be a build-time collision so we surface it rather than
    silently overwrite.
    """
    from protocol_engine import settings

    clusters: dict[str, dict[str, Any]] = {}
    for name in ("pubmed_queries.json", "pubmed_queries_generated.json"):
        with open(settings.CONFIG_DIR / name) as handle:
            payload = json.load(handle)
        for cluster in payload.get("clusters", []):
            cluster_id = cluster["id"]
            if cluster_id in clusters:
                raise ValueError("duplicate cluster id across query configs: %s" % cluster_id)
            clusters[cluster_id] = {**cluster, "config": name}
    return clusters


# --- Results -------------------------------------------------------------------------

def write_results(name: str, payload: dict[str, Any]) -> Path:
    """Write ``results/<name>.json`` deterministically (sorted keys, fixed indent)."""
    path = RESULTS_DIR / ("%s.json" % name)
    with open(path, "w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def read_results(name: str) -> dict[str, Any]:
    with open(RESULTS_DIR / ("%s.json" % name)) as handle:
        return json.load(handle)


def write_csv(name: str, header: Sequence[str], rows: Sequence[Sequence[Any]]) -> Path:
    import csv

    path = RESULTS_DIR / ("%s.csv" % name)
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return path


# --- Statistics ----------------------------------------------------------------------

def bootstrap_ci(
    values: Sequence[float],
    statistic: Callable[[Sequence[float]], float] = None,
    resamples: int = 10_000,
    confidence: float = 0.95,
    seed: int = SEED,
) -> tuple[float, float]:
    """Percentile bootstrap CI over ``values``, resampling the unit of analysis.

    The unit of analysis in this paper is the *query*, so ``values`` is one number
    per query and this resamples queries with replacement.
    """
    if statistic is None:
        statistic = lambda sample: sum(sample) / len(sample)  # noqa: E731
    if not values:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    size = len(values)
    draws = []
    for _ in range(resamples):
        sample = [values[rng.randrange(size)] for _ in range(size)]
        draws.append(statistic(sample))
    draws.sort()
    tail = (1.0 - confidence) / 2.0
    lower = draws[int(tail * resamples)]
    upper = draws[min(resamples - 1, int((1.0 - tail) * resamples))]
    return (lower, upper)


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


# --- Provenance ----------------------------------------------------------------------

def environment_snapshot() -> dict[str, Any]:
    """Versions that affect reproducibility, recorded alongside every result set."""
    versions: dict[str, str] = {}
    for module_name in (
        "numpy", "scipy", "sklearn", "torch", "sentence_transformers",
        "transformers", "chromadb", "matplotlib",
    ):
        try:
            module = __import__(module_name)
            versions[module_name] = getattr(module, "__version__", "unknown")
        except ImportError:
            versions[module_name] = "not installed"
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "seed": SEED,
        "packages": versions,
    }


def banner(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)
