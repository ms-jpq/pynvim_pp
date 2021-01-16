from logging import WARN, StreamHandler, getLogger
from pathlib import Path

log = getLogger(Path(__file__).resolve().parent.name)
log.addHandler(StreamHandler())
log.setLevel(WARN)
