from contextlib import contextmanager
from logging import ERROR, WARN, LogRecord, StreamHandler, getLogger
from pathlib import Path
from sys import stdout
from typing import Iterator

log = getLogger(Path(__file__).resolve(strict=True).parent.name)


class _Handler(StreamHandler):
    def handle(self, record: LogRecord) -> bool:
        if record.levelno <= WARN:
            return super().handle(record)
        else:
            return False


_log = _Handler(stream=stdout)
_err = StreamHandler()
_err.setLevel(ERROR)


log.addHandler(_log)
log.addHandler(_err)
log.setLevel(WARN)


@contextmanager
def suppress_and_log() -> Iterator[None]:
    try:
        yield None
    except Exception as e:
        log.exception("%s", e)
