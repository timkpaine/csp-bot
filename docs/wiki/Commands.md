`csp-bot` ships a small set of built-in commands and makes it easy to add your own.

Because chat platforms each have their own command registration and syntax, `csp-bot` adopts an IRC-like `/`-initiated command syntax.
On most platforms you interact with the bot by tagging it and then giving a command:

```raw
@CSP Bot /help
```

Most commands accept their own arguments, and many can be redirected to another channel by appending `/channel <channel name>`.

## Built-in commands

| Name     | Command     | Description                                                    |
| :------- | :---------- | :------------------------------------------------------------- |
| Help     | `/help`     | Get help with bot commands. Syntax: `/help [command]`          |
| Echo     | `/echo`     | Echo a message. Syntax: `/echo <message> [/channel <channel>]` |
| Schedule | `/schedule` | Schedule a command to run later or on a cron schedule          |
| Status   | `/status`   | Display system status. Syntax: `/status [/channel <channel>]`  |

Which commands a bot exposes is controlled by configuration; see [Configuration](Configuration).

## More commands

Community-supported commands live in [csp-community/csp-bot-commands](https://github.com/csp-community/csp-bot-commands).
To write your own, see [Writing Commands](Writing-Commands).
