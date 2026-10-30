import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx

from iriscan import AsyncIris, Iris, IrisError, plan_trace

BASE = "https://iriscan.app/api"
KEY = "iris_live_test_0000"
SOL = "2zy2NEyvzXfPkdFesbisZViTyz6oCWERFEvSD9PfoRg1"
MINT = "Bo9jh3wsmcC2AjakLWzNmKJ3SgtZmXEcSaW7L2FAvUsU"
SIG = "5" * 88


@pytest.fixture
def iris(monkeypatch):
    monkeypatch.delenv("IRIS_API_KEY", raising=False)
    client = Iris(api_key=KEY)
    yield client
    client.close()


def body(route):
    return json.loads(route.calls.last.request.content)


# --- requests --------------------------------------------------------------------------------


@respx.mock
def test_analyze(iris):
    route = respx.post(f"{BASE}/analyze").mock(return_value=httpx.Response(200, json={"address": SOL}))
    assert iris.analyze(SOL, chain="solana", depth=5000) == {"address": SOL}
    request = route.calls.last.request
    assert body(route) == {"address": SOL, "chain": "solana", "depth": 5000}
    assert request.headers["authorization"] == f"Bearer {KEY}"
    assert request.headers["content-type"] == "application/json"
    assert request.headers["user-agent"].startswith("iriscan-python/")


@respx.mock
def test_options_left_out(iris):
    route = respx.post(f"{BASE}/analyze").mock(return_value=httpx.Response(200, json={}))
    iris.analyze(SOL)
    assert body(route) == {"address": SOL}


@respx.mock
def test_insiders(iris):
    route = respx.post(f"{BASE}/insiders").mock(return_value=httpx.Response(200, json={"insiders": []}))
    iris.insiders(MINT, chain="bsc", limit=20, depth=3)
    assert body(route) == {"mint": MINT, "chain": "bsc", "limit": 20, "depth": 3}


@respx.mock
def test_launch_tool(iris):
    route = respx.post(f"{BASE}/launch-tool").mock(return_value=httpx.Response(200, json={"verdict": "none"}))
    iris.launch_tool(SOL, mint=MINT)
    assert body(route) == {"wallet": SOL, "mint": MINT}


@respx.mock
def test_follow(iris):
    route = respx.post(f"{BASE}/follow").mock(return_value=httpx.Response(200, json={"hops": []}))
    iris.follow(SOL, asset="native", since=datetime(2026, 1, 1, tzinfo=timezone.utc), max_hops=10, chain="solana")
    assert body(route) == {"address": SOL, "asset": "native", "since": 1767225600, "max_hops": 10, "chain": "solana"}


@respx.mock
def test_trace(iris):
    route = respx.post(f"{BASE}/trace").mock(return_value=httpx.Response(200, json={"candidates": []}))
    iris.trace(
        SOL, counterparty=MINT, signature=SIG, direction="out", time=1767225600, sol=254.0226, usd=0,
        window=3600, hops=2, counterparty_kind="mixer",
    )
    assert body(route) == {
        "wallet": SOL, "counterparty": MINT, "signature": SIG, "direction": "out", "time": 1767225600,
        "sol": 254.0226, "usd": 0, "window": 3600, "hops": 2, "counterparty_kind": "mixer",
    }


@respx.mock
def test_tx(iris):
    route = respx.post(f"{BASE}/tx").mock(return_value=httpx.Response(200, json={"hash": SIG}))
    iris.tx(SIG, chain="solana")
    assert body(route) == {"hash": SIG, "chain": "solana"}


@respx.mock
def test_victims(iris):
    route = respx.post(f"{BASE}/victims").mock(return_value=httpx.Response(200, json={"victims": 3}))
    assert iris.victims(SOL)["victims"] == 3
    assert body(route) == {"address": SOL}


@respx.mock
def test_kind(iris):
    route = respx.post(f"{BASE}/kind").mock(return_value=httpx.Response(200, json={"kind": "token"}))
    assert iris.kind(MINT, chain="solana")["kind"] == "token"
    assert body(route) == {"address": MINT, "chain": "solana"}


@respx.mock
def test_chains(iris):
    addr = "0x" + "ab" * 20
    route = respx.post(f"{BASE}/chains").mock(return_value=httpx.Response(200, json={"address": addr, "chains": []}))
    iris.chains(addr)
    assert body(route) == {"address": addr}


