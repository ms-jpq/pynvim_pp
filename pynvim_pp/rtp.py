from itertools import chain
from locale import strxfrm
from pathlib import Path
from typing import Iterable, Iterator

from pynvim import Nvim

from .atomic import Atomic
from .lib import with_suppress


def _walk(path: Path) -> Iterator[Path]:
    for p in path.iterdir():
        if p.is_dir():
            yield from _walk(p)
        else:
            yield p


def rtp_packages(nvim: Nvim, plugins: Iterable[Path]) -> Atomic:
    atomic = Atomic()
    head, *body, tail = nvim.list_runtime_paths()
    rtp = ",".join(chain((head,), body, map(str, plugins), (tail,)))
    atomic.set_option("runtimepath", rtp)

    for path in plugins:
        plug = path / "plugin"
        if plug.exists():
            scripts = (p for p in _walk(plug) if p.suffix in {".lua", ".vim"})
            for script in sorted(scripts, key=lambda p: tuple(map(strxfrm, p.parts))):
                with with_suppress():
                    atomic.command(f"source {script}")

    return atomic
