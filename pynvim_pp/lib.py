from asyncio import get_running_loop
from os import PathLike, name
from os.path import normpath
from pathlib import Path
from string import ascii_lowercase
from typing import Iterator, Literal, Optional, Union
from unicodedata import east_asian_width
from urllib.parse import urlsplit

_UNICODE_WIDTH_LOOKUP = {
    "W": 2,  # CJK
    "N": 2,  # Non printable
}

_SPECIAL = {"\n", "\r"}

_Encoding = Literal["UTF-8", "UTF-16-LE", "UTF-32-LE"]


def encode(text: str, encoding: _Encoding = "UTF-8") -> bytes:
    return text.encode(encoding, errors="surrogateescape")


def decode(btext: bytes, encoding: _Encoding = "UTF-8") -> str:
    return btext.decode(encoding, errors="surrogateescape")


def recode(text: str) -> str:
    return text.encode("UTF-8", errors="ignore").decode("UTF-8")


def display_width(text: str, tabsize: int) -> int:
    def cont() -> Iterator[int]:
        for char in text:
            if char == "\t":
                yield tabsize
            elif char in _SPECIAL:
                yield 2
            else:
                code = east_asian_width(char)
                yield _UNICODE_WIDTH_LOOKUP.get(code, 1)

    return sum(cont())


def _expanduser(path: Path) -> Path:
    try:
        resolved = path.expanduser()
    except RuntimeError:
        return path
    else:
        return resolved


def _safe_path(path: Union[PathLike, str]) -> Optional[Path]:
    p = normpath(path)
    try:
        parsed = urlsplit(p, allow_fragments=False)
    except ValueError:
        return None
    else:
        scheme = parsed.scheme.casefold()
        if scheme in {"", "file"}:
            safe_path = Path(normpath(parsed.path))
            return safe_path
        elif name == "nt" and scheme in {*ascii_lowercase}:
            return Path(p)
        else:
            return None


async def resolve_path(
    cwd: Optional[Path], path: Union[PathLike, str]
) -> Optional[Path]:
    loop = get_running_loop()

    def cont() -> Optional[Path]:
        if not (safe_path := _safe_path(path)):
            return None
        elif safe_path.is_absolute():
            return safe_path
        elif (resolved := _expanduser(safe_path)) != safe_path:
            return resolved
        elif cwd:
            return cwd / path
        else:
            return None

    return await loop.run_in_executor(None, cont)
