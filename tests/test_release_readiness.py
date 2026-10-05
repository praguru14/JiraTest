import tempfile
import unittest
from pathlib import Path

from release_readiness import ReleaseEvidence, ReleaseReadinessEngine


class ReleaseReadinessTests(unittest.TestCase):
    def test_critical_bug_produces_no_go(self):
        evidence = ReleaseEvidence(release="Sprint 24", critical_open_bugs=1)

        result = ReleaseReadinessEngine().assess(evidence, use_ai=False)

        self.assertEqual(result.decision, "NO-GO")
        self.assertTrue(result.blockers)

    def test_missing_approval_produces_needs_approval(self):
        evidence = ReleaseEvidence(
            release="Sprint 24",
            missing_approvals=("Product owner",),
        )

        result = ReleaseReadinessEngine().assess(evidence, use_ai=False)

        self.assertEqual(result.decision, "NEEDS-APPROVAL")
        self.assertIn("Product owner", result.warnings[0])

    def test_clean_evidence_produces_go_and_html(self):
        evidence = ReleaseEvidence(
            release="Sprint 24",
            test_coverage=91.0,
        )
        engine = ReleaseReadinessEngine()
        result = engine.assess(evidence, use_ai=False)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "readiness.html"
            engine.write_html(result, output)
            body = output.read_text(encoding="utf-8")

        self.assertEqual(result.decision, "GO")
        self.assertIn("Sprint 24", body)
        self.assertIn("GO", body)


if __name__ == "__main__":
    unittest.main()
