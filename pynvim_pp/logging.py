from contextlib import contextmanager
from logging import WARN, StreamHandler, getLogger
from pathlib import Path
from time import monotonic
from typing import Any, Iterator

from pynvim import Nvim

from .lib import write

log = getLogger(Path(__file__).resolve().parent.name)
log.addHandler(StreamHandler())
log.setLevel(WARN)


@contextmanager
def bench(nvim: Nvim, *args: Any) -> Iterator[None]:
    t1 = monotonic()
    yield None
    t2 = monotonic()
    write(nvim, *args, t2 - t1)
