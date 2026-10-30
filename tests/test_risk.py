import json
from pathlib import Path

from iriscan import risk_summary

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


def test_launch_tool_none_names_no_tool():
    r = fixture("launch-tool-none")
    assert r["tool_name"] == "Proxima"  # the API names the kit it checked
    assert risk_summary(r) == {
        "bundled": None,
        "bundle_held_pct": None,
        "dev_sold": None,
        "dev_held_pct": None,
        "launch_tool": None,
        "risk_score": None,
        "notes": ["No launch kit found (checked Proxima, BlockX)"],
    }


def test_launch_tool_detection():
    s = risk_summary(fixture("launch-tool-proxima"))
    assert s["launch_tool"] == "Proxima"
    assert s["dev_sold"] is True
    assert s["bundled"] is None and s["risk_score"] is None
    assert "Proxima (confidence 99%)" in s["notes"]
    assert "1 fee of exactly 5% of a sell (0.0657 SOL on 1.3146 SOL received)" in s["notes"]
    assert not any("landing services" in n for n in s["notes"])


def test_launch_tool_likely_counts():
    r = dict(fixture("launch-tool-none"), verdict="likely", verdict_name="Likely Proxima")
    assert risk_summary(r)["launch_tool"] == "Proxima"


def test_insiders():
    s = risk_summary(fixture("insiders"))
    assert {k: s[k] for k in ("bundled", "bundle_held_pct", "dev_sold", "dev_held_pct", "launch_tool", "risk_score")} == {
        "bundled": True,
        "bundle_held_pct": 20.0,
        "dev_sold": None,
        "dev_held_pct": None,
        "launch_tool": None,
        "risk_score": None,
    }
    assert "2 wallets linked to the dev by money, holding 25.4% of the supply" in s["notes"]


def test_insiders_without_bundled_one():
    r = fixture("insiders")
    r["insiders"] = [i for i in r["insiders"] if not i["bundled"]]
    s = risk_summary(r)
    assert s["bundled"] is None and s["bundle_held_pct"] is None


def test_token_analysis():
    s = risk_summary(fixture("analyze-token"))
    assert s["bundled"] is True
    assert s["bundle_held_pct"] == 31.25
    assert s["dev_sold"] is True
    assert s["dev_held_pct"] == 3.0
    assert s["launch_tool"] == "Proxima"
    assert s["risk_score"] == 82
    assert "A bundle holds 31% of the supply" in s["notes"]


def test_token_without_bundle():
    r = fixture("analyze-token")
    t = r["token"]
    t["bundle"] = None
    t["groups"] = []
    t["launch"]["creator_sold"] = 0
    t["launch_tool"]["verdict"] = "none"
    t["holders"] = [{"address": t["launch"]["creator"], "label": None, "entity": None, "amount": 1, "share": 0.015, "pool": False}]
    s = risk_summary(r)
    assert (s["bundled"], s["bundle_held_pct"], s["dev_sold"], s["dev_held_pct"], s["launch_tool"]) == (False, 0.0, False, 1.5, None)


def test_token_with_unread_launch():
    r = fixture("analyze-token")
    r["token"].update(bundle=None, launch=None, groups=[])
    s = risk_summary(r)
    assert (s["bundled"], s["bundle_held_pct"], s["dev_sold"], s["dev_held_pct"]) == (None, None, None, None)


def test_wallet_analysis():
    assert risk_summary(fixture("analyze-wallet")) == {
        "bundled": None,
        "bundle_held_pct": None,
        "dev_sold": None,
        "dev_held_pct": None,
        "launch_tool": None,
        "risk_score": 10,
        "notes": ["MEV_ARBITRAGE, risk LOW"],
    }


def test_something_else():
    assert risk_summary({})["notes"] == ["Not a result of analyze, insiders or launch_tool"]
