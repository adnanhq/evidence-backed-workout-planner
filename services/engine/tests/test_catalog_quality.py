"""Independent "does the catalog recommend what we'd expect?" checks.

These expectations are deliberately NOT inputs to the ranking pipeline. They run
against the committed, regenerated catalog and assert that sensible, evidence-backed
exercises surface organically for each muscle — the verification that the rankings
are honest rather than forced. If a future change to the scoring/evidence logic
breaks one of these, the recommendation quality has regressed.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from protocol_engine import settings


def load_catalog() -> dict:
    return json.loads(Path(settings.CATALOG_PATH).read_text(encoding="utf-8"))


def top_names(exercises: list[dict], muscle: str, goal: str, n: int) -> list[str]:
    ranked = []
    for exercise in exercises:
        info = exercise.get("muscle_group_rankings", {}).get(goal, {}).get(muscle)
        if info:
            ranked.append((info["rank"], exercise["name"]))
    ranked.sort()
    return [name for _, name in ranked[:n]]


class CatalogQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog()
        cls.exercises = cls.catalog["exercises"]

    def top(self, muscle: str, n: int = 5, goal: str = "hypertrophy") -> list[str]:
        return top_names(self.exercises, muscle, goal, n)

    def test_quads_top_are_quad_movements_without_hip_leakage(self) -> None:
        top = self.top("quads", 8)
        self.assertTrue(top)
        leak_terms = ("hip flex", "adduction", "adductor", "abduction", "abductor", "stretch")
        for name in top:
            lowered = name.lower()
            self.assertFalse(
                any(term in lowered for term in leak_terms),
                f"hip/stretch leakage in quad rankings: {name}",
            )
        quad_terms = ("squat", "leg press", "leg extension", "hack", "lunge", "split squat", "step")
        for name in top[:5]:
            self.assertTrue(
                any(term in name.lower() for term in quad_terms),
                f"unexpected non-quad movement in quad top-5: {name}",
            )

    def test_chest_top_are_press_or_fly_movements(self) -> None:
        chest_terms = ("press", "bench", "fly", "flye", "dip", "push", "pec")
        for name in self.top("chest", 5):
            self.assertTrue(
                any(term in name.lower() for term in chest_terms),
                f"unexpected chest top: {name}",
            )

    def test_biceps_top_are_curls(self) -> None:
        for name in self.top("biceps", 5):
            self.assertIn("curl", name.lower(), f"unexpected biceps top: {name}")

    def test_triceps_surfaces_overhead_extension_and_not_a_press(self) -> None:
        top = self.top("triceps", 5)
        self.assertTrue(top)
        # The curated lengthened-position evidence should organically surface overhead work.
        self.assertTrue(
            any("overhead" in name.lower() for name in top),
            f"expected an overhead triceps extension in top-5: {top}",
        )
        # A compound bench press should not be the #1 *triceps* hypertrophy pick.
        self.assertNotIn("bench press", top[0].lower())

    def test_ties_are_flagged_not_faked(self) -> None:
        # Every ranking entry carries tie_size, and the known multi-way bench tie is honest.
        for exercise in self.exercises:
            for goal_ranks in exercise.get("muscle_group_rankings", {}).values():
                for info in goal_ranks.values():
                    self.assertIn("tie_size", info)
        chest_entries = [
            exercise.get("muscle_group_rankings", {}).get("hypertrophy", {}).get("chest")
            for exercise in self.exercises
        ]
        chest_rank_one = next(info for info in chest_entries if info and info["rank"] == 1)
        self.assertGreater(chest_rank_one["tie_size"], 1)


if __name__ == "__main__":
    unittest.main()
