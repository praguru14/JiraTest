import html
import json
from pathlib import Path

from models.llm_adapter import LLMAdapter
from release_readiness.models import ReadinessResult, ReleaseEvidence


class ReleaseReadinessEngine:
    """Combines deterministic release gates with optional AI explanation."""

    def __init__(self, llm=None):
        self.llm = llm

    def assess(self, evidence: ReleaseEvidence, use_ai=True) -> ReadinessResult:
        blockers = []
        warnings = []
        recommendations = []

        if evidence.critical_open_bugs > 0:
            blockers.append(
                f"{evidence.critical_open_bugs} critical bug(s) remain open"
            )
            recommendations.append("Resolve or formally accept all critical bugs.")

        if evidence.ci_failures:
            blockers.append("CI failures: " + ", ".join(evidence.ci_failures))
            recommendations.append("Fix failing pipelines and rerun the release checks.")

        if evidence.security_findings:
            blockers.append(
                "Security findings: " + ", ".join(evidence.security_findings)
            )
            recommendations.append("Remediate or formally waive security findings.")

        if evidence.missing_approvals:
            warnings.append(
                "Missing approvals: " + ", ".join(evidence.missing_approvals)
            )
            recommendations.append("Obtain the missing release approvals.")

        if evidence.test_coverage is not None and evidence.test_coverage < 80:
            warnings.append(f"Test coverage is below target: {evidence.test_coverage:.1f}%")
            recommendations.append("Add tests or document the coverage exception.")

        if blockers:
            decision = "NO-GO"
        elif evidence.missing_approvals:
            decision = "NEEDS-APPROVAL"
        else:
            decision = "GO"

        ai_summary = ""
        if use_ai:
            ai_summary = self._explain(
                evidence,
                decision,
                tuple(blockers),
                tuple(warnings),
                tuple(recommendations),
            )

        return ReadinessResult(
            release=evidence.release,
            decision=decision,
            blockers=tuple(blockers),
            warnings=tuple(warnings),
            recommendations=tuple(dict.fromkeys(recommendations)),
            ai_summary=ai_summary,
            evidence=evidence,
        )

    def write_html(self, result: ReadinessResult, output_path):
        body = self._html(result)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    def _explain(self, evidence, decision, blockers, warnings, recommendations):
        llm = self.llm or LLMAdapter()
        prompt = (
            "You are a release readiness advisor. Explain the deterministic decision "
            "briefly and give practical recommendations. Do not override blockers. "
            "Return plain text, not JSON or markdown.\n\n"
            f"Evidence:\n{json.dumps(evidence.__dict__, indent=2)}\n\n"
            f"Decision: {decision}\n"
            f"Blockers: {json.dumps(blockers)}\n"
            f"Warnings: {json.dumps(warnings)}\n"
            f"Recommendations: {json.dumps(recommendations)}"
        )
        return llm.generate(
            "You explain release risk using only the supplied evidence.",
            prompt,
            max_tokens=300,
        ).strip()

    @staticmethod
    def _html(result):
        esc = html.escape
        section = lambda title, values: (
            f"<h2>{esc(title)}</h2><ul>" + "".join(
                f"<li>{esc(value)}</li>" for value in values
            ) + "</ul>"
            if values else ""
        )
        color = {"GO": "#176b3a", "NO-GO": "#a51d2d", "NEEDS-APPROVAL": "#9a6700"}[result.decision]
        return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{esc(result.release)} readiness</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;max-width:900px;margin:40px auto;padding:0 24px;color:#263238}}h1{{margin-bottom:4px}}.decision{{color:{color};font-size:28px;font-weight:700;margin:20px 0}}li{{margin:8px 0}}</style>
</head><body><h1>{esc(result.release)}</h1><div class="decision">{esc(result.decision)}</div>
{section("Blockers", result.blockers)}{section("Warnings", result.warnings)}{section("Recommendations", result.recommendations)}
{f'<h2>AI summary</h2><p>{esc(result.ai_summary)}</p>' if result.ai_summary else ''}
</body></html>"""
