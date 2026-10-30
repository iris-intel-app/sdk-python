# Iris SDK for Python

**Rug checks, insider maps and fund traces from your own code.** The official client for the [Iris](https://iriscan.app) API: analyze any wallet or token, find the wallets a token's dev is linked to, catch launch kits like Proxima and BlockX, and follow stolen funds through mixers, exchanges and bridges.

```bash
pip install iriscan
```

Python 3.9+. One dependency: `httpx`. Sync and async clients with the same methods, typed responses (`TypedDict`s in `iriscan.types`).

## Quickstart

```python
from iriscan import Iris, risk_summary

iris = Iris()  # reads IRIS_API_KEY, or Iris(api_key="iris_live_…")

report = iris.analyze("<token mint>")             # 1 analysis
print(report["risk"]["level"], report["risk"]["score"])  # HIGH 82

scan = iris.launch_tool("<dev wallet or mint>")   # free
if scan["verdict"] != "none":
    print("Made with", scan["tool_name"])

print(risk_summary(report))  # bundled, bundle_held_pct, dev_sold, dev_held_pct, launch_tool, risk_score, notes
```

Async:

```python
from iriscan import AsyncIris

async with AsyncIris() as iris:
    report = await iris.analyze("<token mint>")
```

## Get an API key

Create one in [your account](https://iriscan.app/account) (Account, then API). The client reads `IRIS_API_KEY` from the environment when you don't pass `api_key`. Keep the key on a server: it spends your account's credits.

The free tier gives 10 API calls a day. Plans and credit packs: [iriscan.app/pricing](https://iriscan.app/pricing).

## Endpoints

| Method | Route | What it returns | Cost |
| --- | --- | --- | --- |
| `analyze(address, chain=None, depth=None)` | `POST /analyze` | Identity, risk score, labels, behaviors, flows; a full token report for a mint (launch, bundle, holders, dev, launch kit) | 1 analysis, 2 above 1,000 transactions (a wallet of 25 transactions or fewer is free) |
| `insiders(mint, chain=None, limit=None, depth=None)` | `POST /insiders` | The wallets the token's creator is linked to by money, with the payments that link them | 2 analyses, or 2 credits |
| `launch_tool(wallet_or_mint, mint=None)` | `POST /launch-tool` | Whether a wallet (or a mint's creator) used Proxima or BlockX, with fee wallets, claims and the funding tree | Free: 10 a minute, 20 a day on the free tier |
| `follow(address, chain=None, asset=None, since=None, max_hops=None)` | `POST /follow` | The main stream of money out of a wallet, hop by hop, to an exchange, bridge, mixer or rest | 2 analyses, or 2 credits |
| `trace(wallet, *, counterparty, signature, direction, time, sol, usd, window=None, chain=None, hops=None)` | `POST /trace` | The likely wallets on the other side of a mixer, exchange or swap service | 1 trace, or 3 credits |
| `trace_transfer(wallet, tx, chain=None, counterparty=None, direction=None)` | `POST /trace/transfer` | `trace` from just a wallet and a transaction: Iris reads the transaction and finds the transfer | As `trace` |
| `tx(hash, chain=None)` | `POST /tx` | One transaction explained: transfers, parties, programs, bridge | Free: 60 a minute, 100 a day on the free tier |
| `victims(drainer)` | `POST /victims` | Every wallet a drainer took funds from, and what each lost | 3 analyses, or 3 credits |
| `kind(address, chain=None)` | `POST /kind` | `"token"` or `"other"` | Free, no key needed |
| `chains(address)` | `POST /chains` | Which EVM chains a 0x address used, with its nonce and balance, and `pick`: the most active one | Free: 20 a minute, 50 a day on the free tier |
| `xchain_resolve(tx, chain=None)` | `POST /xchain/resolve` | The bridge transfers a transaction started or finished, both ends | Free: 30 a minute (shared with `xchain_wallet`) |
| `xchain_wallet(address, chain=None)` | `POST /xchain/wallet` | A wallet's bridge transfers, sent and received | Free, as above |
| `status()` | `GET /status` | The health of the API and its dependencies | Free, public |

Every call made with a key also counts toward the key's call limit (10 a day on the free tier, a number per 10 minutes on a plan). A call that fails is never charged.

Chains: `solana`, `ethereum`, `base`, `arbitrum`, `robinhood`, `bsc`, `polygon`, `dydx`, `noble`, `bitcoin`, `tron`. Leave `chain` out and Iris reads it from the address. Each route accepts the chains in its [docs](https://iriscan.app/developers). Times (`since`, `time`) take Unix seconds or a `datetime`.

## The risk summary

`risk_summary(result)` reduces an `analyze`, `insiders` or `launch_tool` result to one shape:

```python
{
    "bundled": bool | None,            # a launch bundle was found
    "bundle_held_pct": float | None,   # 0 to 100: what the bundle holds now
    "dev_sold": bool | None,           # the creator sold some
    "dev_held_pct": float | None,      # 0 to 100: what the creator holds now
    "launch_tool": str | None,         # "Proxima", "BlockX", "Launch kit"... only when one was detected
    "risk_score": float | None,        # 0 to 100, from analyze
    "notes": list[str],                # short facts, ready to show
}
```

Every field comes from what the API returned. `None` means "this call doesn't say", never "no". A launch-tool scan always names the kit it checked (`tool_name`), so `launch_tool` is set only when `verdict` is not `"none"`.

## Errors

Every failure raises an `IrisError`:

```python
from iriscan import Iris, IrisError

try:
    iris.insiders(mint)
except IrisError as e:
    e.status       # 400, 401, 402, 429, 503, 504... or 0 when no answer came back
    e.code         # "login", "invalid_key", "no_credits", "quota_exceeded", "daily_limit", "rate_limited", "busy", "timeout"...
    e.retry_after  # seconds, on 429 and 503 when known
    e.body         # the API's JSON body
    str(e)         # the API's message, ready to show
```

| Status | Code | Means |
| --- | --- | --- |
| 400 | | The request is wrong: fix it, don't retry |
| 401 | `login`, `invalid_key` | No key, or a revoked one |
| 402 | `no_credits` | Nothing left on the plan or in packs |
| 429 | `quota_exceeded`, `daily_limit`, `rate_limited` | Over a limit: wait `retry_after` |
| 503 | `busy`, `unavailable` | At capacity, or a feature is off |
| 504 | `timeout` | The work took over 2 minutes |
| 0 | `network_error`, `client_timeout`, `unresolved` | Raised by the client |

Retries are off by default. `Iris(max_retries=2)` retries a 429 or 503 after its `Retry-After` (or 2 s, 4 s, 8 s), unless the wait is longer than `max_retry_delay` (60 s by default): a daily limit is raised at once.

After a paid call, `iris.last_credits` holds what the account has left.

## Options

```python
Iris(
    api_key=None,                        # default: the IRIS_API_KEY environment variable
    base_url="https://iriscan.app/api",  # default
    timeout=120.0,                       # seconds, default (the API stops work at 2 minutes)
    max_retries=0,                       # default
    max_retry_delay=60.0,                # default
    user_agent=None,                     # default "iriscan-python/<version>"
    http_client=None,                    # your own httpx.Client (httpx.AsyncClient for AsyncIris)
)
```

Without a key, `status()` and `kind()` work as they are; the other routes answer `401` with the code `login`.

## Examples

- [`examples/check_token.py`](examples/check_token.py): analyze a token and print its risk summary.
- [`examples/check_launch_tool.py`](examples/check_launch_tool.py): check a dev wallet for Proxima or BlockX.

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest                    # unit tests, mocked HTTP
IRIS_LIVE=1 pytest        # adds a smoke test of the free endpoints against iriscan.app
```

## Links

- API docs: [iriscan.app/developers](https://iriscan.app/developers)
- Pricing: [iriscan.app/pricing](https://iriscan.app/pricing)
- API keys: [iriscan.app/account](https://iriscan.app/account)
- Status: [iriscan.app/status](https://iriscan.app/status)

## License

MIT
