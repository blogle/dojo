"""Google OAuth web flow helpers (ephemeral).

Design goals:
- Self-host friendly; no multi-user assumptions.
- Do not persist tokens to disk or DB.
- Keep credentials only in memory and for a short time.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any

from dojo.aspire.gsheets_client import SCOPES
from dojo.core.config import Settings


class GoogleOAuthError(RuntimeError):
    pass


def _require_oauth_flow() -> Any:
    try:
        from google_auth_oauthlib.flow import Flow  # type: ignore[import-not-found]

        return Flow
    except Exception as exc:  # pragma: no cover - depends on optional deps
        raise GoogleOAuthError(
            "Missing optional dependencies for Google OAuth. "
            "Run with `uv sync --extra gsheets` (or `uv run --extra gsheets ...`)."
        ) from exc


def _client_config(settings: Settings, *, redirect_uri: str) -> dict[str, Any]:
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise GoogleOAuthError("Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")

    # Minimal config for google-auth-oauthlib.
    return {
        "web": {
            "client_id": settings.google_oauth_client_id,
            "client_secret": settings.google_oauth_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }


@dataclass
class GoogleOAuthStatus:
    connected: bool
    expires_at_s: float | None


class GoogleOAuthStore:
    """In-memory store for the web OAuth handshake + short-lived credentials."""

    def __init__(self, *, pending_ttl_s: float = 10 * 60, credentials_ttl_s: float = 20 * 60) -> None:
        self._pending_ttl_s = pending_ttl_s
        self._credentials_ttl_s = credentials_ttl_s
        self._pending_states: dict[str, float] = {}
        self._credentials: Any | None = None
        self._credentials_stored_at_s: float | None = None

    def _purge_expired(self) -> None:
        now = time.time()
        self._pending_states = {
            state: created_at
            for state, created_at in self._pending_states.items()
            if now - created_at <= self._pending_ttl_s
        }

        if self._credentials is not None and self._credentials_stored_at_s is not None:
            if now - self._credentials_stored_at_s > self._credentials_ttl_s:
                self.clear_credentials()

    def start(self, settings: Settings, *, redirect_uri: str) -> str:
        self._purge_expired()

        Flow = _require_oauth_flow()
        flow = Flow.from_client_config(
            _client_config(settings, redirect_uri=redirect_uri),
            scopes=list(SCOPES),
            redirect_uri=redirect_uri,
        )

        # Use an explicit state so we can track + enforce a TTL.
        state = secrets.token_urlsafe(32)
        auth_url, _returned_state = flow.authorization_url(
            access_type="online",
            include_granted_scopes="true",
            state=state,
        )

        self._pending_states[state] = time.time()
        return auth_url

    def finish(self, settings: Settings, *, code: str, state: str, redirect_uri: str) -> None:
        self._purge_expired()

        created_at = self._pending_states.get(state)
        if created_at is None:
            raise GoogleOAuthError("OAuth state is missing or expired; restart the sign-in flow")

        Flow = _require_oauth_flow()
        flow = Flow.from_client_config(
            _client_config(settings, redirect_uri=redirect_uri),
            scopes=list(SCOPES),
            redirect_uri=redirect_uri,
        )

        flow.fetch_token(code=code)

        # Store credentials in-memory only.
        self._credentials = flow.credentials
        self._credentials_stored_at_s = time.time()

        # One-time use.
        self._pending_states.pop(state, None)

    def clear_credentials(self) -> None:
        self._credentials = None
        self._credentials_stored_at_s = None

    def status(self) -> GoogleOAuthStatus:
        self._purge_expired()
        if self._credentials is None or self._credentials_stored_at_s is None:
            return GoogleOAuthStatus(connected=False, expires_at_s=None)
        return GoogleOAuthStatus(
            connected=True,
            expires_at_s=self._credentials_stored_at_s + self._credentials_ttl_s,
        )

    def get_credentials(self) -> Any:
        self._purge_expired()
        if self._credentials is None:
            raise GoogleOAuthError("Not connected to Google; start OAuth first")
        return self._credentials
