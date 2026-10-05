from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ReleaseEvidence:
    release: str
    critical_open_bugs: int = 0
    ci_failures: tuple[str, ...] = ()
    security_findings: tuple[str, ...] = ()
    missing_approvals: tuple[str, ...] = ()
    test_coverage: float | None = None
    changed_services: tuple[str, ...] = ()
    recent_incidents: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        return cls(
            release=str(data.get("release", "Unnamed release")),
            critical_open_bugs=int(data.get("critical_open_bugs", 0)),
            ci_failures=tuple(data.get("ci_failures", ())),
            security_findings=tuple(data.get("security_findings", ())),
            missing_approvals=tuple(data.get("missing_approvals", ())),
            test_coverage=data.get("test_coverage"),
            changed_services=tuple(data.get("changed_services", ())),
            recent_incidents=tuple(data.get("recent_incidents", ())),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class ReadinessResult:
    release: str
    decision: str
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    ai_summary: str = ""
    evidence: ReleaseEvidence | None = None
