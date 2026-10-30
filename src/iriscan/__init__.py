"""Official Python SDK for the Iris blockchain-investigation API (https://iriscan.app).

>>> from iriscan import Iris, risk_summary
>>> iris = Iris()  # reads IRIS_API_KEY
>>> report = iris.analyze("<token mint>")
>>> risk_summary(report)
"""

from ._client import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, AsyncIris, Iris, __version__
from ._errors import IrisError
from ._risk import risk_summary
from ._trace_plan import plan_trace
from .types import Chain, RiskSummary

__all__ = [
    "Iris",
    "AsyncIris",
    "IrisError",
    "risk_summary",
    "plan_trace",
    "Chain",
    "RiskSummary",
    "DEFAULT_BASE_URL",
    "DEFAULT_TIMEOUT",
    "__version__",
]
