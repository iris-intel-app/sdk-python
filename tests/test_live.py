"""Calls the real API, free endpoints only. Skipped unless IRIS_LIVE=1.

With IRIS_API_KEY set, /launch-tool and /tx must answer; without one, they must refuse cleanly
with a 401 (they need a key, or the website's visitor cookie).
"""

import os

import pytest

from iriscan import Iris, IrisError

pytestmark = pytest.mark.skipif(os.environ.get("IRIS_LIVE") != "1", reason="set IRIS_LIVE=1 to call iriscan.app")

WALLET = "2zy2NEyvzXfPkdFesbisZViTyz6oCWERFEvSD9PfoRg1"
# The first Ethereum transaction that moved ETH (block 46147).
ETH_TX = "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060"


@pytest.fixture(scope="module")
def iris():
    with Iris(base_url=os.environ.get("IRIS_BASE_URL") or "https://iriscan.app/api", max_retries=1) as client:
        yield client


def test_status(iris):
    s = iris.status()
    assert s["status"] in ("operational", "degraded", "outage", "unknown")
    assert isinstance(s["components"], list)


def test_kind(iris):
    assert iris.kind(WALLET)["kind"] in ("token", "other")


def test_launch_tool(iris):
    if iris.has_api_key:
        r = iris.launch_tool(WALLET)
        assert r["wallet"] == WALLET
        assert r["verdict"] in ("tool", "likely", "none")
    else:
        with pytest.raises(IrisError) as e:
            iris.launch_tool(WALLET)
        assert (e.value.status, e.value.code) == (401, "login")


def test_tx(iris):
    if iris.has_api_key:
        t = iris.tx(ETH_TX, chain="ethereum")
        assert t["hash"].lower() == ETH_TX
        assert t["chain"] == "ethereum"
    else:
        with pytest.raises(IrisError) as e:
            iris.tx(ETH_TX, chain="ethereum")
        assert (e.value.status, e.value.code) == (401, "login")
