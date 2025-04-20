`csp-bot` is a framework for building chat applications.

It is is composed of two major components:

- Engine: [csp](https://github.com/point72/csp) and [csp-gateway](https://github.com/point72/csp-gateway), a streaming, complex event processor core and corresponding application framework
- Configuration: [ccflow](https://github.com/point72/ccflow), a [Pydantic](https://docs.pydantic.dev/latest/)/[Hydra](https://hydra.cc) based extensible, composeable dependency injection and configuration framework

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Running the bot](#running-the-bot)
- [Available Commands](#available-commands)
- [Writing commands](#writing-commands)
- [Backend Feature Matrix](#backend-feature-matrix)
- [Response Formatting](#response-formatting)

## Running the bot

Let's start with a simple Slack bot.
Before we can run the `csp-bot` framework, we need to setup a bot on Slack.
We can follow the documentation on [csp-adapter-slack](https://github.com/point72/csp-adapter-slack/wiki/Setup) using bot name "CSP Bot".

At the end of this setup, we should have two tokens: an "app token" and a "bot token".
Put these in files `.slack_app_token` and `.slack_bot_token`, respectively.

> [!WARNING]
>
> Be sure to avoid committing any tokens for any backends in public repos.

Now we can run our bot.
`csp-bot` uses `ccflow` and `hydra` for configuration, so this syntax might look a little different from CLIs you are used to.
See [Configuration](Configuration) for more information.

```bash
csp-bot-start +gateway=slack +bot_name="CSP Bot" +app_token=.slack_app_token +bot_token=.slack_bot_token
```

Now you can message your bot, and by default it should reply with a help menu of all available commands:

<img src="https://github.com/Point72/csp-bot/blob/main/docs/img/example_slack_chat.png?raw=true" alt="Message to bot with a response of all commands" />

## Available Commands

One of the main goals of `csp-bot` is to allow for extremely easy extension.
The framework comes with a small number of example commands, but makes it easy to extend.
Because backend chat platforms use their own custom command registration and syntax, we adopt an IRC-like `/`-initiated command syntax.
On most platforms, this means to interact with the bot means to tag the bot and provide a command after:

```raw
@CSP Bot /help
```

| Name     | Command     | Description                                                                   |
| :------- | :---------- | :---------------------------------------------------------------------------- |
| Help     | `/help`     | Displays a list of all commands and their help text                           |
| Echo     | `/echo`     | Echos text                                                                    |
| Schedule | `/schedule` | Schedules a command to be run repeatedly, as an example of command scheduling |

Commands can have their own extra arguments, and most commands can be redirected to another channel by appending `/channel <channel name>`.
Community supported commands can be found at [csp-community/csp-bot-commands](https://github.com/csp-community/csp-bot-commands)

## Writing commands

Commands have a simple Python structure.
Here is an example command that replies "hello" to the initiating user.

```python
from typing import Type
from csp_bot.structs import BotCommand, Message
from csp_bot.commands import ReplyToOtherCommand, BaseCommandModel, BaseCommand, mention_user


class HelloCommand(ReplyToOtherCommand):
    def command(self) -> str:
        return "hello"

    def name(self) -> str:
        return "Hello"

    def help(self) -> str:
        return "Say hello to the tagged users. Syntax: /hello [user tags]"

    def execute(self, command: BotCommand) -> Message:
        author = mention_user(command.source.id, command.backend)
        target = [mention_user(user.id, command.backend) for user in command.targets]
        message = f"{author} says hello to {' '.join(target)}!"
        return Message(
            msg=message,
            channel=command.channel,
            backend=command.backend,
        )


class HelloCommandModel(BaseCommandModel):
    command: Type[BaseCommand] = HelloCommand
```

To select commands, including custom commands, follow the documentation in [Configuration](Configuration).
For example, with a Slack bot and the above command in `hello.py`:

**my_bot_config/slack_with_hello.yaml**

```yaml
# @package _global_
defaults:
  - /gateway: slack
  - _self_

bot_name: CSP Bot
app_token: .slack_app_token
bot_token: .slack_bot_token

gateway:
  _target_: csp_bot.Gateway
  modules:
    - /modules/bot
  commands:
    # Selecting a builtin command
    - /commands/help
    # Adding a custom command/s
    - _target_: hello.HelloCommandModel
```

And run with:

```bash
csp-bot-start --config-dir=my_bot_config +bot=slack_with_hello
```

## Backend Feature Matrix

| Backend  | Repo                                                                                      | Official / Community Supported | Public Room | Private Room | User-iniated IM | Non user-initiated IM | Threads | Reactions | Attachments |
| :------- | :---------------------------------------------------------------------------------------- | :----------------------------- | :---------- | :----------- | :-------------- | :-------------------- | :------ | :-------- | :---------- |
| Slack    | [point72/csp-adapter-slack](https://github.com/point72/csp-adapter-slack)                 | Official                       | X           | X            | X               |                       | X       | X         |             |
| Symphony | [point72/csp-adapter-symphony](https://github.com/point72/csp-adapter-symphony)           | Official                       | X           | X            | X               |                       |         |           |             |
| Discord  | [csp-community/csp-adapter-discord](https://github.com/csp-community/csp-adapter-discord) | Community                      | X           | X            | X               |                       | X       | X         |             |

## Response Formatting

Response formatting varies wildly between backends, and it can be quite difficult to produce nicely-formatted results.
We are working on a convenience layer to make this easier.

| Backend  | Format           | Tables | Images |
| :------- | :--------------- | :----- | :----- |
| Slack    | Minimal Markdown | No     | Yes    |
| Symphony | Custom HTML      | Yes    | Yes    |
| Discord  | Minimal Markdown | No     | Yes    |
