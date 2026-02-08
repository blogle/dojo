"""Google OAuth web flow helpers (ephemeral, in-memory).

Design goals:
- Self-host friendly; no multi-user assumptions.
- Never persist tokens to disk or DB.
- Keep credentials only in memory with a short TTL.
"""

from __future__ import annotations

import logging
import secrets
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from dojo.aspire.gsheets_client import SCOPES
from dojo.core.config import Settings

logger = logging.getLogger(__name__)


class GoogleOAuthError(RuntimeError):
    pass


def _require_oauth_flow() -> Any:
    try:
        from google_auth_oauthlib.flow import Flow  # type: ignore[import-not-found]

        return Flow
    except Exception as exc:  # pragma: no cover
        raise GoogleOAuthError("Google OAuth client libraries are unavailable in this environment.") from exc


def _client_config(settings: Settings, *, redirect_uri: str) -> dict[str, Any]:
    client_id = (settings.google_oauth_client_id or "").strip()
    client_secret = (settings.google_oauth_client_secret or "").strip()
    if not client_id or not client_secret:
        raise GoogleOAuthError("Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")

    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }


@dataclass(frozen=True)
class GoogleOAuthStatus:
    connected: bool
    expires_at_s: float | None


class GoogleOAuthStore:
    """In-memory store for the web OAuth handshake + short-lived credentials."""

    def __init__(
        self,
        *,
        pending_ttl_s: float = 10 * 60,
        credentials_ttl_s: float = 20 * 60,
    ) -> None:
        self._pending_ttl_s = pending_ttl_s
        self._credentials_ttl_s = credentials_ttl_s
        self._pending_states: dict[str, tuple[float, str | None, str]] = {}
        self._credentials: Any | None = None
        self._credentials_stored_at_s: float | None = None

    def _purge_expired(self) -> None:
        now = time.time()
        self._pending_states = {
            state: (created_at, origin, redirect_uri)
            for state, (created_at, origin, redirect_uri) in self._pending_states.items()
            if now - created_at <= self._pending_ttl_s
        }

        if self._credentials is not None and self._credentials_stored_at_s is not None:
            if now - self._credentials_stored_at_s > self._credentials_ttl_s:
                self.clear_credentials()

    def start(self, settings: Settings, *, redirect_uri: str, frontend_origin: str | None = None) -> str:
        self._purge_expired()
        Flow = _require_oauth_flow()

        # Safe diagnostics (no secrets, no codes).
        client_id = (settings.google_oauth_client_id or "").strip()
        secret_len = len((settings.google_oauth_client_secret or "").strip())
        logger.info(
            "Google OAuth start redirect_uri=%s origin=%s client_id_suffix=%s secret_len=%s",
            redirect_uri,
            frontend_origin or "",
            client_id[-10:] if len(client_id) > 10 else client_id,
            secret_len,
        )

        flow = Flow.from_client_config(
            _client_config(settings, redirect_uri=redirect_uri),
            scopes=list(SCOPES),
            redirect_uri=redirect_uri,
        )

        state = secrets.token_urlsafe(32)
        auth_url, _returned_state = flow.authorization_url(
            access_type="online",
            include_granted_scopes="true",
            state=state,
        )
        origin = None
        if frontend_origin:
            parsed = urlparse(frontend_origin)
            if parsed.scheme in {"http", "https"} and parsed.netloc:
                origin = f"{parsed.scheme}://{parsed.netloc}"

        self._pending_states[state] = (time.time(), origin, redirect_uri)
        return str(auth_url)

    def pending_frontend_origin(self, state: str) -> str | None:
        self._purge_expired()
        payload = self._pending_states.get(state)
        if not payload:
            return None
        _created_at, origin, _redirect_uri = payload
        return origin

    def pending_redirect_uri(self, state: str) -> str | None:
        self._purge_expired()
        payload = self._pending_states.get(state)
        if not payload:
            return None
        _created_at, _origin, redirect_uri = payload
        return redirect_uri

    def finish(self, settings: Settings, *, code: str, state: str, redirect_uri: str) -> str | None:
        self._purge_expired()
        if state not in self._pending_states:
            raise GoogleOAuthError("OAuth state is missing or expired; restart the sign-in flow")

        _created_at, origin, stored_redirect_uri = self._pending_states[state]
        effective_redirect_uri = stored_redirect_uri or redirect_uri

        client_id = (settings.google_oauth_client_id or "").strip()
        secret_len = len((settings.google_oauth_client_secret or "").strip())
        logger.info(
            "Google OAuth finish redirect_uri=%s client_id_suffix=%s secret_len=%s",
            effective_redirect_uri,
            client_id[-10:] if len(client_id) > 10 else client_id,
            secret_len,
        )

        Flow = _require_oauth_flow()
        flow = Flow.from_client_config(
            _client_config(settings, redirect_uri=effective_redirect_uri),
            scopes=list(SCOPES),
            redirect_uri=effective_redirect_uri,
        )
        try:
            flow.fetch_token(code=code)
        except Exception as exc:  # pragma: no cover
            err_code = getattr(exc, "error", None)
            err_desc = getattr(exc, "description", None)
            logger.warning(
                "Google OAuth token exchange failed: %s %s",
                err_code or type(exc).__name__,
                err_desc or "",
            )
            if err_code:
                raise GoogleOAuthError(f"oauth_token_exchange_failed:{err_code}") from exc
            raise GoogleOAuthError("oauth_token_exchange_failed") from exc

        self._credentials = flow.credentials
        self._credentials_stored_at_s = time.time()
        self._pending_states.pop(state, None)

        return origin

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
