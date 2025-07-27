<a href="https://github.com/point72/csp-bot">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://github.com/point72/csp-bot/raw/main/docs/img/logo-name-dark.png?raw=true">
    <img alt="csp-bot logo, overlapping blue speech bubbles" src="https://github.com/point72/csp-bot/raw/main/docs/img/logo-name.png?raw=true" width="400">
  </picture>
</a>

<br/>

[![Build Status](https://github.com/point72/csp-bot/actions/workflows/build.yaml/badge.svg?branch=main&event=push)](https://github.com/point72/csp-bot/actions/workflows/build.yaml)
[![codecov](https://codecov.io/gh/point72/csp-bot/branch/main/graph/badge.svg)](https://codecov.io/gh/point72/csp-bot)
[![GitHub issues](https://img.shields.io/github/issues/point72/csp-bot.svg)](https://github.com/point72/csp-bot/issues)
[![PyPI](https://img.shields.io/pypi/l/csp-bot.svg)](https://pypi.python.org/pypi/csp-bot)
[![PyPI](https://img.shields.io/pypi/v/csp-bot.svg)](https://pypi.python.org/pypi/csp-bot)

## Features

`csp-bot` is a framework for building chat bots.
It is built on [csp](https://github.com/point72/csp), [csp-gateway](https://github.com/point72/csp-gateway), and [ccflow](https://github.com/point72/ccflow)

`csp-bot` makes it easy to build extensible command-driven bots, and has some key features:

- connect to multiple backend chat platforms from the same instance
- register custom commands across backends
- create scheduled commands
- create asynchronous commands
- tag users
- redirect commands across rooms/channels
- and more!

For a detailed overview and examples, see our [Documentation](https://github.com/Point72/csp-bot/wiki/Overview).

Community-supported commands can be found in the [csp-bot-commands](https://github.com/csp-community/csp-bot-commands) project.

## Installation

Install with `pip`:

```bash
pip install csp csp-bot
```

Install with `conda`

```bash
conda install csp csp-bot -c conda-forge
```

## License

This software is licensed under the Apache 2.0 license. See the [LICENSE](https://github.com/Point72/csp-bot/blob/main/LICENSE) file for details.
