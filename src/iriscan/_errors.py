from __future__ import annotations

from typing import Optional


class IrisError(Exception):
    """Any call that didn't return a result.

    A non-2xx answer from the API, or a failure on the way (network, timeout), with ``status`` 0
    for the latter. ``code`` is the API's own (``login``, ``invalid_key``, ``no_credits``,
    ``quota_exceeded``, ``daily_limit``, ``rate_limited``, ``busy``, ``unavailable``,
    ``timeout``...), or one of the client's: ``network_error``, ``client_timeout``,
    ``invalid_response``, ``unresolved``.
    """

    status: int
    code: Optional[str]
    retry_after: Optional[float]
    body: object

    def __init__(
        self,
        message: str,
        *,
        status: int,
        code: Optional[str] = None,
        retry_after: Optional[float] = None,
        body: object = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.retry_after = retry_after
        self.body = body

    @property
    def retryable(self) -> bool:
        """True for errors worth retrying as is, later: 429, 5xx, network failures, timeouts."""
        if self.status == 0:
            return self.code not in ("unresolved",)
        return self.status == 429 or self.status >= 500

    def __repr__(self) -> str:
        return f"IrisError(status={self.status!r}, code={self.code!r}, message={self.message!r})"
