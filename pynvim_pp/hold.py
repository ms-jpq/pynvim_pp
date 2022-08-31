from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from .window import Window


@asynccontextmanager
async def hold_win(win: Optional[Window]) -> AsyncIterator[Window]:
    win = win or await Window.get_current()
    try:
        yield win
    finally:
        await Window.set_current(win)
