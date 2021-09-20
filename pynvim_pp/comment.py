from dataclasses import dataclass
from typing import Optional
from pynvim.api import Nvim
from pynvim.api.buffer import Buffer
from .api import cur_buf, buf_get_option


@dataclass(frozen=True)
class BlockComment:
    start: str
    end: str


@dataclass(frozen=True)
class CommentStrings:
    block: Optional[BlockComment]
    line: Optional[str]


# Adopted from: https://github.com/b3nj5m1n/kommentary/blob/09d332c66b7155b14eb22c9129aee44d9d2ff496/lua/kommentary/config.lua#L37
# A language will get an explicit configuration here if the commentstring is not defined,
# or if it supports both single-line and multi-line.
# Some filetypes contain multiple "languages" (e.g., javascript react contains both
# Javascript and JSX). In such cases, we omit the languages from the list below so we
# can take advantage of any dynamic maniuplation of 'commentstring' the user might be
# doing (e.g., via this plugin: JoosepAlviste/nvim-ts-context-commentstring)
_default_comment_strings = CommentStrings(BlockComment("/*", "*/"), "// ")
COMMENT_STRINGS = {
    "c": _default_comment_strings,
    "clojure": CommentStrings(BlockComment("(comment ", " )"), ";"),
    "cpp": _default_comment_strings,
    "cs": _default_comment_strings,
    "fennel": CommentStrings(None, ";"),
    "haskell": CommentStrings(BlockComment("{-", "-}"), "--"),
    "java": _default_comment_strings,
    "javascript": _default_comment_strings,
    "kotlin": _default_comment_strings,
    "lua": CommentStrings(BlockComment("--[[", "]]"), "--"),
    "rust": _default_comment_strings,
    "sql": CommentStrings(BlockComment("/*", "*/"), "--"),
    "swift": _default_comment_strings,
    "toml": CommentStrings(None, "#"),
    "typescript": _default_comment_strings,
}


def _get_comment_strings_from_nvim_option(nvim: Nvim, buf: Buffer) -> CommentStrings:
    commentstring: Optional[str] = buf_get_option(nvim, buf, "commentstring")

    if not commentstring:
        return CommentStrings(None, None)
    parts = commentstring.split("%s")

    # This means commentstring is not something like '/*%s*/', or '//%s'
    if len(parts) != 2 or not parts[0]:
        return CommentStrings(None, None)

    first_part, second_part = parts
    if second_part:
        return CommentStrings(
            BlockComment(
                first_part,
                second_part,
            ),
            None,
        )
    else:
        return CommentStrings(None, first_part)


def get_comment_strings(nvim: Nvim) -> CommentStrings:
    # Should be something like '/*%s*/', or '//%s'
    buf = cur_buf(nvim)
    if cms := COMMENT_STRINGS.get(buf_get_option(nvim, buf, "filetype")):
        return cms
    return _get_comment_strings_from_nvim_option(nvim, buf)
