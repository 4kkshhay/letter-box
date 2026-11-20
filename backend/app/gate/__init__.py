"""Password gate in front of every page link.

Off unless PAGE_PASSWORD_HASHES lists at least one hash. When on, a correct
password sets a signed unlock cookie for one page: its HTML is served for 30
minutes after unlocking, so every later visit asks again; the shared assets
and the page's API accept the cookie for longer, so a page left open never
loses its images or saves mid-visit.
"""

import hashlib
import hmac
import json
import math
import time
import unicodedata
from collections import deque
from dataclasses import dataclass
from getpass import getpass
from pathlib import Path
from threading import Lock

from app.admin.auth import _decode, _encode, hash_password, password_hash_configured, verify_password

UNLOCK_COOKIE = "letterbox_unlock"
PAGE_UNLOCK_SECONDS = 30 * 60
RESOURCE_UNLOCK_SECONDS = 6 * 60 * 60
MAX_PASSWORD_CHARS = 200
HINT_AFTER_FAILURES = 3


@dataclass(frozen=True)
class Recipient:
    """Who the gate greets, and the hint shown after a few wrong guesses."""

    name: str = ""
    hint: str = ""


def load_recipient(static_dir: Path) -> Recipient:
    """Read the build's recipient.json (from frontend/shared); empty if absent."""
    path = static_dir / "recipient.json"
    if not path.is_file():
        return Recipient()
    data = json.loads(path.read_text())
    return Recipient(name=str(data.get("name", "")).strip(), hint=str(data.get("hint", "")).strip())


def normalize_password(value: str) -> str:
    """Case, spacing and Unicode form never matter: ` Rose` matches `rose`."""
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def parse_password_hashes(raw: str) -> tuple[str, ...]:
    """PAGE_PASSWORD_HASHES: comma-separated hashes; any one unlocks."""
    hashes = tuple(item.strip() for item in raw.split(",") if item.strip())
    if not all(password_hash_configured(item) for item in hashes):
        raise ValueError("PAGE_PASSWORD_HASHES contains an invalid hash")
    return hashes


def password_matches(password: str, hashes: tuple[str, ...]) -> bool:
    normalized = normalize_password(password[:MAX_PASSWORD_CHARS])
    return bool(normalized) and any(verify_password(normalized, item) for item in hashes)


def _signature(secret: str, payload: str) -> bytes:
    # A key of its own, so an unlock cookie can never pass as an admin session.
    key = hmac.new(secret.encode("utf-8"), b"letterbox page unlock", hashlib.sha256).digest()
    return hmac.new(key, payload.encode("ascii"), hashlib.sha256).digest()


def create_unlock(secret: str, page_name: str, *, issued_at: int | None = None) -> str:
    issued_at = int(time.time()) if issued_at is None else issued_at
    payload = f"v1:{page_name}:{issued_at}"
    return f"{payload}.{_encode(_signature(secret, payload))}"


def unlocked(
    value: str | None, secret: str, *, page_name: str | None, max_age: int, now: int | None = None
) -> bool:
    """Whether the cookie unlocks `page_name` (any page when None) within `max_age`."""
    if not value or not secret:
        return False
    try:
        payload, signature = value.rsplit(".", 1)
        version, name, issued = payload.split(":")
        age = (int(time.time()) if now is None else now) - int(issued)
        return (
            version == "v1"
            and (page_name is None or name == page_name)
            and 0 <= age <= max_age
            and hmac.compare_digest(_signature(secret, payload), _decode(signature))
        )
    except (ValueError, TypeError):
        return False


class GateThrottle:
    """Per-visitor limit on wrong guesses.

    Generous until a page has been opened, so a first visitor working out the
    password never locks themselves out; tighter after that.
    """

    WINDOW_SECONDS = 60 * 60
    GENEROUS = (20, 60 * 60)  # failures allowed, per seconds
    TIGHT = (5, 15 * 60)
    MAX_VISITORS = 10_000

    def __init__(self) -> None:
        self._failures: dict[str, deque[float]] = {}
        self._lock = Lock()

    def _recent(self, visitor: str, now: float) -> deque[float]:
        failures = self._failures.get(visitor, deque())
        while failures and now - failures[0] >= self.WINDOW_SECONDS:
            failures.popleft()
        return failures

    def failures(self, visitor: str) -> int:
        with self._lock:
            return len(self._recent(visitor, time.monotonic()))

    def retry_after(self, visitor: str, *, tight: bool) -> int:
        """Seconds until this visitor may guess again; 0 when they may now."""
        limit, seconds = self.TIGHT if tight else self.GENEROUS
        with self._lock:
            now = time.monotonic()
            counted = [at for at in self._recent(visitor, now) if now - at < seconds]
        if len(counted) < limit:
            return 0
        # Wait until enough of the counted misses fall out of the window.
        return max(1, math.ceil(seconds - (now - counted[len(counted) - limit])))

    def failed(self, visitor: str) -> None:
        with self._lock:
            now = time.monotonic()
            if visitor not in self._failures and len(self._failures) >= self.MAX_VISITORS:
                self._failures = {
                    key: kept for key in self._failures if (kept := self._recent(key, now))
                }
                while len(self._failures) >= self.MAX_VISITORS:
                    del self._failures[next(iter(self._failures))]
            failures = self._recent(visitor, now)
            failures.append(now)
            self._failures[visitor] = failures

    def succeeded(self, visitor: str) -> None:
        with self._lock:
            self._failures.pop(visitor, None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


def main() -> None:
    """Interactive entry point used by scripts/hash-page-password.sh."""
    print("Enter each page password; leave empty to finish. Case and spacing are ignored.")
    hashes = []
    while password := normalize_password(getpass(f"Password {len(hashes) + 1}: ")):
        if normalize_password(getpass("Confirm: ")) != password:
            print("Did not match; try that one again.")
            continue
        hashes.append(hash_password(password))
    if not hashes:
        raise SystemExit("No passwords entered")
    # Single quotes keep the `$` separators literal in Compose `.env` parsing.
    print(f"PAGE_PASSWORD_HASHES='{','.join(hashes)}'")
