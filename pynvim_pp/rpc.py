from asyncio import Future, Queue, gather, get_event_loop, open_unix_connection
from contextlib import asynccontextmanager
from enum import Enum, unique
from functools import wraps
from itertools import count
from pathlib import PurePath
from typing import (
    Any,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    MutableMapping,
    Sequence,
    cast,
)

from msgpack import Packer, Unpacker

from .logging import log
from .types import Callback, RPClient


@unique
class _MsgType(Enum):
    req = 0
    resp = 1
    notif = 2


_RX_Q = MutableMapping[int, Future]
_NOTIFS = MutableMapping[str, Callable[..., Awaitable[None]]]
_RESPS = MutableMapping[str, Callable[[int, Sequence[Any]], Awaitable[Any]]]

_LIMIT = 10**10


async def _connect(
    socket: PurePath,
    tx: AsyncIterable[Any],
    rx: Callable[[AsyncIterator[Any]], Awaitable[None]],
) -> None:
    packer, unpacker = Packer(), Unpacker()
    reader, writer = await open_unix_connection(socket, limit=_LIMIT)

    async def send() -> None:
        async for frame in tx:
            if frame is None:
                await writer.drain()
            else:
                writer.write(packer.pack(frame))

    async def recv() -> AsyncIterator[Any]:
        while data := await reader.read(_LIMIT):
            unpacker.feed(data)
            for frame in unpacker:
                yield frame

    await gather(rx(recv()), send())


class RPCError(Exception):
    ...


class _RPClient(RPClient):
    def __init__(self, tx: Queue, rx: _RX_Q, notifs: _NOTIFS, resps: _RESPS) -> None:
        self._loop, self._uids = get_event_loop(), count()
        self._tx, self._rx = tx, rx
        self._notifs, self._resps = notifs, resps

    async def notify(self, method: str, *params: Any) -> None:
        await self._tx.put((_MsgType.notif.value, method, params))

    async def request(self, method: str, *params: Any) -> Sequence[Any]:
        uid = next(self._uids)
        fut = self._loop.create_future()
        self._rx[uid] = fut
        await self._tx.put((_MsgType.req.value, method, params))
        return cast(Sequence[Any], await fut)

    def on_notify(self, method: str, f: Callback) -> None:
        assert method not in self._notifs
        self._notifs[method] = f

    def on_request(self, method: str, f: Callback) -> None:
        assert method not in self._resps

        @wraps(f)
        async def wrapped(msg_id: int, params: Sequence[Any]) -> None:
            try:
                resp = await f(*params)
            except Exception as e:
                await self._tx.put((_MsgType.resp.value, msg_id, str(e), None))
            else:
                await self._tx.put((_MsgType.resp.value, msg_id, None, resp))

        self._resps[method] = wrapped


@asynccontextmanager
async def client(socket: PurePath) -> AsyncIterator[_RPClient]:
    tx_q: Queue = Queue(maxsize=1)
    rx_q: _RX_Q = {}
    notifs: _NOTIFS = {}
    resps: _RESPS = {}

    async def tx() -> AsyncIterator[Any]:
        while True:
            frame = await tx_q.get()
            yield frame

    async def rx(rx: AsyncIterator[Any]) -> None:
        async for frame in rx:
            assert isinstance(frame, Sequence)
            length = len(frame)
            if length == 3:
                ty, method, params = frame
                assert ty is _MsgType.notif.value
                if notif := notifs.get(method):
                    notif(*params)
                else:
                    log.warn("%s", f"No RPC listener for {method}")

            elif length == 4:
                ty, msg_id, op1, op2 = frame
                if ty is _MsgType.resp.value:
                    assert msg_id not in rx_q
                    if fut := rx_q.get(msg_id):
                        if op1:
                            fut.set_exception(RPCError(op1))
                        else:
                            fut.set_result(op2)
                    else:
                        log.warn("%s", f"Unexpected response message - {op1} | {op2}")
                elif ty is _MsgType.req.value:
                    if callback := resps.get(op1):
                        callback(msg_id, op2)
                    else:
                        log.warn("%s", f"No RPC listener for {op1}")
                else:
                    assert False

    conn = _connect(socket, tx=tx(), rx=rx)
    client = _RPClient(tx=tx_q, rx=rx_q, notifs=notifs, resps=resps)
    yield client
    await conn
