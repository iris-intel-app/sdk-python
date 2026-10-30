from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from .types import RiskSummary

_KIT_NAMES: Dict[str, str] = {
    "proxima": "Proxima",
    "blockx": "BlockX",
    "launch_kit": "Launch kit",
    "funded_like_kit": "Launch kit (funding only)",
}


def risk_summary(result: Mapping[str, Any]) -> RiskSummary:
    """A few facts about a token or a dev, in one shape whatever call they came from.

    Takes what ``analyze``, ``insiders`` or ``launch_tool`` returned. Every field is read from the
    API's answer; ``None`` means "this call doesn't say", never "no". Percentages are 0 to 100.

    - ``bundled``: a launch bundle was found (``analyze`` of a token: ``token.bundle``; ``insiders``:
      True when an insider bought in the launch block, else None).
    - ``bundle_held_pct``: what the bundle holds now (``insiders``: what the bundled insiders hold).
    - ``dev_sold``, ``dev_held_pct``: the creator sold some; what it holds now.
    - ``launch_tool``: "Proxima", "BlockX", "Launch kit"... only when one was detected. A launch-tool
      scan always names the kit it checked, so its ``verdict`` must not be "none".
    - ``risk_score``: Iris's score, 0 to 100 (``analyze`` only).
    - ``notes``: short facts, ready to show.
    """
    out: RiskSummary = {
        "bundled": None,
        "bundle_held_pct": None,
        "dev_sold": None,
        "dev_held_pct": None,
        "launch_tool": None,
        "risk_score": None,
        "notes": [],
    }
    if not isinstance(result, Mapping):
        return out
    if "verdict" in result and "tool_name" in result and "sells" in result:
        _from_launch_tool(result, out)
    elif isinstance(result.get("insiders"), list) and "dev" in result:
        _from_insiders(result, out)
    elif "identity" in result and "risk" in result:
        _from_analyze(result, out)
    else:
        out["notes"].append("Not a result of analyze, insiders or launch_tool")
    return out


def _from_launch_tool(r: Mapping[str, Any], out: RiskSummary) -> None:
    notes = out["notes"]
    # The report names the kit it looked for even when it found nothing: only a verdict counts.
    if r.get("verdict") != "none":
        out["launch_tool"] = r.get("tool_name")
        notes.append(f"{r.get('verdict_name')} (confidence {_fmt(_pct(r.get('confidence') or 0))}%)")
        for e in r.get("evidence") or []:
            if e.get("strength") == "strong":
                notes.append(e.get("text", ""))
    else:
        checked = ", ".join(r.get("checked") or []) or r.get("tool_name") or "launch kits"
        notes.append(f"No launch kit found (checked {checked})")
    # Sells are the scanned wallet's: the dev's own sells of one token only when narrowed to it.
    if r.get("mint") and ((r.get("sells") or {}).get("seen") or 0) > 0:
        out["dev_sold"] = True
    if r.get("complete") is False:
        notes.append("The scan was cut short: some history was not read")
    notes.extend(r.get("notes") or [])


def _from_insiders(r: Mapping[str, Any], out: RiskSummary) -> None:
    notes = out["notes"]
    bundled = [i for i in r.get("insiders") or [] if i.get("bundled")]
    if bundled:
        out["bundled"] = True
        out["bundle_held_pct"] = _pct(sum(i.get("holds") or 0 for i in bundled))
        notes.append(f"{len(bundled)} insider{'' if len(bundled) == 1 else 's'} bought in the launch block")
    s = r.get("summary") or {}
    if s:
        n = s.get("insiders", 0)
        notes.append(
            f"{n} wallet{'' if n == 1 else 's'} linked to the dev by money, "
            f"holding {_fmt(_pct(s.get('held_share') or 0))}% of the supply"
        )
    if r.get("complete") is False:
        notes.append(f"The search was cut short: {s.get('checked', 0)} of {s.get('candidates', 0)} wallets checked")
    notes.extend(r.get("notes") or [])


def _from_analyze(r: Mapping[str, Any], out: RiskSummary) -> None:
    risk = r.get("risk") or {}
    score = risk.get("score")
    out["risk_score"] = score if isinstance(score, (int, float)) else None
    token = r.get("token")
    if not token:
        identity = (r.get("identity") or {}).get("type") or "UNKNOWN"
        out["notes"].append(f"{identity}, risk {risk.get('level') or 'unknown'}")
        return
    _from_token(token, out)
    if (r.get("meta") or {}).get("scope") == "database":
        out["notes"].append("Only labels were available: nothing was read on chain")


def _from_token(token: Mapping[str, Any], out: RiskSummary) -> None:
    notes: List[str] = out["notes"]
    bundle = token.get("bundle")
    launch: Optional[Mapping[str, Any]] = token.get("launch")
    # `bundle` is None when no bundle was found; that means "no" only when the launch was read.
    if bundle and (bundle.get("wallets") or 0) > 0:
        out["bundled"] = True
        out["bundle_held_pct"] = _pct(bundle.get("held_share") or 0)
        if bundle.get("summary"):
            notes.append(bundle["summary"])
    elif launch:
        out["bundled"] = False
        out["bundle_held_pct"] = 0.0

    creator = next((g for g in token.get("groups") or [] if g.get("key") == "creator"), None)
    if creator:
        out["dev_held_pct"] = _pct(creator.get("held_share") or 0)
        out["dev_sold"] = (creator.get("sold_share") or 0) > 0 or ((launch or {}).get("creator_sold") or 0) > 0
    elif launch:
        out["dev_sold"] = (launch.get("creator_sold") or 0) > 0
        dev = launch.get("creator")
        holder = next((h for h in token.get("holders") or [] if dev and h.get("address") == dev), None)
        if holder:
            out["dev_held_pct"] = _pct(holder.get("share") or 0)

    kit = token.get("launch_tool")
    if kit and kit.get("verdict") and kit.get("verdict") != "none":
        out["launch_tool"] = _KIT_NAMES.get(kit["verdict"], kit.get("tool"))
        if kit.get("summary"):
            notes.append(kit["summary"])
    for flag in token.get("flags") or []:
        notes.append(flag.get("title", ""))


def _pct(share: float) -> float:
    """A 0-to-1 share as a percentage, two decimals."""
    return round(share * 100, 2)


def _fmt(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else str(n)