@respx.mock
def test_xchain_resolve(iris):
    route = respx.post(f"{BASE}/xchain/resolve").mock(return_value=httpx.Response(200, json={"links": [], "warnings": []}))
    iris.xchain_resolve("0x" + "a" * 64)
    assert body(route) == {"chain": "ethereum", "tx": "0x" + "a" * 64}
    iris.xchain_resolve("b" * 64, chain="bitcoin")
    assert body(route) == {"chain": "bitcoin", "tx": "b" * 64}
    iris.xchain_resolve(SIG)
    assert body(route)["chain"] == "solana"


def test_xchain_resolve_needs_a_chain_for_bare_hex(iris):
    with pytest.raises(IrisError) as e:
        iris.xchain_resolve("c" * 64)
    assert (e.value.status, e.value.code) == (0, "unresolved")


@respx.mock
def test_xchain_wallet(iris):
    route = respx.post(f"{BASE}/xchain/wallet").mock(return_value=httpx.Response(200, json={"links": []}))
    iris.xchain_wallet(SOL)
    assert body(route) == {"chain": "solana", "address": SOL}
    iris.xchain_wallet("0x" + "cd" * 20, chain="base")
    assert body(route)["chain"] == "base"


@respx.mock
def test_status_is_a_get(iris):
    route = respx.get(f"{BASE}/status").mock(return_value=httpx.Response(200, json={"status": "operational"}))
    assert iris.status()["status"] == "operational"
    request = route.calls.last.request
    assert request.content == b""
    assert "content-type" not in request.headers


@respx.mock
def test_trace_transfer(iris):
    route = respx.post(f"{BASE}/trace/transfer").mock(return_value=httpx.Response(200, json={"candidates": []}))
    iris.trace_transfer(SOL, SIG, chain="solana", direction="out")
    assert route.call_count == 1
    assert body(route) == {"wallet": SOL, "signature": SIG, "chain": "solana", "direction": "out"}


@respx.mock
def test_chains_pick_and_polygon(iris):
    addr = "0x" + "ef" * 20
    respx.post(f"{BASE}/chains").mock(return_value=httpx.Response(200, json={"address": addr, "chains": [], "pick": "polygon"}))
    assert iris.chains(addr)["pick"] == "polygon"
    route = respx.post(f"{BASE}/analyze").mock(return_value=httpx.Response(200, json={}))
    iris.analyze(addr, chain="polygon")
    assert body(route)["chain"] == "polygon"


def test_plan_trace_prefers_the_exchange():
    exchange = "ExchangeHotWa11et1111111111111111111111111"
    other = "SomeoneE1se11111111111111111111111111111111"
    summary = {
        "chain": "solana",
        "hash": SIG,
        "time": 1767225600,
        "transfers": [
            {"from": SOL, "to": other, "amount": 50, "asset": "SOL", "mint": None, "usd": 7500},
            {"from": SOL, "to": exchange, "amount": 10, "asset": "SOL", "mint": None, "usd": 1500},
            {"from": SOL, "to": exchange, "amount": 200, "asset": "USDC", "mint": "EPj", "usd": 200},
        ],
        "parties": [
            {"address": exchange, "chain": "solana", "kind": "wallet", "label": "Binance deposit", "category": "exchange", "entity": "Binance", "role": "receiver", "analyzable": False},
            {"address": other, "chain": "solana", "kind": "wallet", "label": None, "category": None, "entity": None, "role": "receiver", "analyzable": True},
        ],
    }
    assert plan_trace(summary, SOL) == (
        SOL,
        {"counterparty": exchange, "signature": SIG, "direction": "out", "time": 1767225600, "sol": 10, "usd": 200, "chain": "solana"},
    )
    with pytest.raises(IrisError) as e:
        plan_trace(dict(summary, transfers=[]), SOL)
    assert e.value.code == "unresolved"


# --- auth ------------------------------------------------------------------------------------


@respx.mock
def test_no_key_no_authorization(monkeypatch):
    monkeypatch.delenv("IRIS_API_KEY", raising=False)
    route = respx.post(f"{BASE}/kind").mock(return_value=httpx.Response(200, json={"kind": "other"}))
    with Iris() as iris:
        assert not iris.has_api_key
        iris.kind(SOL)
    assert "authorization" not in route.calls.last.request.headers


