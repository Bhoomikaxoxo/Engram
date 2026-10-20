"""Engram-based session management for conversation history."""

from __future__ import annotations

import queue
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TYPE_CHECKING

from .client import spawn_context_thread
from .client import get_engram_client
from .session_auth import EngramAuthError, SessionAuthMixin
from .session_context import SessionContextMixin
from .session_migration import SessionMigrationMixin
from .session_peers import SessionPeersMixin

if TYPE_CHECKING:
    from engram import Engram

logger = logging.getLogger(__name__)

# Sentinel to signal the async writer thread to shut down
_ASYNC_SHUTDOWN = object()

# Engram persists every message and get_or_create() re-hydrates on a miss, so the local copies stay bounded.
_SESSION_MESSAGE_RETENTION = 200
_SESSION_IDLE_TTL_SECONDS = 3600
_SESSION_SWEEP_INTERVAL_SECONDS = 300
# Hard caps for a burst of distinct sessions inside one TTL window; the dicts evict least recently used,
# and _joined_author_peers drops its oldest session so its authors rejoin on their next write.
_SESSION_CACHE_MAX_SIZE = 128
_PEERS_CACHE_MAX_SIZE = 512


@dataclass
class EngramSession:
    """A conversation session backed by Engram: a local message cache that syncs to Engram."""

    key: str  # channel:chat_id
    user_peer_id: str  # Engram peer ID for the user
    assistant_peer_id: str  # Engram peer ID for the assistant
    engram_session_id: str  # Engram session ID
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    # Held by _flush_session across select, send and the _synced flip. It lives with the message list it guards.
    _flush_lock: threading.RLock = field(default_factory=threading.RLock, repr=False, compare=False)

    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        """Add a message to the local cache."""
        self.messages.append({"role": role, "content": content, "timestamp": datetime.now().isoformat(), **kwargs})
        self.updated_at = datetime.now()


