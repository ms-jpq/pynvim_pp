from typing import Iterable, NewType, Sequence

grapheme = NewType("grapheme", str)


def break_into(string: str) -> Sequence[grapheme]:
    return tuple(map(grapheme, string))


def join(chars: Iterable[grapheme]) -> str:
    return "".join(chars)
