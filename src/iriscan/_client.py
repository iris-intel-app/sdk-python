from __future__ import annotations

import asyncio
import json
import os
import re
import time as _time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Mapping, Optional, Tuple, TypeVar, Union, cast

import httpx

from ._errors import IrisError
from .types import (
    AnalyzeResult,
    ChainsResult,
    Credits,
    FollowResult,
    InsidersResult,
    KindResult,
    LaunchToolResult,
    RateLimit,
    StatusResult,
    TraceResult,
    TxResult,
    VictimsResult,
    XchainResult,
)

__version__ = "0.1.0"

DEFAULT_BASE_URL = "https://iriscan.app/api"
DEFAULT_TIMEOUT = 120.0

T = TypeVar("T")
Time = Union[int, float, datetime]
_Request = Tuple[str, str, Optional[Dict[str, Any]]]


class _Base:
    """What the sync and async clients share: building requests and reading answers."""

    def __init__(
        self,
        api_key: Optional[str],
        base_url: str,
        timeout: float,
        max_retries: int,
        max_retry_delay: float,
        user_agent: Optional[str],
    ) -> None:
        self._api_key = api_key if api_key is not None else (os.environ.get("IRIS_API_KEY") or None)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.max_retry_delay = max_retry_delay
        self._user_agent = user_agent or f"iriscan-python/{__version__}"
        #: What the account had left after the last paid call (the ``x-iris-credits`` header).
        self.last_credits: Optional[Credits] = None
        #: The key's call limit after the last call, when the server sent it.
        self.last_rate_limit: Optional[RateLimit] = None

    @property
    def has_api_key(self) -> bool:
        return bool(self._api_key)

    def __repr__(self) -> str:  # never shows the key
        return f"{type(self).__name__}(base_url={self.base_url!r}, api_key={'set' if self._api_key else None})"

    def _headers(self, body: bool) -> Dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": self._user_agent}
        if body:
            headers["Content-Type"] = "application/json"
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    # The requests, shared by both clients: (method, path, body).

    @staticmethod
    def _post(path: str, body: Mapping[str, Any]) -> _Request:
        return "POST", path, {k: v for k, v in body.items() if v is not None}

    def _analyze(self, address: str, chain: Optional[str], depth: Optional[int]) -> _Request:
        return self._post("/analyze", {"address": address, "chain": chain, "depth": depth})

    def _insiders(self, mint: str, chain: Optional[str], limit: Optional[int], depth: Optional[int]) -> _Request:
        return self._post("/insiders", {"mint": mint, "chain": chain, "limit": limit, "depth": depth})

    def _launch_tool(self, wallet_or_mint: str, mint: Optional[str]) -> _Request:
        return self._post("/launch-tool", {"wallet": wallet_or_mint, "mint": mint})

    def _follow(
        self, address: str, chain: Optional[str], asset: Optional[str], since: Optional[Time], max_hops: Optional[int]
    ) -> _Request:
        body = {"address": address, "chain": chain, "asset": asset, "since": _unix(since), "max_hops": max_hops}
        return self._post("/follow", body)

    def _trace(self, wallet: str, fields: Mapping[str, Any]) -> _Request:
        body = dict(fields)
        body["wallet"] = wallet
        body["time"] = _unix(body.get("time"))
        return self._post("/trace", body)

    def _trace_transfer(
        self, wallet: str, tx: str, chain: Optional[str], counterparty: Optional[str], direction: Optional[str]
    ) -> _Request:
        body = {"wallet": wallet, "signature": tx, "chain": chain, "counterparty": counterparty, "direction": direction}
        return self._post("/trace/transfer", body)

    def _tx(self, hash: str, chain: Optional[str]) -> _Request:
        return self._post("/tx", {"hash": hash, "chain": chain})

    def _victims(self, drainer: str) -> _Request:
        return self._post("/victims", {"address": drainer})

    def _kind(self, address: str, chain: Optional[str]) -> _Request:
        return self._post("/kind", {"address": address, "chain": chain})

    def _chains(self, address: str) -> _Request:
        return self._post("/chains", {"address": address})

    def _xchain_resolve(self, tx: str, chain: Optional[str]) -> _Request:
        return self._post("/xchain/resolve", {"chain": chain or _guess_tx_chain(tx), "tx": tx})

    def _xchain_wallet(self, address: str, chain: Optional[str]) -> _Request:
        default = "ethereum" if address.strip().lower().startswith("0x") else "solana"
        return self._post("/xchain/wallet", {"chain": chain or default, "address": address})

    # Answers.

    def _read(self, response: httpx.Response) -> Any:
        self._read_headers(response.headers)
        text = response.text
        parsed = _parse_json(text)
        if not response.is_success:
            raise _error_from(response, parsed, text)
        if parsed is _NOT_JSON:
            raise IrisError(
                "Iris answered with something that is not JSON",
                status=response.status_code,
                code="invalid_response",
                body=text,
            )
        return parsed

    def _read_headers(self, headers: httpx.Headers) -> None:
        credits = headers.get("x-iris-credits")
        if credits:
            parsed = _parse_json(credits)
            if isinstance(parsed, dict):
                self.last_credits = cast(Credits, parsed)
        try:
            if "x-ratelimit-limit" in headers:
                self.last_rate_limit = {
                    "limit": int(headers["x-ratelimit-limit"]),
                    "remaining": int(headers["x-ratelimit-remaining"]),
                    "reset": int(headers["x-ratelimit-reset"]),
                }
        except (KeyError, ValueError):
            pass

    def _retry_delay(self, error: IrisError, attempt: int) -> Optional[float]:
        """Seconds to wait before retrying, or None to give up."""
        if attempt >= self.max_retries or error.status not in (429, 503):
            return None
        delay = error.retry_after if error.retry_after is not None else 2.0 * 2**attempt
        return None if delay > self.max_retry_delay else delay