@respx.mock
def test_key_from_environment(monkeypatch):
    monkeypatch.setenv("IRIS_API_KEY", KEY)
    route = respx.get(f"{BASE}/status").mock(return_value=httpx.Response(200, json={}))
    with Iris() as iris:
        iris.status()
        assert KEY not in repr(iris)
    assert route.calls.last.request.headers["authorization"] == f"Bearer {KEY}"


@respx.mock
def test_base_url_and_user_agent():
    route = respx.get("http://localhost:3000/api/status").mock(return_value=httpx.Response(200, json={}))
    with Iris(api_key=KEY, base_url="http://localhost:3000/api/", user_agent="guard/1") as iris:
        iris.status()
    assert route.calls.last.request.headers["user-agent"] == "guard/1"


# --- errors ----------------------------------------------------------------------------------


def fail(iris, response):
    if isinstance(response, Exception):
        respx.post(f"{BASE}/analyze").mock(side_effect=response)
    else:
        respx.post(f"{BASE}/analyze").mock(return_value=response)
    with pytest.raises(IrisError) as e:
        iris.analyze(SOL)
    return e.value


@respx.mock
def test_400_message(iris):
    e = fail(iris, httpx.Response(400, json={"error": "Not a valid Solana address"}))
    assert (e.status, e.code, e.retry_after) == (400, None, None)
    assert str(e) == e.message == "Not a valid Solana address"
    assert e.body == {"error": "Not a valid Solana address"}
    assert not e.retryable


@respx.mock
def test_401_codes(iris):
    assert fail(iris, httpx.Response(401, json={"error": "Log in", "code": "login"})).code == "login"
    assert fail(iris, httpx.Response(401, json={"error": "bad", "code": "invalid_key"})).code == "invalid_key"


@respx.mock
def test_402_no_credits(iris):
    e = fail(iris, httpx.Response(402, json={"error": "No analyses left", "code": "no_credits"}))
    assert (e.status, e.code) == (402, "no_credits")


@respx.mock
def test_429_retry_after_header(iris):
    e = fail(iris, httpx.Response(429, json={"error": "slow", "code": "quota_exceeded"}, headers={"retry-after": "240"}))
    assert (e.status, e.code, e.retry_after) == (429, "quota_exceeded", 240)
    assert e.retryable


@respx.mock
def test_429_reset_at_without_header(iris):
    reset = (datetime.now(timezone.utc) + timedelta(seconds=90)).isoformat().replace("+00:00", "Z")
    e = fail(iris, httpx.Response(429, json={"error": "used", "code": "daily_limit", "reset_at": reset}))
    assert e.code == "daily_limit"
    assert 88 <= e.retry_after <= 91


@respx.mock
def test_503_busy_defaults_to_10s(iris):
    e = fail(iris, httpx.Response(503, json={"error": "busy", "code": "busy"}))
    assert (e.status, e.code, e.retry_after) == (503, "busy", 10)


@respx.mock
def test_504_timeout(iris):
    e = fail(iris, httpx.Response(504, json={"error": "too long", "code": "timeout"}))
    assert (e.status, e.code, e.retry_after) == (504, "timeout", None)


@respx.mock
def test_non_json_error_page(iris):
    e = fail(iris, httpx.Response(502, text="<html>Bad gateway</html>"))
    assert e.status == 502
    assert str(e) == "Iris answered 502 Bad Gateway"
    assert e.body == "<html>Bad gateway</html>"


@respx.mock
def test_non_json_success(iris):
    e = fail(iris, httpx.Response(200, text="hello"))
    assert (e.status, e.code) == (200, "invalid_response")


@respx.mock
def test_network_error(iris):
    e = fail(iris, httpx.ConnectError("connection refused"))
    assert (e.status, e.code) == (0, "network_error")
    assert "connection refused" in str(e)


@respx.mock
def test_client_timeout(iris):
    e = fail(iris, httpx.ReadTimeout("slow"))
    assert (e.status, e.code) == (0, "client_timeout")


# --- retries ---------------------------------------------------------------------------------


@respx.mock
def test_no_retries_by_default(iris):
    route = respx.get(f"{BASE}/status").mock(return_value=httpx.Response(503, json={"code": "busy"}, headers={"retry-after": "0"}))
    with pytest.raises(IrisError):
        iris.status()
    assert route.call_count == 1


