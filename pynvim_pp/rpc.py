from asyncio import (
    Future,
    Queue,
    create_task,
    gather,
    get_event_loop,
    open_unix_connection,
)
from asyncio.exceptions import InvalidStateError
from contextlib import asynccontextmanager, suppress
from enum import Enum, unique
from functools import cached_property, wraps
from itertools import count
from pathlib import PurePath
from sys import version_info
from traceback import format_exc
from typing import (
    Any,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Coroutine,
    Mapping,
    MutableMapping,
    NewType,
    Optional,
    Sequence,
    Type,
)

from msgpack import ExtType, Packer, Unpacker

from .buffer import Buffer
from .logging import log
from .tabpage import Tabpage
from .types import PARENT, Chan, Ext, ExtData, Method, NvimError, RPCallable, RPClient
from .window import Window


@unique
class MsgType(Enum):
    req = 0
    resp = 1
    notif = 2


RPCdefault = Callable[[MsgType, Method, Sequence[Any]], Coroutine[Any, Any, Any]]
_MSG_ID = NewType("_MSG_ID", int)
_RX_Q = MutableMapping[_MSG_ID, Future]
_METHODS = MutableMapping[
    str, Callable[[Optional[_MSG_ID], Sequence[Any]], Coroutine[Any, Any, None]]
]

_LIMIT = 10**6


def _pack(val: Any) -> ExtType:
    if isinstance(val, Ext):
        return ExtType(val.code, val.data)
    else:
        raise TypeError()


class _Hooker:
    def __init__(self) -> None:
        self._mapping: Mapping[int, Type[Ext]] = {}

    def init(self, *exts: Type[Ext]) -> None:
        self._mapping = {cls.code: cls for cls in exts}

    def ext_hook(self, code: int, data: bytes) -> Ext:
        if cls := self._mapping.get(code):
            return cls(data=ExtData(data))
        else:
            raise RuntimeError((code, data))


def _wrap(
    tx: Queue, f: Callable[..., Awaitable[Any]]
) -> Callable[[Optional[_MSG_ID], Sequence[Any]], Coroutine[Any, Any, None]]:
    @wraps(f)
    async def wrapped(msg_id: Optional[int], params: Sequence[Any]) -> None:
        if msg_id is None:
            await f(*params)
        else:
            try:
                resp = await f(*params)
            except Exception as e:
                error = str((e, format_exc()))
                await tx.put((MsgType.resp.value, msg_id, error, None))
            else:
                await tx.put((MsgType.resp.value, msg_id, None, resp))

    return wrapped


async def _connect(
    socket: PurePath,
    tx: AsyncIterable[Any],
    rx: Callable[[AsyncIterator[Any]], Awaitable[None]],
    hooker: _Hooker,
) -> None:
    packer, unpacker = Packer(default=_pack), Unpacker(ext_hook=hooker.ext_hook)
    reader, writer = await open_unix_connection(socket)

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


class _RPClient(RPClient):
    def __init__(self, tx: Queue, rx: _RX_Q, notifs: _METHODS) -> None:
        self._loop, self._uids = get_event_loop(), map(_MSG_ID, count())
        self._tx, self._rx = tx, rx
        self._methods = notifs
        self._chan: Optional[Chan] = None

    @cached_property
    def chan(self) -> Chan:
        assert self._chan
        return self._chan

    async def notify(self, method: Method, *params: Any) -> None:
        await self._tx.put((MsgType.notif.value, method, params))

    async def request(self, method: Method, *params: Any) -> Any:
        uid = next(self._uids)
        fut = self._loop.create_future()
        self._rx[uid] = fut
        await self._tx.put((MsgType.req.value, uid, method, params))
        return await fut

    def register(self, f: RPCallable) -> None:
        assert f.method not in self._methods
        wrapped = _wrap(self._tx, f=f)
        self._methods[f.method] = wrapped


@asynccontextmanager
async def client(socket: PurePath, default: RPCdefault) -> AsyncIterator[_RPClient]:
    tx_q: Queue = Queue()
    rx_q: _RX_Q = {}
    methods: _METHODS = {}
    nil_handler = _wrap(tx_q, f=default)

    async def tx() -> AsyncIterator[Any]:
        while True:
            frame = await tx_q.get()
            yield frame
            yield None

    async def rx(rx: AsyncIterator[Any]) -> None:
        async for frame in rx:
            assert isinstance(frame, Sequence)
            length = len(frame)
            if length == 3:
                ty, method, params = frame
                assert ty == MsgType.notif.value
                if cb := methods.get(method):
                    create_task(cb(None, params))
                else:
                    create_task(nil_handler(None, (MsgType.notif, method, params)))

            elif length == 4:
                ty, msg_id, op1, op2 = frame
                if ty == MsgType.resp.value:
                    err, res = op1, op2
                    if fut := rx_q.get(msg_id):
                        with suppress(InvalidStateError):
                            if err:
                                fut.set_exception(NvimError(err))
                            else:
                                fut.set_result(res)
                    else:
                        log.warn("%s", f"Unexpected response message - {err} | {res}")
                elif ty == MsgType.req.value:
                    method, argv = op1, op2
                    if cb := methods.get(method):
                        create_task(cb(msg_id, argv))
                    else:
                        create_task(nil_handler(msg_id, (MsgType.req, method, argv)))
                else:
                    assert False

    hooker = _Hooker()
    conn = create_task(_connect(socket, tx=tx(), rx=rx, hooker=hooker))
    rpc = _RPClient(tx=tx_q, rx=rx_q, notifs=methods)

    await rpc.notify(
        Method("nvim_set_client_info"),
        PARENT.name,
        {
            "major": version_info.major,
            "minor": version_info.minor,
            "patch": version_info.micro,
        },
        "remote",
        (),
        {},
    )
    chan, meta = await rpc.request(Method("nvim_get_api_info"))

    assert isinstance(meta, Mapping)
    types = meta.get("types")
    error_info = meta.get("error_types")
    assert isinstance(types, Mapping)
    assert isinstance(error_info, Mapping)

    Buffer.init_code(code=types["Buffer"]["id"])
    Window.init_code(code=types["Window"]["id"])
    Tabpage.init_code(code=types["Tabpage"]["id"])

    rpc._chan = chan
    hooker.init(Buffer, Window, Tabpage)

    yield rpc
    await conn
