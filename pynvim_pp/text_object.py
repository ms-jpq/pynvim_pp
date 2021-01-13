from typing import FrozenSet, MutableSequence, Tuple

from .grapheme import break_into, grapheme, join


def is_word(c: grapheme, unifying_chars: FrozenSet[grapheme]) -> bool:
    return c.isalnum() or c in unifying_chars


def gen_lhs_rhs(
    line: str, col: int, unifying_chars: FrozenSet[grapheme]
) -> Tuple[Tuple[str, str], Tuple[str, str]]:
    graphemes = tuple(break_into(line))
    before, after = reversed(graphemes[:col]), iter(graphemes[col:])

    words_lhs: MutableSequence[grapheme] = []
    syms_lhs: MutableSequence[grapheme] = []
    words_rhs: MutableSequence[grapheme] = []
    syms_rhs: MutableSequence[grapheme] = []

    encountered_sym = False
    for char in before:
        is_w = is_word(char, unifying_chars=unifying_chars)
        if encountered_sym:
            if is_w:
                break
            else:
                syms_lhs.append(char)
        else:
            if is_w:
                words_lhs.append(char)
            else:
                syms_lhs.append(char)
                encountered_sym = True

    encountered_sym = False
    for char in after:
        is_w = is_word(char, unifying_chars=unifying_chars)
        if encountered_sym:
            if is_w:
                break
            else:
                syms_rhs.append(char)
        else:
            if is_w:
                words_rhs.append(char)
            else:
                syms_rhs.append(char)
                encountered_sym = True

    words = join(reversed(words_lhs)), join(words_rhs)
    syms = join(reversed(syms_lhs)), join(syms_rhs)
    return words, syms
