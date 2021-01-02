from contextlib import contextmanager
from typing import Iterator, Optional

from pynvim import Nvim
from pynvim.api import Window


@contextmanager
def hold_win_pos(nvim: Nvim, win: Optional[Window] = None) -> Iterator[None]:
    win = win or nvim.api.get_current_win()
    try:
        yield None
    finally:
        nvim.api.set_current_win(win)
