`csp-bot` is a framework for building command-driven chat bots that run against one or more chat platforms at once.

It is composed of two major components:

- Engine: [csp](https://github.com/point72/csp) and [csp-gateway](https://github.com/point72/csp-gateway), a streaming, complex event processor core and corresponding application framework
- Configuration: [ccflow](https://github.com/point72/ccflow), a [Pydantic](https://docs.pydantic.dev/latest/)/[Hydra](https://hydra.cc) based extensible, composeable dependency injection and configuration framework

Messages, users, and channels are unified across platforms by [chatom](https://github.com/Point72/chatom), so a single bot and its commands work the same on Slack, Symphony, Discord, and Telegram.

## Running your first bot

Let's run a Slack bot.
First, follow the [csp-adapter-slack setup](https://github.com/point72/csp-adapter-slack/wiki/Setup) to create a bot named "CSP Bot".
That gives you two tokens: an *app token* and a *bot token*.

> [!WARNING]
>
> Be sure to avoid committing tokens for any backend into a repository.

Provide the tokens through the environment and start the bot:

```bash
export SLACK_BOT_TOKEN=xoxb-...
export SLACK_APP_TOKEN=xapp-...

csp-bot-start +gateway=slack
```

`csp-bot` uses `ccflow` and `hydra` for configuration, so the command line is composed of config selections rather than flags.
`+gateway=slack` selects the pre-canned Slack gateway; see [Configuration](Configuration) for the full picture.

Message your bot, and by default it replies with a help menu of all available commands:

<img src="https://github.com/Point72/csp-bot/blob/main/docs/img/example_slack_chat.png?raw=true" alt="Message to bot with a response of all commands" />

## Running against multiple backends

The same bot can connect to several platforms simultaneously.
Add backends by listing them — no per-combination config required:

```bash
csp-bot-start +gateway=bot +backend='[slack,telegram]'
```

See [Configuration](Configuration) for pre-canned combinations and how to capture your selection in a file.

## Where to go next

- [Installation](Installation) — install `csp-bot` and the backend adapters you need.
- [Configuration](Configuration) — select backends and customize the gateway.
- [Backends](Backends) — supported platforms, credentials, and feature support.
- [Commands](Commands) — the built-in commands.
- [Writing Commands](Writing-Commands) — add your own commands.
