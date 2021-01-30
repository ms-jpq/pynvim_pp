from dataclasses import dataclass
from typing import AbstractSet, MutableSequence


def is_word(c: str, unifying_chars: AbstractSet[str]) -> bool:
    return c.isalnum() or c in unifying_chars


@dataclass(frozen=True)
class SplitCtx:
    lhs: str
    rhs: str
    word_lhs: str
    word_rhs: str
    syms_lhs: str
    syms_rhs: str


def gen_split(lhs: str, rhs: str, unifying_chars: AbstractSet[str]) -> SplitCtx:
    word_lhs: MutableSequence[str] = []
    syms_lhs: MutableSequence[str] = []
    word_rhs: MutableSequence[str] = []
    syms_rhs: MutableSequence[str] = []

    encountered_sym = False
    for char in reversed(lhs):
        is_w = is_word(char, unifying_chars=unifying_chars)
        if encountered_sym:
            if is_w:
                break
            else:
                syms_lhs.append(char)
        else:
            if is_w:
                word_lhs.append(char)
            else:
                syms_lhs.append(char)
                encountered_sym = True

    encountered_sym = False
    for char in rhs:
        is_w = is_word(char, unifying_chars=unifying_chars)
        if encountered_sym:
            if is_w:
                break
            else:
                syms_rhs.append(char)
        else:
            if is_w:
                word_rhs.append(char)
            else:
                syms_rhs.append(char)
                encountered_sym = True

    ctx = SplitCtx(
        lhs=lhs,
        rhs=rhs,
        word_lhs="".join(reversed(word_lhs)),
        word_rhs="".join(word_rhs),
        syms_lhs="".join(reversed(syms_lhs)),
        syms_rhs="".join(syms_rhs),
    )
    return ctx
