from logging import ERROR, WARN, LogRecord, StreamHandler, getLogger
from pathlib import Path
from sys import stdout

log = getLogger(Path(__file__).resolve().parent.name)


class _Handler(StreamHandler):
    def handle(self, record: LogRecord) -> None:
        if record.levelno < WARN:
            super().handle(record)


_log = _Handler(stream=stdout)
_err = StreamHandler()
_err.setLevel(ERROR)


log.addHandler(_log)
log.addHandler(_err)
log.setLevel(WARN)

