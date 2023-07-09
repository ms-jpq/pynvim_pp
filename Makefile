MAKEFLAGS += --jobs
MAKEFLAGS += --no-builtin-rules
MAKEFLAGS += --warn-undefined-variables
SHELL := bash
.DELETE_ON_ERROR:
.ONESHELL:
.SHELLFLAGS := -Eeuo pipefail -O dotglob -O nullglob -O extglob -O failglob -O globstar -c

.DEFAULT_GOAL := help

.PHONY: clean clobber lint test build fmt

clean:
	rm -rf -- .mypy_cache/

clobber: clean
	rm -rf -- .venv/

.venv/bin/python3:
	python3 -m venv -- .venv

define PYDEPS
from itertools import chain
from os import execl
from sys import executable

from tomli import load

with open("pyproject.toml", "rb") as fd:
    toml = load(fd)

project = toml["project"]
execl(
    executable,
    executable,
    "-m",
    "pip",
    "install",
    "--upgrade",
    "--",
    *project.get("dependencies", ()),
    *chain.from_iterable(project["optional-dependencies"].values()),
)
endef
export -- PYDEPS

.venv/bin/mypy: .venv/bin/python3
	'$<' -m pip install -- tomli
	'$<' <<< "$$PYDEPS"

lint: .venv/bin/mypy
	'$<' -- .

fmt: .venv/bin/mypy
	.venv/bin/isort --profile=black --gitignore -- .
	.venv/bin/black --extend-exclude pack -- .
