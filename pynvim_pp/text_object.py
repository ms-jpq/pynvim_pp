from dataclasses import dataclass
from itertools import takewhile
from typing import AbstractSet, MutableSequence


def is_word(unifying_chars: AbstractSet[str], chr: str) -> bool:
    return chr.isalnum() or chr in unifying_chars


@dataclass(frozen=True)
class SplitCtx:
    lhs: str
    rhs: str
    word_lhs: str
    word_rhs: str
    syms_lhs: str
    syms_rhs: str
    ws_lhs: str
    ws_rhs: str


def gen_split(unifying_chars: AbstractSet[str], lhs: str, rhs: str) -> SplitCtx:
    word_lhs: MutableSequence[str] = []
    syms_lhs: MutableSequence[str] = []
    word_rhs: MutableSequence[str] = []
    syms_rhs: MutableSequence[str] = []

    encountered_sym = False
    for char in reversed(lhs):
        is_w = is_word(unifying_chars, chr=char)
        if char.isspace():
            break
        elif encountered_sym:
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
        is_w = is_word(unifying_chars, chr=char)
        if char.isspace():
            break
        elif encountered_sym:
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

    w_lhs, w_rhs = "".join(reversed(word_lhs)), "".join(word_rhs)

    ws_lhs = "".join(reversed(tuple(takewhile(lambda c: c.isspace(), reversed(lhs)))))
    ws_rhs = "".join(takewhile(lambda c: c.isspace(), rhs))

    ctx = SplitCtx(
        lhs=lhs,
        rhs=rhs,
        word_lhs=w_lhs,
        word_rhs=w_rhs,
        syms_lhs="".join(reversed(syms_lhs)) + w_lhs,
        syms_rhs=w_rhs + "".join(syms_rhs),
        ws_lhs=ws_lhs,
        ws_rhs=ws_rhs,
    )
    return ctx
