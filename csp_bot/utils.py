from typing import Literal
from urllib.parse import urlparse  # quote

from .backends import mention_user_discord, mention_user_slack, mention_user_symphony

__all__ = (
    "is_valid_url",
    "format_with_message_ml",
    "sanitize_message",
    "recursive_format_for_message_ml",
    "mention_user",
    "Backend",
)

Backend = Literal["discord", "slack", "symphony"]


def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def format_with_message_ml(text, to_message_ml: bool = True) -> str:
    """If to_message_ml, we convert to message ml by replacing special sequences of character. Else, we convert from message_ml in the same way"""
    pairs = [
        ("&", "&#38;"),
        ("<", "&lt;"),
        ("${", "&#36;{"),
        ("#{", "&#35;{"),
    ]

    for original, msg_ml_version in pairs:
        if to_message_ml:
            text = text.replace(original, msg_ml_version)
        else:
            text = text.replace(msg_ml_version, original)

    return text


def sanitize_message(text):
    return format_with_message_ml(text, to_message_ml=True)


def recursive_format_for_message_ml(d):
    if isinstance(d, (list, set, tuple)):
        return [recursive_format_for_message_ml(v) for v in d]
    elif isinstance(d, dict):
        return {sanitize_message(str(k)): recursive_format_for_message_ml(v) for k, v in d.items()}
    else:
        return sanitize_message(str(d))


def mention_user(email_or_userid: str = "", backend: Backend = "symphony") -> str:
    if backend == "symphony":
        return mention_user_symphony(email_or_userid)
    elif backend == "slack":
        if not email_or_userid.startswith("@"):
            email_or_userid = f"@{email_or_userid}"
        return mention_user_slack(email_or_userid)
    elif backend == "discord":
        return mention_user_discord(email_or_userid)
    else:
        raise NotImplementedError(f"Unsupported backend: {backend}")
