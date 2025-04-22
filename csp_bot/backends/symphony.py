from csp import Struct
from pydantic import BaseModel

__all__ = (
    "SymphonyAdapterConfig",
    "SymphonyAdapter",
    "SymphonyMessage",
    "Presence",
    "mention_user_symphony",
)

# reexport
try:
    from csp_adapter_symphony import SymphonyAdapter, SymphonyAdapterConfig, SymphonyMessage, mention_user as mention_user_symphony
    from csp_adapter_symphony.adapter import Presence
except ImportError:

    class SymphonyAdapterConfig(BaseModel):
        pass

    SymphonyAdapter = None
    Presence = None

    class SymphonyMessage(Struct):
        _ignore: str = ""

    mention_user_symphony = lambda x: x  # noqa: E731
