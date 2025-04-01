`csp-bot` is written in Python and Javascript. While prebuilt wheels are provided for end users, it is also straightforward to build `csp-bot` from either the Python [source distribution](https://packaging.python.org/en/latest/specifications/source-distribution-format/) or the GitHub repository.

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Make commands](#make-commands)
- [Prerequisites](#prerequisites)
- [Clone](#clone)
- [Install Python dependencies](#install-python-dependencies)
- [Build](#build)
- [Lint and Autoformat](#lint-and-autoformat)
- [Testing](#testing)

## Make commands

As a convenience, `csp-bot` uses a `Makefile` for commonly used commands. You can print the main available commands by running `make` with no arguments

```bash
> make

build                          build the library
clean                          clean the repository
fix                            run autofixers
install                        install library
lint                           run lints
test                           run the tests
```

## Prerequisites

## Clone

Clone the repo with:

```bash
git clone https://github.com/Point72/csp-bot.git
cd csp-bot
```

## Install Python dependencies

Python build and develop dependencies are specified in the `pyproject.toml`, but you can manually install them:

```bash
make requirements
```

Note that these dependencies would otherwise be installed normally as part of [PEP517](https://peps.python.org/pep-0517/) / [PEP518](https://peps.python.org/pep-0518/).

## Build

Build the python project in the usual manner:

```bash
make build
```

## Lint and Autoformat

`csp-bot` has linting and auto formatting.

| Language | Linter     | Autoformatter | Description |
| :------- | :--------- | :------------ | :---------- |
| Python   | `ruff`     | `ruff`        | Style       |
| Python   | `ruff`     | `ruff`        | Imports     |
| Markdown | `prettier` | `prettier`    | Style       |

**Python Linting**

```bash
make lint
```

**Python Autoformatting**

```bash
make fix
```

**Documentation Linting**

We use `prettier` for our Markdown linting, so follow the above docs.

## Testing

`csp-bot` has Python tests, which can be run via `pytest`.
First, install the Python development dependencies with

```bash
make develop
```

**Python**

```bash
make test
```
