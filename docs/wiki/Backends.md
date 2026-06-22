`csp-bot` connects to chat platforms through `csp` adapters, wrapped by [`chatom`](https://github.com/Point72/chatom) for a unified message, user, and channel model.
This page is the reference for which backends exist, how to authenticate them, and what each one can do.

## Supported backends

| Backend  | Adapter                                                                                     | Support   |
| :------- | :------------------------------------------------------------------------------------------ | :-------- |
| Slack    | [point72/csp-adapter-slack](https://github.com/point72/csp-adapter-slack)                   | Official  |
| Symphony | [point72/csp-adapter-symphony](https://github.com/point72/csp-adapter-symphony)             | Official  |
| Discord  | [csp-community/csp-adapter-discord](https://github.com/csp-community/csp-adapter-discord)   | Community |
| Telegram | [csp-community/csp-adapter-telegram](https://github.com/csp-community/csp-adapter-telegram) | Community |

The adapters are optional dependencies — install the ones you need:

```bash
pip install csp-adapter-slack csp-adapter-telegram
```

## Credentials

Each backend reads its credentials from environment variables, matching the names used by the built-in `backend` configs.

| Backend  | Environment variables                | `chatom` config field     |
| :------- | :----------------------------------- | :------------------------ |
| Slack    | `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN` | `bot_token`, `app_token`  |
| Discord  | `DISCORD_TOKEN`                      | `token`                   |
| Symphony | `SYMPHONY_BOT_KEY`                   | `bot_private_key_content` |
| Telegram | `TELEGRAM_BOT_TOKEN`                 | `bot_token`               |

To set a field other than the default (for example, a Symphony key on disk rather than in the environment), override it in your own config:

```yaml
# @package modules.bot.config
symphony:
  config:
    bot_private_key_path: /path/to/bot-key.pem
    bot_certificate_path: /path/to/bot-cert.pem
```

For platform-specific setup of tokens and bot accounts, follow the adapter guides:

- [Slack Adapter setup](https://github.com/Point72/csp-adapter-slack/wiki/Setup)
- [Symphony Adapter setup](https://github.com/Point72/csp-adapter-symphony/wiki/Setup)
- [Discord Adapter setup](https://github.com/csp-community/csp-adapter-discord/wiki/Setup)
- [Telegram Adapter](https://github.com/csp-community/csp-adapter-telegram/wiki)

## Feature matrix

| Backend  | Public Room | Private Room | User-initiated IM | Threads | Reactions | Attachments |
| :------- | :---------- | :----------- | :---------------- | :------ | :-------- | :---------- |
| Slack    | X           | X            | X                 | X       | X         |             |
| Symphony | X           | X            | X                 |         |           |             |
| Discord  | X           | X            | X                 | X       | X         |             |
| Telegram | X           | X            | X                 |         |           |             |

## Response formatting

Response formatting varies between backends, and built-in commands render their output in the right dialect for each one.

| Backend  | Format           | Tables | Images |
| :------- | :--------------- | :----- | :----- |
| Slack    | Minimal Markdown | No     | Yes    |
| Symphony | Custom HTML      | Yes    | Yes    |
| Discord  | Minimal Markdown | No     | Yes    |
| Telegram | HTML             | No     | Yes    |
