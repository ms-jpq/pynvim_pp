from logging import ERROR, WARN, Handler, LogRecord, getLogger
from os import linesep
from pathlib import Path

from pynvim import Nvim

log = getLogger(Path(__file__).resolve().parent.name)
log.setLevel(WARN)


def nvim_handler(nvim: Nvim) -> Handler:
    class NvimHandler(Handler):
        def handle(self, record: LogRecord) -> None:
            msg = self.format(record) + linesep

            if record.levelno >= ERROR:
                nvim.async_call(nvim.err_write, msg)
            else:
                nvim.async_call(nvim.out_write, msg)

    return NvimHandler()
