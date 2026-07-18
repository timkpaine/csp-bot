"""Command execution engine supporting four function signatures.

Handles sync functions, async functions, sync generators, and async
generators uniformly. The caller gets back a list of response items
(Message, FormattedMessage, str, or None) regardless of which
signature the command used.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import threading
from typing import Any, List, Optional, Union

from chatom import Message
from chatom.base.attachment import Attachment, AttachmentType, Image as BaseImage
from chatom.format import FormattedMessage
from chatom.format.attachment import FormattedAttachment, FormattedImage

from csp_bot.structs import BotCommand

log = logging.getLogger(__name__)

# Module-level async event loop running in a background thread.
# Lazily initialised on first use.
_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_thread: Optional[threading.Thread] = None
_loop_lock = threading.Lock()


def _get_event_loop() -> asyncio.AbstractEventLoop:
    """Get or create the shared background event loop."""
    global _loop, _loop_thread
    with _loop_lock:
        if _loop is None or _loop.is_closed():
            _loop = asyncio.new_event_loop()
            _loop_thread = threading.Thread(
                target=_loop.run_forever,
                name="csp-bot-async-loop",
                daemon=True,
            )
            _loop_thread.start()
    return _loop


def _extract_attachments(fm: FormattedMessage) -> list:
    """Extract base Attachment objects from a FormattedMessage.

    Converts FormattedAttachment/FormattedImage from both the content list
    and the attachments list into chatom base Attachment/Image objects
    suitable for Message.attachments.
    """
    result = []
    for node in fm.content:
        if isinstance(node, FormattedImage):
            result.append(
                BaseImage(
                    url=node.url,
                    data=node.data,
                    filename=node.filename,
                    alt_text=node.alt_text,
                    content_type=node.content_type or "image/png",
                    size=node.size if hasattr(node, "size") else None,
                    width=node.width,
                    height=node.height,
                    attachment_type=AttachmentType.IMAGE,
                )
            )
        elif isinstance(node, FormattedAttachment):
            att_type = Attachment.from_content_type(node.content_type) if node.content_type else AttachmentType.FILE
            result.append(
                Attachment(
                    filename=node.filename,
                    url=node.url,
                    data=node.data,
                    size=node.size,
                    content_type=node.content_type,
                    attachment_type=att_type,
                )
            )
    for fa in fm.attachments:
        att_type = Attachment.from_content_type(fa.content_type) if fa.content_type else AttachmentType.FILE
        result.append(
            Attachment(
                filename=fa.filename,
                url=fa.url,
                data=fa.data,
                size=fa.size,
                content_type=fa.content_type,
                attachment_type=att_type,
            )
        )
    return result


def _coerce_response(item: Any, backend: str) -> Optional[Union[Message, BotCommand]]:
    """Coerce a command return value into a chatom Message.

    Accepts:
        - None → None
        - BotCommand → pass-through
        - str → Message(content=str)
        - Message → pass-through (ensure metadata.backend set)
        - FormattedMessage → Message with rendered content + formatted_content

    Returns:
        A chatom Message, BotCommand, or None.
    """
    if item is None:
        return None

    if isinstance(item, BotCommand):
        return item

    if isinstance(item, Message):
        if item.metadata is None:
            item.metadata = {}
        if not item.metadata.get("backend"):
            item.metadata["backend"] = backend
        return item

    if isinstance(item, FormattedMessage):
        rendered = item.render_for(backend)
        attachments = _extract_attachments(item)
        msg = Message(
            content=rendered,
            attachments=attachments,
            metadata={"backend": backend, "formatted": item},
        )
        return msg

    if isinstance(item, str):
        return Message(
            content=item,
            metadata={"backend": backend},
        )

    # Unknown type — try str()
    log.warning(f"Command returned unexpected type {type(item)}, converting to str")
    return Message(
        content=str(item),
        metadata={"backend": backend},
    )


def execute_command_func(
    fn: Any,
    ctx: Any,
    timeout: float = 60.0,
) -> List[Optional[Union[Message, BotCommand]]]:
    """Execute a command callable and return a list of Messages.

    Detects the function signature and dispatches accordingly:
    - sync function → call directly, wrap single result
    - async function → run in background loop, wrap single result
    - sync generator → drain, collect all yielded items
    - async generator → drain in background loop, collect all

    Args:
        fn: The callable (function, bound method, generator, etc.)
        ctx: The CommandContext to pass.
        timeout: Timeout in seconds for async operations and generators.

    Returns:
        List of Messages/BotCommands.
    """
    backend = getattr(ctx, "backend", "")

    if inspect.isasyncgenfunction(fn):
        return _run_async_generator(fn, ctx, backend, timeout)
    elif inspect.isgeneratorfunction(fn):
        return _run_sync_generator(fn, ctx, backend, timeout)
    elif inspect.iscoroutinefunction(fn):
        return _run_async_function(fn, ctx, backend, timeout)
    else:
        return _run_sync_function(fn, ctx, backend)


def _run_sync_function(fn: Any, ctx: Any, backend: str) -> List[Optional[Union[Message, BotCommand]]]:
    """Execute a plain sync function."""
    try:
        result = fn(ctx)
        return [_coerce_response(result, backend)]
    except Exception:
        log.exception("Error executing sync command")
        raise


def _run_async_function(
    fn: Any,
    ctx: Any,
    backend: str,
    timeout: float,
) -> List[Optional[Union[Message, BotCommand]]]:
    """Execute an async function in the background event loop."""
    loop = _get_event_loop()
    try:
        future = asyncio.run_coroutine_threadsafe(fn(ctx), loop)
        result = future.result(timeout=timeout)
        return [_coerce_response(result, backend)]
    except asyncio.TimeoutError:
        log.error(f"Async command timed out after {timeout}s")
        raise
    except Exception:
        log.exception("Error executing async command")
        raise


def _run_sync_generator(
    fn: Any,
    ctx: Any,
    backend: str,
    timeout: float,
) -> List[Optional[Union[Message, BotCommand]]]:
    """Drain a sync generator until it yields None sentinel."""
    results: List[Optional[Union[Message, BotCommand]]] = []
    try:
        gen = fn(ctx)
        for item in gen:
            if item is None:
                break
            results.append(_coerce_response(item, backend))
    except GeneratorExit:
        pass
    except Exception:
        log.exception("Error in generator command")
        raise
    return results


async def _drain_async_gen(
    fn: Any,
    ctx: Any,
    backend: str,
) -> List[Optional[Union[Message, BotCommand]]]:
    """Async helper to drain an async generator until None sentinel."""
    results: List[Optional[Union[Message, BotCommand]]] = []
    async for item in fn(ctx):
        if item is None:
            break
        results.append(_coerce_response(item, backend))
    return results


def _run_async_generator(
    fn: Any,
    ctx: Any,
    backend: str,
    timeout: float,
) -> List[Optional[Union[Message, BotCommand]]]:
    """Drain an async generator in the background event loop."""
    loop = _get_event_loop()
    try:
        future = asyncio.run_coroutine_threadsafe(
            _drain_async_gen(fn, ctx, backend),
            loop,
        )
        return future.result(timeout=timeout)
    except asyncio.TimeoutError:
        log.error(f"Async generator command timed out after {timeout}s")
        raise
    except Exception:
        log.exception("Error in async generator command")
        raise
