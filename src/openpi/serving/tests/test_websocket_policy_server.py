import asyncio
import concurrent.futures
import contextlib
import socket
import threading
import time
import urllib.parse

from openpi_client import base_policy as _base_policy
from openpi_client import msgpack_numpy
import pytest
import websockets.sync.client

from openpi.serving import websocket_policy_server


class SlowPolicy(_base_policy.BasePolicy):
    """Sleeps in `infer` and records how many calls overlap."""

    def __init__(self, infer_s: float) -> None:
        self._infer_s = infer_s
        self._lock = threading.Lock()
        self._running = 0
        self.max_running = 0

    def infer(self, obs: dict) -> dict:
        with self._lock:
            self._running += 1
            self.max_running = max(self.max_running, self._running)
        time.sleep(self._infer_s)
        with self._lock:
            self._running -= 1
        return {"echo": obs["value"]}


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextlib.contextmanager
def _serving(policy: _base_policy.BasePolicy, warmup_obs: dict | None = None):
    port = _free_port()
    server = websocket_policy_server.WebsocketPolicyServer(policy, host="127.0.0.1", port=port, warmup_obs=warmup_obs)
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    serving = asyncio.run_coroutine_threadsafe(server.run(), loop)
    try:
        yield f"ws://127.0.0.1:{port}"
    finally:
        serving.cancel()
        concurrent.futures.wait([serving], timeout=5)
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=5)
        loop.close()


# The websockets client keepalive at a small scale: its default is 20 s and 20 s, and a 40 s compile exceeds it.
CLIENT_PING_INTERVAL_S = 0.2
CLIENT_PING_TIMEOUT_S = 0.2


def _connect(uri: str, *, keepalive: bool = True) -> websockets.sync.client.ClientConnection:
    ping_interval = CLIENT_PING_INTERVAL_S if keepalive else None
    deadline = time.monotonic() + 5
    while True:
        try:
            connection = websockets.sync.client.connect(
                uri, compression=None, max_size=None, ping_interval=ping_interval, ping_timeout=CLIENT_PING_TIMEOUT_S
            )
        except ConnectionRefusedError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.05)
            continue
        msgpack_numpy.unpackb(connection.recv())  # The server sends its metadata first.
        return connection


def _infer(connection: websockets.sync.client.ClientConnection, value: int) -> dict:
    connection.send(msgpack_numpy.Packer().pack({"value": value}))
    return msgpack_numpy.unpackb(connection.recv())


def test_a_slow_infer_keeps_a_client_with_keepalive_connected():
    with _serving(SlowPolicy(infer_s=1.0)) as uri, _connect(uri) as connection:
        assert _infer(connection, 7)["echo"] == 7
        assert _infer(connection, 8)["echo"] == 8


def test_infer_calls_from_two_clients_run_one_at_a_time():
    policy = SlowPolicy(0.3)
    # No keepalive: this test checks only that the calls do not overlap.
    with (
        _serving(policy) as uri,
        _connect(uri, keepalive=False) as first,
        _connect(uri, keepalive=False) as second,
        concurrent.futures.ThreadPoolExecutor(max_workers=2) as clients,
    ):
        answers = list(clients.map(_infer, [first, second], [1, 2]))
    assert [answer["echo"] for answer in answers] == [1, 2]
    assert policy.max_running == 1


class FirstCallPolicy(_base_policy.BasePolicy):
    """Holds its first `infer` for `first_call_s`, or until `release` is set, and records each observation."""

    def __init__(self, first_call_s: float) -> None:
        self._first_call_s = first_call_s
        self.first_call_started = threading.Event()
        self.release = threading.Event()
        self.observations: list[dict] = []

    def infer(self, obs: dict) -> dict:
        self.observations.append(obs)
        if len(self.observations) == 1:
            self.first_call_started.set()
            self.release.wait(timeout=self._first_call_s)
        return {"echo": obs["value"]}


def test_the_server_listens_only_after_the_warm_up_inference_returns():
    policy = FirstCallPolicy(first_call_s=5.0)
    with _serving(policy, warmup_obs={"value": 0}) as uri:
        assert policy.first_call_started.wait(timeout=5)
        with pytest.raises(ConnectionRefusedError):
            socket.create_connection(("127.0.0.1", urllib.parse.urlsplit(uri).port), timeout=1)
        policy.release.set()
        with _connect(uri) as connection:
            assert _infer(connection, 7)["echo"] == 7
    assert [obs["value"] for obs in policy.observations] == [0, 7]


def test_a_client_with_keepalive_gets_a_fast_first_answer_after_the_warm_up():
    with (
        _serving(FirstCallPolicy(first_call_s=1.0), warmup_obs={"value": 0}) as uri,
        _connect(uri) as connection,
    ):
        answer = _infer(connection, 7)
    assert answer["echo"] == 7
    assert answer["server_timing"]["infer_ms"] < 500
