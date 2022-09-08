from __future__ import annotations

from typing import Sequence, cast

from .buffer import Buffer
from .types import Ext, HasLocalCall, NoneType, NvimPos


class Window(Ext, HasLocalCall):
    prefix = "nvim_win"

    @classmethod
    async def list(cls) -> Sequence[Window]:
        return cast(
            Sequence[Window], await cls.api.list_wins(NoneType, prefix=cls.base_prefix)
        )

    @classmethod
    async def get_current(cls) -> Window:
        return await cls.api.get_current_win(Window, prefix=cls.base_prefix)

    @classmethod
    async def set_current(cls, win: Window) -> None:
        await cls.api.set_current_win(NoneType, win, prefix=cls.base_prefix)

    async def close(self) -> None:
        await self.api.close(NoneType, self, True)

    async def get_buf(self) -> Buffer:
        return await self.api.get_buf(Buffer, self)

    async def set_buf(self, buf: Buffer) -> None:
        await self.api.set_buf(NoneType, self, buf)

    async def get_cursor(self) -> NvimPos:
        row, col = cast(NvimPos, await self.api.get_cursor(NoneType, self))
        return row - 1, col

    async def set_cursor(self, row: int, col: int) -> None:
        await self.api.set_cursor(NoneType, self, (row + 1, col))
