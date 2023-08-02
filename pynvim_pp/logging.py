from contextlib import contextmanager
from logging import ERROR, WARN, LogRecord, StreamHandler, captureWarnings, getLogger
from sys import stdout
from typing import Iterator

log = getLogger()


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
captureWarnings(True)


@contextmanager
def suppress_and_log() -> Iterator[None]:
    try:
        yield None
    except Exception as e:
        log.exception("%s", e)
