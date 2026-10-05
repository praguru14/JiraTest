import argparse
import json
import sys

from release_readiness import ReleaseEvidence, ReleaseReadinessEngine


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate release readiness from an evidence JSON file."
    )
    parser.add_argument("evidence", help="Path to release evidence JSON")
    parser.add_argument("--output", default="output/release_readiness.html")
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Use deterministic checks only; do not call an LLM",
    )
    args = parser.parse_args()

    with open(args.evidence, encoding="utf-8") as stream:
        evidence = ReleaseEvidence.from_dict(json.load(stream))

    engine = ReleaseReadinessEngine()
    result = engine.assess(evidence, use_ai=not args.no_ai)
    engine.write_html(result, args.output)

    print(f"Decision: {result.decision}")
    print(f"Report: {args.output}")
    return 0 if result.decision == "GO" else 2


if __name__ == "__main__":
    sys.exit(main())
