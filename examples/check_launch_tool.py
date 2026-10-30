"""Was this wallet (or this token's dev) using a launch kit such as Proxima or BlockX?

    IRIS_API_KEY=iris_live_… python examples/check_launch_tool.py <wallet or mint>

Free (10 a minute; 20 a day on the free tier).
"""

import sys

from iriscan import Iris, IrisError, risk_summary


def main() -> int:
    target = sys.argv[1] if len(sys.argv) > 1 else "2zy2NEyvzXfPkdFesbisZViTyz6oCWERFEvSD9PfoRg1"
    with Iris() as iris:
        try:
            scan = iris.launch_tool(target)
        except IrisError as e:
            if e.status == 401:
                print("This route needs an API key: get one at https://iriscan.app/account", file=sys.stderr)
            elif e.status == 429:
                print(f"Rate limited ({e.code}); try again in {e.retry_after or 'a few'} seconds", file=sys.stderr)
            else:
                print(f"Iris refused ({e.status}): {e}", file=sys.stderr)
            return 2

    # The API always names the kit it checked: only the verdict says whether one was found.
    if scan["verdict"] == "none":
        print(f"{scan['wallet']}: no launch kit found (checked {', '.join(scan['checked'])})")
    else:
        print(f"{scan['wallet']}: {scan['verdict_name']}, confidence {round(scan['confidence'] * 100)}%")
        for e in scan["evidence"]:
            print(f"- [{e['strength']}] {e['text']}")
        print("fee wallets:", ", ".join(f["address"] for f in scan["fee_wallets"]) or "none")
    print("summary:", risk_summary(scan))
    return 0


if __name__ == "__main__":
    sys.exit(main())
