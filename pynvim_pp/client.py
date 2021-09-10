from abc import abstractmethod
from asyncio.events import AbstractEventLoop
from asyncio.tasks import run_coroutine_threadsafe
from concurrent.futures import Executor
from os import getpid, getppid, kill
from queue import SimpleQueue
from signal import SIGTERM
from string import Template
from textwrap import dedent
from time import sleep
from typing import Any, Awaitable, MutableMapping, Protocol, Sequence

from pynvim import Nvim

from .logging import log, with_suppress
from .rpc import RpcCallable, RpcMsg, nil_handler


class Client(Protocol):
    @abstractmethod
    def __init__(self, pool: Executor) -> None:
        ...

    @abstractmethod
    def on_msg(self, nvim: Nvim, msg: RpcMsg) -> Any:
        ...

    @abstractmethod
    def wait(self, nvim: Nvim) -> int:
        ...


def _on_err(name: str, args: Sequence[Any], error: Exception) -> None:
    tpl = """
    ERROR IN RPC FOR :: ${name} :: ${args}
    ${error}
    """
    msg = Template(dedent(tpl)).substitute(name=name, args=args, error=error)
    log.exception("%s", msg)


class BasicClient(Client):
    def __init__(self, pool: Executor) -> None:
        self._pool = pool
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
                    _on_err(name, args=args, error=e)

        fut = run_coroutine_threadsafe(forever(), loop=loop)
        return fut.result()


def run_client(nvim: Nvim, pool: Executor, client: Client) -> int:
    def on_rpc(name: str, args: Sequence[Sequence[Any]]) -> Any:
        try:
            return client.on_msg(nvim, (name, args))
        except Exception as e:
            _on_err(name, args=args, error=e)

    @with_suppress()
    def main() -> int:
        return client.wait(nvim)

    @with_suppress()
    def forever1() -> None:
        nvim.run_loop(
            err_cb=lambda err: log.error("%s", err),
            notification_cb=on_rpc,
            request_cb=on_rpc,
        )

    @with_suppress()
    def forever2() -> None:
        ppid = getppid()
        while True:
            sleep(1)
            if getppid() != ppid:
                kill(getpid(), SIGTERM)

    pool.submit(forever1)
    pool.submit(forever2)
    return main()
