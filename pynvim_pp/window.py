from __future__ import annotations

from typing import NewType, Sequence, Tuple, cast

from .buffer import Buffer
from .rpc_types import MsgPackWindow
from .types import HasVOL, NoneType, NvimPos

WinNum = NewType("WinNum", int)


class Window(MsgPackWindow, HasVOL):
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

    async def get_number(self) -> WinNum:
        return WinNum(await self.api.get_number(int, self))

    async def get_buf(self) -> Buffer:
        return await self.api.get_buf(Buffer, self)

    async def set_buf(self, buf: Buffer) -> None:
        await self.api.set_buf(NoneType, self, buf)

    async def get_cursor(self) -> NvimPos:
        row, col = cast(NvimPos, await self.api.get_cursor(NoneType, self))
        return row - 1, col

    async def set_cursor(self, row: int, col: int) -> None:
        await self.api.set_cursor(NoneType, self, (row + 1, col))

    async def get_height(self) -> int:
        return await self.api.get_height(int, self)

    async def set_height(self, height: int) -> None:
        await self.api.set_height(NoneType, self, height)

    async def get_width(self) -> int:
        return await self.api.get_width(int, self)

    async def set_width(self, height: int) -> None:
        await self.api.set_width(NoneType, self, height)

    async def get_position(self) -> Tuple[int, int]:
        return cast(Tuple[int, int], await self.api.get_position(NoneType, self))