@respx.mock
def test_retries_429_and_503():
    route = respx.get(f"{BASE}/status").mock(
        side_effect=[
            httpx.Response(503, json={"code": "busy"}, headers={"retry-after": "0"}),
            httpx.Response(429, json={"code": "rate_limited"}, headers={"retry-after": "0"}),
            httpx.Response(200, json={"status": "operational"}),
        ]
    )
    with Iris(api_key=KEY, max_retries=2) as iris:
        assert iris.status()["status"] == "operational"
    assert route.call_count == 3


@respx.mock
def test_gives_up_after_max_retries():
    route = respx.get(f"{BASE}/status").mock(return_value=httpx.Response(503, json={"code": "busy"}, headers={"retry-after": "0"}))
    with Iris(api_key=KEY, max_retries=1) as iris, pytest.raises(IrisError):
        iris.status()
    assert route.call_count == 2


@respx.mock
def test_no_retry_past_max_delay():
    route = respx.get(f"{BASE}/status").mock(return_value=httpx.Response(429, json={"code": "daily_limit"}, headers={"retry-after": "3600"}))
    with Iris(api_key=KEY, max_retries=3) as iris, pytest.raises(IrisError) as e:
        iris.status()
    assert e.value.retry_after == 3600
    assert route.call_count == 1


@respx.mock
def test_never_retries_400():
    route = respx.get(f"{BASE}/status").mock(return_value=httpx.Response(400, json={"error": "bad"}))
    with Iris(api_key=KEY, max_retries=3) as iris, pytest.raises(IrisError):
        iris.status()
    assert route.call_count == 1


# --- headers ---------------------------------------------------------------------------------


@respx.mock
def test_credits_and_rate_limit_headers(iris):
    credits = {"plan": "api_pro", "analyses_left": 9412, "traces_left": 488, "pack_credits": 0}
    respx.post(f"{BASE}/analyze").mock(
        return_value=httpx.Response(
            200,
            json={},
            headers={
                "x-iris-credits": json.dumps(credits),
                "x-ratelimit-limit": "500",
                "x-ratelimit-remaining": "499",
                "x-ratelimit-reset": "1793360989",
            },
        )
    )
    iris.analyze(SOL)
    assert iris.last_credits == credits
    assert iris.last_rate_limit == {"limit": 500, "remaining": 499, "reset": 1793360989}


# --- async -----------------------------------------------------------------------------------


@respx.mock
def test_async_has_the_same_methods_and_errors(monkeypatch):
    monkeypatch.delenv("IRIS_API_KEY", raising=False)
    sync_methods = {m for m in dir(Iris) if not m.startswith("_") and callable(getattr(Iris, m))} - {"close"}
    async_methods = {m for m in dir(AsyncIris) if not m.startswith("_") and callable(getattr(AsyncIris, m))} - {"aclose"}
    assert sync_methods == async_methods

    respx.post(f"{BASE}/launch-tool").mock(return_value=httpx.Response(200, json={"verdict": "none"}))
    respx.post(f"{BASE}/analyze").mock(return_value=httpx.Response(402, json={"error": "No credits", "code": "no_credits"}))
    status = respx.get(f"{BASE}/status").mock(
        side_effect=[httpx.Response(503, json={"code": "busy"}, headers={"retry-after": "0"}), httpx.Response(200, json={"status": "operational"})]
    )

    async def run():
        async with AsyncIris(api_key=KEY, max_retries=1) as iris:
            assert (await iris.launch_tool(SOL))["verdict"] == "none"
            assert (await iris.status())["status"] == "operational"
            with pytest.raises(IrisError) as e:
                await iris.analyze(SOL)
            assert (e.value.status, e.value.code) == (402, "no_credits")
            with pytest.raises(IrisError) as e:
                await iris.xchain_resolve("c" * 64)
            assert e.value.code == "unresolved"

    asyncio.run(run())
    assert status.call_count == 2


@respx.mock
def test_async_trace_transfer():
    trace = respx.post(f"{BASE}/trace/transfer").mock(return_value=httpx.Response(200, json={"candidates": []}))

    async def run():
        async with AsyncIris(api_key=KEY) as iris:
            await iris.trace_transfer("0x" + "ab" * 20, "0x" + "a" * 64, chain="polygon", counterparty="0x" + "cd" * 20)

    asyncio.run(run())
    assert body(trace) == {"wallet": "0x" + "ab" * 20, "signature": "0x" + "a" * 64, "chain": "polygon", "counterparty": "0x" + "cd" * 20}
