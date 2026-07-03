"""API-layer tests over the real committed catalog.

``TestClient(app)`` is used WITHOUT the context manager so the lifespan warmup
(Chroma + embedding model load) never runs — the endpoints under test only need
the lazily-loaded catalog JSON."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import data
from app.main import app

client = TestClient(app)


def catalog_muscle_counts(muscle: str) -> tuple[int, int]:
    """(primary count, merged primary+secondary count) straight from the catalog."""
    primary = 0
    merged = 0
    for ex in data.exercises():
        muscles = ex.get("muscles", {}) or {}
        if muscle in muscles.get("primary", []):
            primary += 1
        if muscle in muscles.get("primary", []) or muscle in muscles.get("secondary", []):
            merged += 1
    return primary, merged


class MuscleFilterTests(unittest.TestCase):
    def test_muscle_filter_matches_primary_only(self):
        primary_count, merged_count = catalog_muscle_counts("mid_back")
        # The dataset genuinely has secondary-only mid_back exercises (shoulder
        # presses etc.); if this ever fails the fixture assumption changed.
        self.assertGreater(merged_count, primary_count)

        resp = client.get("/api/exercises", params={"muscle": "mid_back", "page_size": 100})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["total"], primary_count)
        for item in body["items"]:
            self.assertIn("mid_back", item["primaryMuscles"], item["name"])

    def test_muscle_filter_excludes_secondary_only_shoulder_moves(self):
        resp = client.get("/api/exercises", params={"muscle": "mid_back", "page_size": 100})
        names = [item["name"].lower() for item in resp.json()["items"]]
        for phrase in ("shoulder press", "lateral raise", "overhead press"):
            offenders = [n for n in names if phrase in n]
            self.assertEqual(offenders, [], f"'{phrase}' exercises leaked into mid_back")

    def test_muscle_filter_secondary_only_exercise_absent(self):
        # Find a concrete secondary-only case and assert the filter drops it.
        sample = next(
            ex
            for ex in data.exercises()
            if "mid_back" in (ex.get("muscles", {}) or {}).get("secondary", [])
            and "mid_back" not in (ex.get("muscles", {}) or {}).get("primary", [])
        )
        resp = client.get("/api/exercises", params={"muscle": "mid_back", "page_size": 100})
        ids = {item["exerciseId"] for item in resp.json()["items"]}
        self.assertNotIn(sample["exercise_id"], ids)


class TaxonomyTests(unittest.TestCase):
    def test_taxonomy_muscles_all_have_primary_exercises(self):
        resp = client.get("/api/taxonomies")
        self.assertEqual(resp.status_code, 200)
        muscle_groups = resp.json()["muscleGroups"]
        self.assertNotIn("neck", muscle_groups)
        self.assertIn("mid_back", muscle_groups)
        for muscle in muscle_groups:
            listing = client.get("/api/exercises", params={"muscle": muscle, "page_size": 1})
            self.assertGreaterEqual(
                listing.json()["total"], 1, f"taxonomy muscle '{muscle}' has no exercises"
            )


class ErrorHandlingTests(unittest.TestCase):
    def test_generate_endpoint_sanitizes_unexpected_errors(self):
        with patch("app.main.generate_protocol", side_effect=RuntimeError("secret internals")):
            resp = client.post(
                "/api/protocol/generate",
                json={"goal": "hypertrophy", "muscles": ["biceps"], "equipment": ["dumbbell"]},
            )
        self.assertEqual(resp.status_code, 502)
        self.assertNotIn("secret internals", resp.json()["detail"])


if __name__ == "__main__":
    unittest.main()
