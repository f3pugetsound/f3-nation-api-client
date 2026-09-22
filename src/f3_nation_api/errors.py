"""Exceptions raised by the F3 Nation API client."""


class F3NationError(Exception):
    """Base exception for client failures."""


class F3NationResponseError(F3NationError):
    """The API returned a response that does not match its contract."""


class F3NationAuthenticationError(F3NationError):
    """The API rejected the configured credentials."""


class F3NationNotFoundError(F3NationError):
    """A requested F3 Nation resource could not be found."""


class F3NationAmbiguousMatchError(F3NationError):
    """An exact lookup returned more than one matching resource."""


class F3NationRateLimitError(F3NationError):
    """The API remained rate-limited after bounded retries."""


class F3NationServerError(F3NationError):
    """The API remained unavailable after bounded retries."""
