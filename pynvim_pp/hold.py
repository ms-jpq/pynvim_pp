from contextlib import contextmanager
from typing import Iterator, Optional

from pynvim import Nvim
from pynvim.api import Window

from .api import cur_win, set_cur_win


@contextmanager
def hold_win_pos(nvim: Nvim, win: Optional[Window] = None) -> Iterator[None]:
    win = win or cur_win(nvim)
    try:
        yield None
    finally:
        set_cur_win(nvim, win)
