from __future__ import annotations

from typing import Sequence, cast

from .types import Ext, NoneType
from .window import Window


class Tabpage(Ext):
    prefix = "nvim_tabpage"

    @classmethod
    async def list(cls) -> Sequence[Tabpage]:
        return cast(Sequence[Tabpage], await cls.api.list_tabs(NoneType))

    @classmethod
    async def get_current(cls) -> Tabpage:
        return await cls.api.get_current_tabpage(Tabpage)

    @classmethod
    async def set_current(cls, tab: Tabpage) -> None:
        await cls.api.set_current_tabpage(NoneType, tab)

    async def list_wins(self) -> Sequence[Window]:
        return cast(Sequence[Window], await self.api.list_wins(NoneType, self))
