from typing import Iterable, Iterator, NewType

grapheme = NewType("grapheme", str)

# TODO: how do I do grapheme without dependencies?
def break_into(string: str) -> Iterator[grapheme]:
    for char in string:
        yield grapheme(char)


def join(chars: Iterable[grapheme]) -> str:
    return "".join(chars)
