from typing import FrozenSet, MutableSequence, Tuple

from .grapheme import Grapheme, join


def is_word(c: Grapheme, unifying_chars: FrozenSet[Grapheme]) -> bool:
    return str(c).isalnum() or c in unifying_chars


def gen_lhs_rhs(
    line: str, col: int, unifying_chars: FrozenSet[str]
) -> Tuple[Tuple[str, str], Tuple[str, str]]:
    glyphs = Grapheme(line)
    unifying = frozenset(Grapheme(char) for char in unifying_chars)
    before, after = reversed(glyphs[:col]), iter(glyphs[col:])

    words_lhs: MutableSequence[Grapheme] = []
    syms_lhs: MutableSequence[Grapheme] = []
    words_rhs: MutableSequence[Grapheme] = []
    syms_rhs: MutableSequence[Grapheme] = []

    encountered_sym = False
    for char in before:
        is_w = is_word(char, unifying_chars=unifying)
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
        is_w = is_word(char, unifying_chars=unifying)
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

    words = join("", reversed(words_lhs)), join("", words_rhs)
    syms = join("", reversed(syms_lhs)), join("", syms_rhs)
    return words, syms