class Iris(_Base):
    """The Iris API client.

    >>> iris = Iris(api_key="iris_live_…")   # or set IRIS_API_KEY
    >>> report = iris.analyze("<mint>")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        *,
        max_retries: int = 0,
        max_retry_delay: float = 60.0,
        user_agent: Optional[str] = None,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        super().__init__(api_key, base_url, timeout, max_retries, max_retry_delay, user_agent)
        self._owns_client = http_client is None
        self._http = http_client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        if self._owns_client:
            self._http.close()

    def __enter__(self) -> "Iris":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def analyze(self, address: str, chain: Optional[str] = None, depth: Optional[int] = None) -> AnalyzeResult:
        """Who an address is, how risky, the evidence, its money in and out; a token report for a mint. 1 analysis (2 above 1,000 transactions)."""
        return cast(AnalyzeResult, self._call(self._analyze(address, chain, depth)))

    def insiders(
        self, mint: str, chain: Optional[str] = None, limit: Optional[int] = None, depth: Optional[int] = None
    ) -> InsidersResult:
        """A token's insiders: the wallets its creator is linked to by money. 2 analyses or 2 credits."""
        return cast(InsidersResult, self._call(self._insiders(mint, chain, limit, depth)))

    def launch_tool(self, wallet_or_mint: str, mint: Optional[str] = None) -> LaunchToolResult:
        """Whether a Solana wallet (or a mint's creator) used a launch kit (Proxima, BlockX). Free."""
        return cast(LaunchToolResult, self._call(self._launch_tool(wallet_or_mint, mint)))

    def follow(
        self,
        address: str,
        chain: Optional[str] = None,
        asset: Optional[str] = None,
        since: Optional[Time] = None,
        max_hops: Optional[int] = None,
    ) -> FollowResult:
        """The main stream of money out of a wallet, hop by hop. 2 analyses or 2 credits."""
        return cast(FollowResult, self._call(self._follow(address, chain, asset, since, max_hops)))

    def trace(
        self,
        wallet: str,
        *,
        counterparty: str,
        signature: str,
        direction: str,
        time: Time,
        sol: float,
        usd: float,
        window: Optional[int] = None,
        chain: Optional[str] = None,
        hops: Optional[int] = None,
        counterparty_kind: Optional[str] = None,
    ) -> TraceResult:
        """One transfer followed through a mixer, an exchange or a swap service. 1 trace, or 3 credits."""
        fields = dict(
            counterparty=counterparty, signature=signature, direction=direction, time=time, sol=sol, usd=usd,
            window=window, chain=chain, hops=hops, counterparty_kind=counterparty_kind,
        )
        return cast(TraceResult, self._call(self._trace(wallet, fields)))

    def trace_transfer(
        self,
        wallet: str,
        tx: str,
        chain: Optional[str] = None,
        counterparty: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> TraceResult:
        """``trace`` from a wallet and a transaction: Iris reads the transaction and finds the wallet's
        transfer to or from a mixer, exchange or swap service (or ``counterparty``). Costs what ``trace`` costs."""
        return cast(TraceResult, self._call(self._trace_transfer(wallet, tx, chain, counterparty, direction)))

    def tx(self, hash: str, chain: Optional[str] = None) -> TxResult:
        """One transaction explained: transfers, parties, programs, bridge. Free (with a key)."""
        return cast(TxResult, self._call(self._tx(hash, chain)))

    def victims(self, drainer: str) -> VictimsResult:
        """A drainer's victims and what each lost (Solana). 3 analyses or 3 credits."""
        return cast(VictimsResult, self._call(self._victims(drainer)))

    def kind(self, address: str, chain: Optional[str] = None) -> KindResult:
        """Whether an address is a token ("token") or not ("other"). Free, no key needed."""
        return cast(KindResult, self._call(self._kind(address, chain)))

    def chains(self, address: str) -> ChainsResult:
        """Which EVM chains a 0x address has used. Free."""
        return cast(ChainsResult, self._call(self._chains(address)))

    def xchain_resolve(self, tx: str, chain: Optional[str] = None) -> XchainResult:
        """The bridge transfers a transaction started or finished. Free (with a key)."""
        return cast(XchainResult, self._call(self._xchain_resolve(tx, chain)))

    def xchain_wallet(self, address: str, chain: Optional[str] = None) -> XchainResult:
        """A wallet's bridge transfers, sent and received. Free (with a key)."""
        return cast(XchainResult, self._call(self._xchain_wallet(address, chain)))

    def status(self) -> StatusResult:
        """The health of the API and what it relies on. Free, public."""
        return cast(StatusResult, self._call(("GET", "/status", None)))

    def _call(self, request: _Request) -> Any:
        method, path, body = request
        attempt = 0
        while True:
            try:
                return self._once(method, path, body)
            except IrisError as e:
                delay = self._retry_delay(e, attempt)
                if delay is None:
                    raise
                _time.sleep(delay)
                attempt += 1

    def _once(self, method: str, path: str, body: Optional[Dict[str, Any]]) -> Any:
        try:
            response = self._http.request(
                method,
                self._url(path),
                headers=self._headers(body is not None),
                content=None if body is None else json.dumps(body),
                timeout=self.timeout,
            )
        except httpx.TimeoutException as e:
            raise IrisError(f"Iris did not answer within {self.timeout:g} s", status=0, code="client_timeout") from e
        except httpx.HTTPError as e:
            raise IrisError(f"Could not reach Iris: {e}", status=0, code="network_error") from e
        return self._read(response)


class AsyncIris(_Base):
    """The Iris API client for asyncio, with the same methods as ``Iris``.

    >>> async with AsyncIris() as iris:
    ...     report = await iris.analyze("<mint>")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        *,
        max_retries: int = 0,
        max_retry_delay: float = 60.0,
        user_agent: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        super().__init__(api_key, base_url, timeout, max_retries, max_retry_delay, user_agent)
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def __aenter__(self) -> "AsyncIris":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def analyze(self, address: str, chain: Optional[str] = None, depth: Optional[int] = None) -> AnalyzeResult:
        """See ``Iris.analyze``."""
        return cast(AnalyzeResult, await self._call(self._analyze(address, chain, depth)))

    async def insiders(
        self, mint: str, chain: Optional[str] = None, limit: Optional[int] = None, depth: Optional[int] = None
    ) -> InsidersResult:
        """See ``Iris.insiders``."""
        return cast(InsidersResult, await self._call(self._insiders(mint, chain, limit, depth)))

    async def launch_tool(self, wallet_or_mint: str, mint: Optional[str] = None) -> LaunchToolResult:
        """See ``Iris.launch_tool``."""
        return cast(LaunchToolResult, await self._call(self._launch_tool(wallet_or_mint, mint)))

    async def follow(
        self,
        address: str,
        chain: Optional[str] = None,
        asset: Optional[str] = None,
        since: Optional[Time] = None,
        max_hops: Optional[int] = None,
    ) -> FollowResult:
        """See ``Iris.follow``."""
        return cast(FollowResult, await self._call(self._follow(address, chain, asset, since, max_hops)))

    async def trace(
        self,
        wallet: str,
        *,
        counterparty: str,
        signature: str,
        direction: str,
        time: Time,
        sol: float,
        usd: float,
        window: Optional[int] = None,
        chain: Optional[str] = None,
        hops: Optional[int] = None,
        counterparty_kind: Optional[str] = None,
    ) -> TraceResult:
        """See ``Iris.trace``."""
        fields = dict(
            counterparty=counterparty, signature=signature, direction=direction, time=time, sol=sol, usd=usd,
            window=window, chain=chain, hops=hops, counterparty_kind=counterparty_kind,
        )
        return cast(TraceResult, await self._call(self._trace(wallet, fields)))

    async def trace_transfer(
        self,
        wallet: str,
        tx: str,
        chain: Optional[str] = None,
        counterparty: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> TraceResult:
        """See ``Iris.trace_transfer``."""
        return cast(TraceResult, await self._call(self._trace_transfer(wallet, tx, chain, counterparty, direction)))

    async def tx(self, hash: str, chain: Optional[str] = None) -> TxResult:
        """See ``Iris.tx``."""
        return cast(TxResult, await self._call(self._tx(hash, chain)))

    async def victims(self, drainer: str) -> VictimsResult:
        """See ``Iris.victims``."""
        return cast(VictimsResult, await self._call(self._victims(drainer)))

    async def kind(self, address: str, chain: Optional[str] = None) -> KindResult:
        """See ``Iris.kind``."""
        return cast(KindResult, await self._call(self._kind(address, chain)))

    async def chains(self, address: str) -> ChainsResult:
        """See ``Iris.chains``."""
        return cast(ChainsResult, await self._call(self._chains(address)))

    async def xchain_resolve(self, tx: str, chain: Optional[str] = None) -> XchainResult:
        """See ``Iris.xchain_resolve``."""
        return cast(XchainResult, await self._call(self._xchain_resolve(tx, chain)))

    async def xchain_wallet(self, address: str, chain: Optional[str] = None) -> XchainResult:
        """See ``Iris.xchain_wallet``."""
        return cast(XchainResult, await self._call(self._xchain_wallet(address, chain)))

    async def status(self) -> StatusResult:
        """See ``Iris.status``."""
        return cast(StatusResult, await self._call(("GET", "/status", None)))

    async def _call(self, request: _Request) -> Any:
        method, path, body = request
        attempt = 0
        while True:
            try:
                return await self._once(method, path, body)
            except IrisError as e:
                delay = self._retry_delay(e, attempt)
                if delay is None:
                    raise
                await asyncio.sleep(delay)
                attempt += 1

    async def _once(self, method: str, path: str, body: Optional[Dict[str, Any]]) -> Any:
        try:
            response = await self._http.request(
                method,
                self._url(path),
                headers=self._headers(body is not None),
                content=None if body is None else json.dumps(body),
                timeout=self.timeout,
            )
        except httpx.TimeoutException as e:
            raise IrisError(f"Iris did not answer within {self.timeout:g} s", status=0, code="client_timeout") from e
        except httpx.HTTPError as e:
            raise IrisError(f"Could not reach Iris: {e}", status=0, code="network_error") from e
        return self._read(response)


# ------------------------------------------------------------------------------------------------

_NOT_JSON = object()


def _parse_json(text: str) -> Any:
    if not text:
        return _NOT_JSON
    try:
        return json.loads(text)
    except ValueError:
        return _NOT_JSON


def _error_from(response: httpx.Response, parsed: Any, text: str) -> IrisError:
    data = parsed if isinstance(parsed, dict) else {}
    message = data.get("error") if isinstance(data.get("error"), str) and data.get("error") else None
    if message is None:
        reason = f" {response.reason_phrase}" if response.reason_phrase else ""
        message = f"Iris answered {response.status_code}{reason}"
    code = data.get("code") if isinstance(data.get("code"), str) else None
    return IrisError(
        message,
        status=response.status_code,
        code=code,
        retry_after=_retry_after(response, data, code),
        body=text if parsed is _NOT_JSON else parsed,
    )


def _retry_after(response: httpx.Response, data: Mapping[str, Any], code: Optional[str]) -> Optional[float]:
    """The ``Retry-After`` header, else the body's ``reset_at`` (some routes reach the client
    without the header), else 10 seconds for ``busy``."""
    if response.status_code not in (429, 503):
        return None
    header = response.headers.get("retry-after")
    if header:
        try:
            return max(0.0, float(header))
        except ValueError:
            try:
                when = parsedate_to_datetime(header)
                return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError):
                pass
    reset = data.get("reset_at")
    if isinstance(reset, str):
        try:
            when = datetime.fromisoformat(reset.replace("Z", "+00:00"))
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            return max(0.0, float(int((when - datetime.now(timezone.utc)).total_seconds() + 0.999)))
        except ValueError:
            pass
    if code == "busy":
        return 10.0
    return None


def _unix(value: Optional[Time]) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return int(value.timestamp())
    return int(value)


_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
_EVM_HASH = re.compile(r"^0x[0-9a-fA-F]{64}$")
_BASE58 = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{64,88}$")


def _guess_tx_chain(tx: str) -> str:
    t = tx.strip()
    if _EVM_HASH.match(t):
        return "ethereum"
    if not _HEX64.match(t) and _BASE58.match(t):
        return "solana"
    raise IrisError(
        "Pass chain=: a 64-hex-digit hash could be Bitcoin, Tron, Noble or dYdX",
        status=0,
        code="unresolved",
    )
