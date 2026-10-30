"""Analyze a token and print what matters before buying it.

    IRIS_API_KEY=iris_live_… python examples/check_token.py <mint>

Costs 1 analysis.
"""

import sys

from iriscan import Iris, IrisError, risk_summary


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python examples/check_token.py <mint>", file=sys.stderr)
        return 1
    mint = sys.argv[1]

    with Iris(max_retries=2) as iris:  # reads IRIS_API_KEY
        try:
            report = iris.analyze(mint)
        except IrisError as e:
            print(f"Iris refused ({e.status} {e.code or ''}): {e}", file=sys.stderr)
            return 2

    token = report.get("token") or {}
    risk = report["risk"]
    print(f"{token.get('name') or report['address']} ({token.get('symbol') or '?'}): "
          f"{report['identity']['type']}, risk {risk['level']} ({risk['score']}/100)")

    s = risk_summary(report)
    print(f"bundled: {s['bundled']}  bundle holds: {s['bundle_held_pct']}%")
    print(f"dev sold: {s['dev_sold']}  dev holds: {s['dev_held_pct']}%")
    print(f"launch kit: {s['launch_tool'] or 'none found'}")
    for note in s["notes"]:
        print(f"- {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
