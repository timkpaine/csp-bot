Configuration for `csp-bot` classes is driven by [`ccflow`](https://github.com/Point72/ccflow).
`ccflow` leverages [Pydantic](https://docs.pydantic.dev/latest/) for type validation, and combines it with [Hydra](https://hydra.cc/) / [OmegaConf](https://omegaconf.readthedocs.io/en/2.3_branch/) for config-driven initialization.
The [`ccflow` examples](https://github.com/Point72/ccflow/wiki/First-Steps) provide a nice overview of its functionality.

In the context of `csp-bot`, this means that we can control commands, backends, and their respective configuration, all from a convenient and extensible set of yaml files.

Here is an example of a yaml-based configuration for the standard Slack-based chatbot:

**example/slack.yaml**

```yaml
# @package _global_
defaults:
  - /gateway: slack
  - _self_

bot_name: CSP Bot
app_token: .slack_app_token
bot_token: .slack_bot_token

# csp-bot-start --config-dir=example +bot=slack
```

This configuration:

- Inherits from a builtin configuration called `slack`
- Sets the bot name to `CSP Bot`
- Expects `app_token` and `bot_token` files called `.slack_app_token` and `.slack_bot_token`, respectively

> [!NOTE]
>
> We didn't need to create a local yaml file, but its convenient to do so.
> Instead, we could have used the [hydra override syntax](https://hydra.cc/docs/advanced/override_grammar/basic/) to provide these from the command line:
> `csp-bot-start +gateway=slack +bot_name="CSP Bot" +app_token=.slack_app_token +bot_token=.slack_bot_token`

Hydra allows for easy unioning of configs, which is what we do here.
To see the full picture, let's take a look at the builtin configuration `slack`

```yaml
# @package _global_
defaults:
  - _self_

bot_name: ???
app_token: ???
bot_token: ???

modules:
  bot:
    _target_: csp_bot.Bot
    config:
      _target_: csp_bot.BotConfig
      slack_config:
        _target_: csp_bot.SlackConfig
        bot_name: ${bot_name}
        adapter_config:
          _target_: csp_bot.SlackAdapterConfig
          app_token: ${app_token}
          bot_token: ${bot_token}

hydra:
  job:
    name: csp-bot-slack[${bot_name}]
```

The `???` show that these fields should be overridden in other configs, which is exactly what we do in our `example/slack.yaml`.
We also see that the bot instance is configured with a `SlackConfig`.

For each backend supported, this is just a wrapper around the backend adapter's configuration:

- [Discord Adapter Config](https://github.com/timkpaine/csp-adapter-discord/wiki/Setup)
- [Slack Adapter Config](https://github.com/Point72/csp-adapter-slack/wiki/Setup)
- [Symphony Adapter Config](https://github.com/Point72/csp-adapter-symphony/wiki/Setup)

By default, we provide a few builtinn configurations

- Slack (Hydra: `/gateway: slack`)
- Symphony (Hydra: `/gateway: symphony`)
- Discord: (Hydra: `/gateway: discord`)
- Slack+Discord (Hydra: `/gateway: mixed`)
- Slack+Symphony+Discord (Hydra: `/gateway: all`)

You can extend these configs, or use them as the basis for your own custom config.
All can be founnd in-source in [csp_bot/config/gateway](https://github.com/Point72/csp-bot/tree/main/csp_bot/config/gateway).
