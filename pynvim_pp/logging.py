from logging import ERROR, WARN, StreamHandler, getLogger
from pathlib import Path
from sys import stdout

log = getLogger(Path(__file__).resolve().parent.name)

_log = StreamHandler(stream=stdout)
_err = StreamHandler()

_err.setLevel(ERROR)

log.addHandler(_log)
log.addHandler(_err)
log.setLevel(WARN)