class EngramSessionManager(SessionAuthMixin, SessionPeersMixin, SessionContextMixin, SessionMigrationMixin):
    """Conversation sessions backed by Engram, alongside hermes' SQLite state and file memory.
    Auth retry, peer-ID resolution, recall and memory-file migration live in the mixins."""

    def __init__(
        self, engram: Engram | None = None, context_tokens: int | None = None, config: Any | None = None,
        runtime_user_peer_name: str | None = None, runtime_user_peer_name_alt: str | None = None,
    ):
        """``engram`` defaults to the per-identity cached client; ``context_tokens`` caps
        context() calls (None = Engram default); the runtime peer names are the gateway
        user identity (and a stable alternate) for per-user memory scoping."""
        self._engram = engram
        self._context_tokens = context_tokens
        self._config = config
        self._runtime_user_peer_name = runtime_user_peer_name
        self._runtime_user_peer_name_alt = runtime_user_peer_name_alt
        self._cache: dict[str, EngramSession] = {}
        # Sessions whose flush failed after a newer object took their cache key; flush_all() retries them.
        self._retry_sessions: list[EngramSession] = []
        self._cache_lock = threading.RLock()
        self._peers_cache: dict[str, Any] = {}
        # engram_session_id -> author peer IDs already joined to that session.
        self._joined_author_peers: dict[str, set[str]] = {}
        self._sessions_cache: dict[str, Any] = {}
        self._last_idle_sweep_ts: float = 0.0
        # Bumped (under _cache_lock) whenever _force_reauth rebuilds the client, so an
        # in-flight resolver never stores an object bound to the discarded client.
        self._client_generation = 0

        # Set when a call still fails auth after a forced token refresh; cleared on the next success.
        self._auth_failure: str | None = None
        self._auth_notice_emitted = False

        # Behavior knobs copied from config (EngramClientConfig defaults when absent); the
        # observation booleans map 1:1 to Engram's SessionPeerConfig toggles.
        for name, default in (
            ("write_frequency", "async"), ("dialectic_reasoning_level", "low"), ("dialectic_dynamic", True),
            ("dialectic_max_chars", 600), ("dialectic_max_input_chars", 10000),
            ("user_observe_me", True), ("user_observe_others", True),
            ("ai_observe_me", True), ("ai_observe_others", True),
        ):
            setattr(self, f"_{name}", getattr(config, name) if config else default)
        self._turn_counter: int = 0
        # engram session id -> observation booleans. Whole dicts are swapped in one assignment, so readers never see a partial one.
        self._session_observation: dict[str, dict[str, bool]] = {}

        # Prefetch cache: session_key -> last context result (consumed once per turn).
        # Dialectic results are cached on the plugin side (EngramMemoryProvider._prefetch_result)
        # so session-start prewarm and turn-driven fires share one source of truth.
        self._context_cache: dict[str, dict] = {}
        self._prefetch_cache_lock = threading.Lock()

        # Async write queue — the writer thread starts lazily on first enqueue
        # (_ensure_async_writer_locked): constructing a manager must not spawn background
        # work or touch the network (unit tests build managers with mocked clients).
        self._async_queue: queue.Queue | None = queue.Queue() if self._write_frequency == "async" else None
        self._async_thread: threading.Thread | None = None
        self._async_thread_lock = threading.Lock()
        # Set by shutdown/stop_async_writer: no new threads after the join, late saves flush inline.
        self._shutting_down = False

    @property
    def engram(self) -> Engram:
        """The Engram client, refreshing a near-expiry OAuth token in place. Always goes through
        ``get_engram_client`` WITH this manager's bound config: a long session can't outlive its
        1h access token, and daemon threads can't see the ambient ContextVar profile, so a bare
        ``get_engram_client()`` would migrate them onto the first-built profile.

        See #69123, #74065.
        """
        self._engram = get_engram_client(self._config)
        return self._engram

    # ----- SDK object caches (generation-guarded against client rebuilds) -----

    def _cached_sdk_object(self, cache: dict[str, Any], key: str, fetch: Any) -> Any:
        """Get-or-fetch from ``cache``; a fetch that straddles a client rebuild is not cached."""
        while True:
            with self._cache_lock:
                if key in cache:
                    cache[key] = cache.pop(key)  # dict order is the LRU order the caps evict from
                    return cache[key]
                generation = self._client_generation
            obj = fetch()
            with self._cache_lock:
                if self._client_generation == generation:
                    return cache.setdefault(key, obj)
            # Client rebuilt mid-resolve: this object holds the discarded transport. Retry.

    def _cached_session(self, session_key: str) -> EngramSession | None:
        """The locally cached session, stamped as used so recall alone keeps it out of the idle sweep."""
        with self._cache_lock:
            session = self._cache.get(session_key)
            if session is not None:
                session.updated_at = datetime.now()
                self._cache[session_key] = self._cache.pop(session_key)
        return session

    def _sdk_session(self, session_id: str) -> Any:
        """Get or create the SDK session (cached until a client rebuild clears the cache)."""
        return self._cached_sdk_object(self._sessions_cache, session_id, lambda: self.engram.session(session_id))

    def _get_or_create_peer(self, peer_id: str) -> Any:
        """Get or create a Engram peer (one get-or-create API call, then cached)."""
        return self._cached_sdk_object(
            self._peers_cache, peer_id, lambda: self._authed_call("peer setup", lambda: self.engram.peer(peer_id)))

    # ----- Observation config (per session) -----

    def _observation_flags(self, engram_session_id: str) -> dict[str, bool]:
        """The four observation booleans for one session: the values synced from that session's
        server config once setup ran, else the config snapshot held on the manager."""
        synced = self._session_observation.get(engram_session_id)
        if synced is not None:
            return dict(synced)
        return {f"{kind}_{name}": getattr(self, f"_{kind}_{name}")
                for kind in ("user", "ai") for name in ("observe_me", "observe_others")}

    def _ai_observes_others(self, session: EngramSession) -> bool:
        """Whether the AI peer observes other peers in this session; this picks the recall observer."""
        synced = self._session_observation.get(session.engram_session_id)
        return synced["ai_observe_others"] if synced is not None else self._ai_observe_others

    # ----- Session creation -----

    def _configure_session_peers(self, session_id: str, user_peer: Any, assistant_peer: Any) -> dict[str, bool] | None:
        """add_peers with this session's observation config, then adopt the server's effective
        config (set via the Engram UI, it wins over local defaults). Returns the effective flags for
        get_or_create to store next to the cache entry, or None when auth died mid-way (already
        recorded by _authed_call)."""
        peers = (("user", user_peer), ("ai", assistant_peer))
        flags = self._observation_flags(session_id)
        synced = dict(flags)
        try:
            from engram.session import SessionPeerConfig
            peer_entries = [
                (peer, SessionPeerConfig(observe_me=flags[f"{kind}_observe_me"], observe_others=flags[f"{kind}_observe_others"]))
                for kind, peer in peers
            ]
            self._authed_call("session peer setup", lambda: self._sdk_session(session_id).add_peers(peer_entries))

            def _adopt_server_config() -> None:
                server_cfgs = self._authed_call(
                    "peer configuration read",
                    lambda: [self._sdk_session(session_id).get_peer_configuration(peer) for _, peer in peers],
                )
                for (kind, _), server_cfg in zip(peers, server_cfgs):
                    for field_name in ("observe_me", "observe_others"):
                        value = getattr(server_cfg, field_name)
                        if value is not None:
                            synced[f"{kind}_{field_name}"] = value
                logger.debug("Engram observation synced from server for session '%s': user(me=%s,others=%s) ai(me=%s,others=%s)",
                             session_id, synced["user_observe_me"], synced["user_observe_others"],
                             synced["ai_observe_me"], synced["ai_observe_others"])

            self._guarded(_adopt_server_config, None, logging.DEBUG,
                          "Engram get_peer_configuration failed (using local config): %s")
        except EngramAuthError:
            return None
        except Exception as e:
            logger.warning("Engram session '%s' add_peers failed (non-fatal): %s", session_id, e)
        return synced

    def _load_existing_messages(self, session_id: str) -> list:
        """Load prior messages via context() (one call for messages + metadata), oldest first."""
        try:
            ctx = self._authed_call(
                "session context load",
                lambda: self._sdk_session(session_id).context(summary=True, tokens=self._context_tokens))
            existing_messages = ctx.messages or []
            if len(existing_messages) > 1:
                timestamps = [m.created_at for m in existing_messages if m.created_at]
                if timestamps and timestamps != sorted(timestamps):
                    logger.warning("Engram messages not chronologically ordered for session '%s', sorting", session_id)
                    existing_messages = sorted(existing_messages, key=lambda m: m.created_at or datetime.min)
            if existing_messages:
                logger.info("Engram session '%s' retrieved (%d existing messages)", session_id, len(existing_messages))
            else:
                logger.info("Engram session '%s' created (new)", session_id)
            return existing_messages
        except EngramAuthError:
            logger.warning("Engram session '%s' loaded without server context: auth failed", session_id)
        except Exception as e:
            logger.warning("Engram session '%s' loaded (failed to fetch context: %s)", session_id, e)
        return []

    def _get_or_create_engram_session(self, session_id: str, user_peer: Any, assistant_peer: Any) -> tuple[Any, list, dict[str, bool] | None]:
        """(engram_session, existing_messages, observation flags) with peers configured; a cached session
        yields no messages and the flags stored when it was configured."""
        with self._cache_lock:
            if session_id in self._sessions_cache:
                logger.debug("Engram session '%s' retrieved from cache", session_id)
                return self._sessions_cache[session_id], [], self._session_observation.get(session_id)

        self._authed_call("session setup", lambda: self._sdk_session(session_id))
        observation = self._configure_session_peers(session_id, user_peer, assistant_peer)
        existing_messages: list = self._load_existing_messages(session_id) if observation is not None else []

        with self._cache_lock:
            engram_session = self._sessions_cache.get(session_id)
        if engram_session is None:
            # A mid-init client rebuild dropped the cached session; resolve a fresh one.
            engram_session = self._authed_call("session setup", lambda: self._sdk_session(session_id))
        return engram_session, existing_messages, observation

    @staticmethod
    def _has_unsynced(session: EngramSession) -> bool:
        return any(not m.get("_synced") for m in list(session.messages))

    def _evict_session_locked(self, key: str, session: EngramSession) -> None:
        """Drop one session and every entry keyed to it. Caller holds _cache_lock."""
        del self._cache[key]
        self._sessions_cache.pop(session.engram_session_id, None)
        self._session_observation.pop(session.engram_session_id, None)
        with self._prefetch_cache_lock:
            self._context_cache.pop(key, None)

    def _enforce_cache_caps_locked(self) -> None:
        """Evict least recently used entries above the hard caps. A session with unsynced messages
        is never evicted: it is the only copy until the flush lands. Caller holds _cache_lock."""
        for key, session in list(self._cache.items()):
            if len(self._cache) <= _SESSION_CACHE_MAX_SIZE:
                break
            if not self._has_unsynced(session):
                self._evict_session_locked(key, session)
        live_ids = {s.engram_session_id for s in self._cache.values()}
        for session_id in list(self._sessions_cache):
            if len(self._sessions_cache) <= _SESSION_CACHE_MAX_SIZE:
                break
            if session_id not in live_ids:
                del self._sessions_cache[session_id]
        for session_id in [sid for sid in self._session_observation if sid not in live_ids]:
            del self._session_observation[session_id]
        live_peers = {p for s in self._cache.values() for p in (s.user_peer_id, s.assistant_peer_id)}
        for peer_id in list(self._peers_cache):
            if len(self._peers_cache) <= _PEERS_CACHE_MAX_SIZE:
                break
            if peer_id not in live_peers:
                del self._peers_cache[peer_id]
        with self._prefetch_cache_lock:
            for key in [k for k in self._context_cache if k not in self._cache]:
                del self._context_cache[key]

    def _sweep_idle_sessions_locked(self) -> int:
        """Evict sessions idle beyond _SESSION_IDLE_TTL_SECONDS together with their SDK session,
        observation flags and prefetch entries, then enforce the caps. Caller holds _cache_lock."""
        cutoff = time.time() - _SESSION_IDLE_TTL_SECONDS
        evicted = 0
        for key, session in list(self._cache.items()):
            if session.updated_at.timestamp() >= cutoff or self._has_unsynced(session):
                continue
            self._evict_session_locked(key, session)
            evicted += 1
        self._enforce_cache_caps_locked()
        return evicted

    def _maybe_sweep_idle_sessions(self) -> None:
        """Rate-limited idle sweep, run from get_or_create so no watcher thread is needed."""
        now = time.time()
        with self._cache_lock:
            if now - self._last_idle_sweep_ts < _SESSION_SWEEP_INTERVAL_SECONDS:
                return
            self._last_idle_sweep_ts = now
            evicted = self._sweep_idle_sessions_locked()
        if evicted:
            logger.info("Engram session cache idle sweep evicted %d session(s)", evicted)

    def get_or_create(self, key: str, *, user_peer_id: str | None = None) -> EngramSession:
        """Get an existing session or create a new one for ``key`` (usually channel:chat_id).
        ``user_peer_id`` replaces the resolved user peer when the session's participant is not the
        runtime user, e.g. the sender bot of an a2a session."""
        self._maybe_sweep_idle_sessions()
        if (cached := self._cached_session(key)) is not None:
            logger.debug("Local session cache hit: %s", key)
            return cached

        # Gateway sessions normally use the platform-native runtime identity so multi-user
        # bots scope memory per user; config can alias/prefix it, or pinPeerName pins all
        # identities to peerName for single-user deployments (see _resolve_user_peer_id).
        # Determine peer IDs — no lock needed (read-only, no shared state mutation). See #14984.
        user_peer_id = user_peer_id or self._resolve_user_peer_id(key)
        assistant_peer_id = self.assistant_peer_id()

        # All expensive I/O outside the lock — Engram's persistence is source of truth.
        engram_session_id = self._sanitize_id(key)
        user_peer = self._get_or_create_peer(user_peer_id)
        assistant_peer = self._get_or_create_peer(assistant_peer_id)
        _, existing_messages, observation = self._get_or_create_engram_session(engram_session_id, user_peer, assistant_peer)

        session = EngramSession(
            key=key, user_peer_id=user_peer_id, assistant_peer_id=assistant_peer_id, engram_session_id=engram_session_id,
            messages=[
                {"role": "assistant" if msg.peer_id == assistant_peer_id else "user", "content": msg.content,
                 "timestamp": msg.created_at.isoformat() if msg.created_at else "", "_synced": True}
                for msg in existing_messages
            ],
        )
        with self._cache_lock:
            self._cache[key] = session
            # Stored with the cache entry and dropped with it, so the dict can hold no orphan ids.
            if observation is not None:
                self._session_observation[engram_session_id] = observation
            self._enforce_cache_caps_locked()
        return session

    # ----- Writes -----

    def _join_observation_flags(self, engram_session_id: str) -> tuple[bool, bool]:
        """(observe_me, observe_others) for an author peer joining ``engram_session_id``: the session's
        server-synced values once setup ran, else the manager's config snapshot."""
        flags = self._observation_flags(engram_session_id)
        return flags["user_observe_me"], flags["user_observe_others"]

    def _author_peer_for_session(self, engram_session: Any, engram_session_id: str, author_peer_id: str) -> Any:
        """The author's peer, joined to the session the first time it writes.

        Joins are remembered per session, so this costs one API call per author."""
        peer = self._get_or_create_peer(author_peer_id)
        with self._cache_lock:
            if author_peer_id in self._joined_author_peers.get(engram_session_id, ()):
                return peer
        try:
            from engram.session import SessionPeerConfig
            observe_me, observe_others = self._join_observation_flags(engram_session_id)
            config = SessionPeerConfig(observe_me=observe_me, observe_others=observe_others)
            engram_session.add_peers([(peer, config)])
        except Exception as e:
            # The write still lands under the right peer. Only the membership (observe config) is missing.
            logger.debug("Engram author peer join failed for %s: %s", author_peer_id, e)
            return peer
        with self._cache_lock:
            self._joined_author_peers.setdefault(engram_session_id, set()).add(author_peer_id)
            while len(self._joined_author_peers) > _SESSION_CACHE_MAX_SIZE:
                self._joined_author_peers.pop(next(iter(self._joined_author_peers)))
        return peer
    @staticmethod
    def _trim_synced_messages(session: EngramSession) -> None:
        """Drop the oldest synced messages beyond _SESSION_MESSAGE_RETENTION. Messages are appended in
        order, so trimming from the front stops at the first unsynced one and never drops it."""
        excess = len(session.messages) - _SESSION_MESSAGE_RETENTION
        while excess > 0 and session.messages and session.messages[0].get("_synced"):
            session.messages.pop(0)
            excess -= 1

    def _flush_session(self, session: EngramSession) -> bool:
        """Write unsynced messages to Engram synchronously. The session's lock keeps the async writer and an
        exit-time flush_all() from posting the same batch."""
        with session._flush_lock:
            return self._flush_session_locked(session)

    def _flush_session_before(self, session: EngramSession, deadline: float | None) -> bool:
        """_flush_session that starts only while ``deadline`` has time left and waits for the session's lock no
        longer than that; False, with nothing sent, otherwise. An upload that has started is not interrupted: the
        SDK has no per-call timeout, so it runs to the client's HTTP timeout."""
        if deadline is None:
            self._flush_session(session)
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not session._flush_lock.acquire(timeout=remaining):
            return False
        try:
            self._flush_session(session)  # re-enters the RLock already held above
        finally:
            session._flush_lock.release()
        return True

    def _flush_session_locked(self, session: EngramSession) -> bool:
        new_messages = [m for m in session.messages if not m.get("_synced")]
        if not new_messages:
            return True

        # Resolved inside the operation so a retry after a client rebuild gets fresh objects.
        def _sync_messages() -> int:
            user_peer = self._get_or_create_peer(session.user_peer_id)
            assistant_peer = self._get_or_create_peer(session.assistant_peer_id)
            engram_session = self._sessions_cache.get(session.engram_session_id)
            if engram_session is None:
                engram_session, _, observation = self._get_or_create_engram_session(
                    session.engram_session_id, user_peer, assistant_peer)
                if observation is not None:
                    with self._cache_lock:
                        self._session_observation[session.engram_session_id] = observation
            engram_messages = []
            for m in new_messages:
                if m["role"] != "user":
                    engram_messages.append(assistant_peer.message(m["content"]))
                    continue
                author_peer_id = m.get("author_peer_id")
                peer = (self._author_peer_for_session(engram_session, session.engram_session_id, author_peer_id)
                        if author_peer_id else user_peer)
                engram_messages.append(peer.message(m["content"]))
            engram_session.add_messages(engram_messages)
            return len(engram_messages)

        try:
            logger.debug("Synced %d messages to Engram for %s", self._authed_call("message sync", _sync_messages), session.key)
            ok = True
        except Exception as e:
            logger.error("Failed to sync messages to Engram: %s", e)
            ok = False
        for msg in new_messages:
            msg["_synced"] = ok
        if ok:
            # Under the cache lock so the eviction check never iterates a list being trimmed.
            with self._cache_lock:
                self._trim_synced_messages(session)
        return ok

    def _try_flush(self, session: EngramSession, level: int, msg: str) -> bool:
        """_flush_session that logs (never raises) a failure; False when the batch didn't land."""
        try:
            if self._flush_session(session):
                return True
            logger.log(level, msg)
        except Exception as e:
            logger.log(level, msg + ": %s", e)
        return False

    def _async_writer_loop(self) -> None:
        """Background daemon thread: drains the async write queue, retrying each batch once."""
        while True:
            try:
                item = self._async_queue.get(timeout=5)
                if item is _ASYNC_SHUTDOWN:
                    break
                if not self._try_flush(item, logging.WARNING, "Engram async write failed, retrying once"):
                    if self._shutting_down:
                        # The shutdown flush is already attempting this session within its own budget.
                        logger.error("Engram async write failed while shutting down, so the batch stays unsynced")
                        continue
                    time.sleep(2)
                    self._try_flush(item, logging.ERROR, "Engram async write retry failed, dropping batch")
            except queue.Empty:
                continue
            except Exception as e:
                logger.error("Engram async writer error: %s", e)

    def _reclaim_key_locked(self, session: EngramSession) -> EngramSession | None:
        """Put a session with unsynced messages back where flush_all() looks. Returns the newer object that
        owns the key when there is one (this session's batch still needs a home), None otherwise."""
        if not self._has_unsynced(session):
            return None
        current = self._cache.get(session.key)
        if current is None:
            self._cache[session.key] = session
        return None if current is None or current is session else current

    def _retain_for_retry(self, session: EngramSession) -> None:
        """An evicted key takes the session back; a key a newer object owns keeps that object, and this one
        waits in the retry list."""
        with self._cache_lock:
            if self._reclaim_key_locked(session) is not None and not any(s is session for s in self._retry_sessions):
                self._retry_sessions.append(session)

    def _keep_until_flushed(self, session: EngramSession) -> None:
        """Like _retain_for_retry, but when a newer object owns the key this batch is written now."""
        with self._cache_lock:
            owner = self._reclaim_key_locked(session)
        if owner is not None:
            self._flush_now(session)

    def _flush_now(self, session: EngramSession) -> None:
        """A save-time flush whose failed batch stays reachable for flush_all(), even after an eviction."""
        if not self._flush_session(session):
            self._retain_for_retry(session)

    def save(self, session: EngramSession) -> None:
        """Save messages per write_frequency: "async" enqueues for the background thread, "turn"
        flushes now, "session" defers until flush_all(), int N flushes every N turns."""
        self._turn_counter += 1
        wf = self._write_frequency
        if wf == "async" and self._async_queue is not None:
            # Under the writer lock, so a put cannot slip in after stop_async_writer() drained the queue.
            with self._async_thread_lock:
                if not self._shutting_down:
                    self._ensure_async_writer_locked()
                    self._async_queue.put(session)
                    return
            self._flush_now(session)
        elif self._shutting_down or wf == "turn" or (isinstance(wf, int) and wf > 0 and self._turn_counter % wf == 0):
            self._flush_now(session)
        else:
            self._keep_until_flushed(session)

    def flush_all(self, timeout: float | None = None) -> None:
        """Flush unsynced messages for all cached sessions, then drain the async queue inline. ``timeout`` bounds
        when a flush may start and how long it waits for a session's lock, not an upload already in flight, which
        runs to the client's HTTP timeout. A session skipped keeps its messages and is counted in one warning."""
        deadline = None if timeout is None else time.monotonic() + timeout
        skipped = self._flush_cached_before(deadline)
        skipped.extend(self._drain_async_queue(deadline))
        self._warn_unsynced(skipped, timeout)

    def _flush_cached_before(self, deadline: float | None) -> list[EngramSession]:
        """Flush every cached and retry-listed session that ``deadline`` allows; returns the ones it did not."""
        with self._cache_lock:
            sessions = list(self._cache.values())
            sessions += [s for s in self._retry_sessions if not any(s is c for c in sessions)]
        skipped: list[EngramSession] = []
        for session in sessions:
            try:
                if not self._flush_session_before(session, deadline):
                    skipped.append(session)
            except Exception as e:
                logger.error("Engram flush_all error for %s: %s", session.key, e)
        with self._cache_lock:
            self._retry_sessions = [s for s in self._retry_sessions if self._has_unsynced(s)]
        return skipped

    def _warn_unsynced(self, skipped: list[EngramSession], timeout: float | None) -> None:
        left = [s for s in {id(s): s for s in skipped}.values() if self._has_unsynced(s)]
        if left:
            unsynced = sum(1 for s in left for m in list(s.messages) if not m.get("_synced"))
            logger.warning("Engram flush ran out of time after %.1fs with %d message(s) in %d session(s) still unsynced",
                           timeout or 0.0, unsynced, len(left))

    def _drain_async_queue(self, deadline: float | None = None) -> list[EngramSession]:
        """Flush every queued session inline. Returns the sessions ``deadline`` left unflushed."""
        skipped: list[EngramSession] = []
        if self._async_queue is None:
            return skipped
        while not self._async_queue.empty():
            try:
                item = self._async_queue.get_nowait()
            except queue.Empty:
                break
            if item is not _ASYNC_SHUTDOWN and not self._flush_session_before(item, deadline):
                skipped.append(item)
        return skipped

    def _ensure_async_writer_locked(self) -> None:
        if self._async_thread is None or not self._async_thread.is_alive():
            self._async_thread = spawn_context_thread(self._async_writer_loop, name="engram-async-writer", owner=self)
            self._async_thread.start()

    def stop_async_writer(self, timeout: float = 10.0) -> None:
        """Join the async writer, then drain whatever was queued before the join, both within ``timeout``.
        saveMessages: false never enqueues, so the drain is a no-op there and the exit stays clean."""
        self._warn_unsynced(self._stop_async_writer_before(time.monotonic() + timeout), timeout)

    def _stop_async_writer_before(self, deadline: float) -> list[EngramSession]:
        """Join the writer for what is left of ``deadline``, then drain the queue under the same deadline. A writer
        still inside an upload keeps running to the client's HTTP timeout; it holds the shared client, so it is
        joined, never abandoned."""
        with self._async_thread_lock:
            self._shutting_down = True
        if self._async_queue is not None and self._async_thread is not None and self._async_thread.is_alive():
            self._async_queue.put(_ASYNC_SHUTDOWN)
            self._async_thread.join(timeout=max(0.0, deadline - time.monotonic()))
        return self._drain_async_queue(deadline)

    def shutdown(self, timeout: float = 10.0) -> None:
        """Flush everything, then stop the async writer thread, within ``timeout``. The budget stops new uploads
        from starting and bounds the lock waits and the join; an upload already in flight runs to the client's
        HTTP timeout. Whatever stayed unsynced is counted in one warning."""
        with self._async_thread_lock:
            self._shutting_down = True
        if self._async_queue is not None:
            deadline = time.monotonic() + timeout
            skipped = self._flush_cached_before(deadline)
            skipped.extend(self._drain_async_queue(deadline))
            skipped.extend(self._stop_async_writer_before(deadline))
            self._warn_unsynced(skipped, timeout)

    # ----- Prefetch cache -----

    def prefetch_context(self, session_key: str, user_message: str | None = None) -> None:
        """Fire get_prefetch_context in a background thread; consumed next turn via pop_context_result().
        No-op once shutdown began, so nothing is left running after the join."""
        if self._shutting_down:
            return

        def _run():
            result = self.get_prefetch_context(session_key, user_message)
            if result:
                self.set_context_result(session_key, result)

        spawn_context_thread(_run, name="engram-context-prefetch", owner=self).start()

    def set_context_result(self, session_key: str, result: dict[str, str]) -> None:
        """Store a prefetched context result in a thread-safe way."""
        if not result:
            return
        with self._prefetch_cache_lock:
            self._context_cache[session_key] = result

    def pop_context_result(self, session_key: str) -> dict[str, str]:
        """Return and clear the cached context result ({} if none ready yet)."""
        with self._prefetch_cache_lock:
            return self._context_cache.pop(session_key, {})


# ---- BEGIN PLUGIN-COMPAT (revert-scheduled; see COMPAT_MANIFEST.md) ----
# Names external plugins imported from this module before the Sep 2026 decomposition.
# Internal code MUST NOT use these (scripts/check_compat_pointers.py fails CI if it does).
# The whole block is removed by reverting the commit that added it.
from typing import Callable  # noqa: F401,E402
from pathlib import Path  # noqa: F401,E402
import hashlib  # noqa: F401,E402
import re  # noqa: F401,E402
# ---- END PLUGIN-COMPAT ----
