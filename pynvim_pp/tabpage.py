from __future__ import annotations

from typing import Sequence, cast

from .types import Ext, NoneType
from .window import Window


class TabPage(Ext):
    prefix = "nvim_tabpage"

    @classmethod
    async def list(cls) -> Sequence[TabPage]:
        return cast(Sequence[TabPage], await cls.api.list_tabs(NoneType))

    @classmethod
    async def get_current(cls) -> TabPage:
        return await cls.api.get_current_tabpage(TabPage)

    @classmethod
    async def set_current(cls, tab: TabPage) -> None:
        await cls.api.set_current_tabpage(NoneType, tab)

    async def list_wins(self) -> Sequence[Window]:
        return cast(Sequence[Window], await self.api.list_wins(NoneType, self))
