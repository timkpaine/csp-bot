from csp import Struct
from pydantic import BaseModel

__all__ = (
    "SlackAdapterConfig",
    "SlackAdapterManager",
    "SlackMessage",
    "mention_user_slack",
)

# reexport
try:
    from csp_adapter_slack import SlackAdapterConfig, SlackAdapterManager, SlackMessage, mention_user as mention_user_slack
except ImportError:

    class SlackAdapterConfig(BaseModel):
        pass

    SlackAdapterManager = None

    class SlackMessage(Struct):
        _ignore: str = ""

    mention_user_slack = lambda x: x  # noqa: E731
