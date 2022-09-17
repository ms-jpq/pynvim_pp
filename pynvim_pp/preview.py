from typing import Optional, Sequence, Tuple

from .atomic import Atomic
from .buffer import Buffer
from .tabpage import Tabpage
from .types import NoneType
from .window import Window


async def preview_windows(tab: Optional[Tabpage] = None) -> Sequence[Window]:
    tab = tab or await Tabpage.get_current()
    wins = await tab.list_wins()
    atomic = Atomic()
    for win in wins:
        atomic.win_get_option(win, "previewwindow")

    prv = await atomic.commit(bool)
    previews = tuple(win for win, preview in zip(wins, prv) if preview)
    return previews


async def _open_preview() -> Tuple[Window, Buffer]:
    if win := next(iter(await preview_windows(None)), None):
        with Atomic() as (atomic, ns):
            atomic.set_current_win(win)
            ns.buf = atomic.win_get_buf(win)
            await atomic.commit(NoneType)
        buf = ns.buf(Buffer)
        return win, buf
    else:
        with Atomic() as (atomic, ns):
            atomic.command("new")
            ns.height = atomic.get_option("previewheight")
            ns.win = atomic.get_current_win()
            await atomic.commit(NoneType)

        height = ns.height(int)
        win = ns.win(Window)

        with Atomic() as (atomic, ns):
            ns.buf = atomic.win_get_buf(win)
            atomic.win_set_option(win, "previewwindow", True)
            atomic.win_set_height(win, height)
            await atomic.commit(NoneType)

        buf = ns.buf(Buffer)
        await buf.opts.set("bufhidden", "wipe")
        return win, buf


async def buf_set_preview(buf: Buffer, syntax: str, preview: Sequence[str]) -> None:
    atomic = Atomic()
    atomic.buf_set_option(buf, "undolevels", -1)
    atomic.buf_set_option(buf, "buftype", "nofile")
    atomic.buf_set_option(buf, "modifiable", True)
    atomic.buf_set_lines(buf, 0, -1, True, preview)
    atomic.buf_set_option(buf, "modifiable", False)
    atomic.buf_set_option(buf, "syntax", syntax)
    await atomic.commit(NoneType)


async def set_preview(syntax: str, preview: Sequence[str]) -> Buffer:
    _, buf = await _open_preview()
    await buf_set_preview(buf=buf, syntax=syntax, preview=preview)
    return buf
