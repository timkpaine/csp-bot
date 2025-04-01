from csp_bot import Bot, load_config


def test_with_initialize() -> None:
    overrides = ["+gateway=slack", "app_token=xapp-1", "bot_token=xoxb-", "bot_name=DUMMY_BOT_NAME"]
    registry = load_config(overrides=overrides, overwrite=True)
    gateway = registry["gateway"]
    bot_module = None
    for module in gateway.modules:
        if isinstance(module, Bot):
            bot_module = module
            break

    assert bot_module is not None, "Gateway must have `Bot` as a module"
    assert bot_module.config.slack_config.bot_name == "DUMMY_BOT_NAME"

    adapter_config = bot_module.config.slack_config.adapter_config

    assert adapter_config.app_token == "xapp-1"
    assert adapter_config.bot_token == "xoxb-"
