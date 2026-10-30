from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Optional, Tuple

from ._errors import IrisError

# Coins counted as the chain's native coin in a trace's `sol` (wrapped ones included).
_NATIVE = {"SOL", "WSOL", "ETH", "WETH", "BNB", "WBNB", "BTC", "TRX", "WTRX"}
# Coins counted as dollars in a trace's `usd`.
_STABLE = {"USDC", "USDT", "USDC.E", "USDBC", "PYUSD", "USD1", "DAI", "USDS", "FDUSD"}
# Party categories a trace goes through: exchanges, mixers and privacy pools, swap services.
_THROUGH = re.compile(r"exchange|cex|mixer|privacy|swap|instant", re.I)


def plan_trace(
    summary: Mapping[str, Any],
    wallet: str,
    *,
    counterparty: Optional[str] = None,
    direction: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    """The ``/trace`` request for ``wallet``'s transfer in a transaction read with ``/tx``.

    Returns ``(wallet, fields)``: the counterparty (the one asked for, else a known exchange,
    mixer or swap service, else the largest), the direction, the time and the amounts moved
    between the two. Raises ``IrisError`` (code ``unresolved``) when there is nothing to trace.
    """
    evm = wallet.strip().lower().startswith("0x")

    def norm(a: str) -> str:
        return a.strip().lower() if evm else a.strip()

    me = norm(wallet)
    wanted = norm(counterparty) if counterparty else None
    time = summary.get("time")
    if time is None:
        raise _unresolved("The transaction's time could not be read, so it can't be traced")

    legs: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for t in summary.get("transfers") or []:
        src, dst = norm(t["from"]), norm(t["to"])
        if src == me and dst != me:
            way, other = "out", dst
        elif dst == me and src != me:
            way, other = "in", src
        else:
            continue
        if wanted and other != wanted:
            continue
        if direction and direction != way:
            continue
        asset = str(t.get("asset", "")).upper()
        leg = legs.setdefault((way, other), {"other": other, "direction": way, "sol": 0.0, "usd": 0.0, "value": 0.0})
        amount = float(t.get("amount") or 0)
        if asset in _NATIVE:
            leg["sol"] += amount
        elif asset in _STABLE:
            leg["usd"] += amount
        usd = t.get("usd")
        leg["value"] += float(usd) if usd is not None else (amount if asset in _STABLE else 0.0)

    base = {"signature": summary.get("hash"), "time": time, "chain": summary.get("chain")}
    candidates = [leg for leg in legs.values() if leg["sol"] > 0 or leg["usd"] > 0]
    if not candidates:
        # A Bitcoin wallet through a CoinJoin: the CoinJoin's txid is the counterparty.
        if summary.get("chain") == "bitcoin":
            sent = any(norm(t["from"]) == me for t in summary.get("transfers") or [])
            fields = dict(base, counterparty=wanted or summary.get("hash"), direction=direction or ("out" if sent else "in"), sol=0, usd=0)
            return me, fields
        if wanted:
            raise _unresolved(f"The transaction moved no coin or stablecoin between {wallet} and {counterparty}")
        raise _unresolved(f"The transaction moved no coin or stablecoin to or from {wallet}")

    parties = {norm(p["address"]): p for p in summary.get("parties") or []}

    def through(leg: Dict[str, Any]) -> bool:
        p = parties.get(leg["other"])
        return bool(p and _THROUGH.search(f"{p.get('category') or ''} {p.get('label') or ''}"))

    def size(leg: Dict[str, Any]) -> float:
        return float(leg["value"] or leg["sol"] + leg["usd"])

    pick = sorted(candidates, key=lambda leg: (through(leg), size(leg)), reverse=True)[0]
    fields = dict(
        base,
        counterparty=pick["other"],
        direction=pick["direction"],
        sol=round(pick["sol"], 9),
        usd=round(pick["usd"], 9),
    )
    return me, fields


def _unresolved(message: str) -> IrisError:
    return IrisError(message, status=0, code="unresolved")
