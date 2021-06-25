from abc import abstractmethod
from asyncio.events import AbstractEventLoop
from asyncio.tasks import run_coroutine_threadsafe
from os import getpid, getppid, kill
from queue import SimpleQueue
from signal import SIGKILL
from threading import Thread
from time import sleep
from typing import Any, Awaitable, MutableMapping, Protocol, Sequence, TypeVar

from pynvim import Nvim

from .consts import linesep
from .logging import log
from .rpc import RpcCallable, nil_handler

T = TypeVar("T")

from .rpc import RpcMsg


class Client(Protocol):
    @abstractmethod
    def on_msg(self, nvim: Nvim, msg: RpcMsg) -> Any:
        ...

    @abstractmethod
    def wait(self, nvim: Nvim) -> int:
        ...


class BasicClient(Client):
    def __init__(self) -> None:
        self._handlers: MutableMapping[str, RpcCallable] = {}
        self._q: SimpleQueue = SimpleQueue()

    def on_msg(self, nvim: Nvim, msg: RpcMsg) -> Any:
        name, (args, *_) = msg
        handler = self._handlers.get(name, nil_handler(name))
        ret = handler(nvim, *args)
        if isinstance(ret, Awaitable):
            self._q.put((name, args, ret))
            return None
        else:
            return ret

    def wait(self, nvim: Nvim) -> int:
        loop: AbstractEventLoop = nvim.loop

        async def forever() -> int:
            while True:
                name, args, aw = await loop.run_in_executor(None, self._q.get)
                try:
                    await aw
                except Exception as e:
                    fmt = f"ERROR IN RPC FOR: %s - %s{linesep}%s"
                    log.exception(fmt, name, args, e)

        fut = run_coroutine_threadsafe(forever(), loop=loop)
        return fut.result()


def _exit() -> None:
    kill(getpid(), SIGKILL)


def run_client(nvim: Nvim, client: Client) -> int:
    def on_rpc(name: str, args: Sequence[Sequence[Any]]) -> Any:
        try:
            return client.on_msg(nvim, (name, args))
        except Exception as e:
            fmt = f"ERROR IN RPC FOR: %s - %s{linesep}%s"
            log.exception(fmt, name, args, e)

    def main() -> int:
        return client.wait(nvim)

    def forever1() -> None:
        nvim.run_loop(
            err_cb=lambda err: log.error("%s", err),
            notification_cb=on_rpc,
            request_cb=on_rpc,
        )

    def forever2() -> None:
        while True:
            sleep(1)
            if getppid() == 1:
                _exit()

    Thread(target=forever1, daemon=True).start()
    Thread(target=forever2, daemon=True).start()
    return main()

