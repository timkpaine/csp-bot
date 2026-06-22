Commands are the unit of behaviour in `csp-bot`.
This guide walks through writing a custom command and wiring it into a running bot.

## Write the command

A command subclasses one of the reply base classes and implements four methods: `command()`, `name()`, `help()`, and `execute()`.
The `execute()` method receives a `BotCommand` and returns a `chatom` `Message` (or `None` for no reply).

This example greets the users tagged in the message:

```python
from typing import Optional, Type

from chatom import Message

from csp_bot.commands import BaseCommand, BaseCommandModel, ReplyToOtherCommand
from csp_bot.structs import BotCommand
from csp_bot.utils import mention_users


class HelloCommand(ReplyToOtherCommand):
    def command(self) -> str:
        return "hello"

    def name(self) -> str:
        return "Hello"

    def help(self) -> str:
        return "Say hello to the tagged users. Syntax: /hello [user tags]"

    def execute(self, command: BotCommand) -> Optional[Message]:
        if not command.targets:
            return None
        mentions = mention_users(
            [t.to_chatom_user() for t in command.targets],
            command.backend,
        )
        return Message(
            content=f"Hello {mentions}!",
            channel=command.channel,
            metadata={"backend": command.backend},
        )


class HelloCommandModel(BaseCommandModel):
    command: Type[BaseCommand] = HelloCommand
```

`mention_users()` renders each tagged user in the right format for the backend the message came from, so the same command works across every platform.

## Register the command

Commands are selected by configuration.
Put `hello.py` next to a bot config and list the command alongside the built-ins:

**my_bot/bot/slack.yaml**

```yaml
# @package _global_
defaults:
  - /gateway: slack
  - _self_

bot_name: CSP Bot

gateway:
  commands:
    - /commands/help
    - /commands/echo
    - _target_: hello.HelloCommandModel
```

Then start the bot, pointing Hydra at your config directory so it can import `hello.py`:

```bash
csp-bot-start --config-dir=my_bot +bot=slack
```

Tagging the bot with `/hello @someone` now replies with a greeting.

## Choosing a base class

The reply base class fixes how many users a command may tag and who gets mentioned:

| Base class             | Tags       | Mentions           |
| :--------------------- | :--------- | :----------------- |
| `ReplyCommand`         | none       | replies in-channel |
| `ReplyToAuthorCommand` | one        | the message author |
| `ReplyToOtherCommand`  | one        | the tagged user    |
| `ReplyToAllCommand`    | any number | all tagged users   |
| `NoResponseCommand`    | none       | no reply           |
