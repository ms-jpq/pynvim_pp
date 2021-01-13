from __future__ import annotations

from typing import Any, Iterable, Iterator, NewType, Sequence, Union, cast

grapheme = NewType("grapheme", str)


def new(string: str) -> Sequence[grapheme]:
    return tuple(map(grapheme, string))


def join(
    sep: Union[str, grapheme, Grapheme],
    glyphs: Iterable[Union[str, grapheme, Grapheme]],
) -> str:
    return str(sep).join(map(str, glyphs))


class Grapheme:
    def __init__(
        self, glyphs: Union[str, grapheme, Sequence[grapheme], Grapheme]
    ) -> None:
        if isinstance(glyphs, str):
            self._body = new(glyphs)
        elif isinstance(glyphs, Sequence):
            self._body = cast(Sequence[grapheme], glyphs)
        elif isinstance(glyphs, Grapheme):
            self._body = glyphs._body
        else:
            raise ValueError(glyphs)

    def __len__(self) -> int:
        return len(self._body)

    def __eq__(self, x: Any) -> bool:
        if isinstance(x, Grapheme):
            return self._body == x._body
        else:
            return False

    def __hash__(self) -> int:
        return hash(self._body)

    def __contains__(self, x: Any) -> bool:
        return x in self._body

    def __iter__(self) -> Iterator[Grapheme]:
        return (Grapheme((g,)) for g in self._body)

    def __reversed__(self) -> Iterator[Grapheme]:
        return (Grapheme((g,)) for g in reversed(self._body))

    def __str__(self) -> str:
        return join("", self._body)

    def __getitem__(self, index: Union[int, slice]) -> Grapheme:
        glyph = self._body.__getitem__(index)
        if isinstance(glyph, Sequence):
            return Grapheme(glyph)
        else:
            return Grapheme((glyph,))
