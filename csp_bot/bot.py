import re
import threading
import time
from csv import reader
from datetime import datetime, timedelta
from io import StringIO
from logging import getLogger
from types import MappingProxyType
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import csp
from bs4 import BeautifulSoup, Tag
from croniter import croniter
from csp import Outputs, ts
from pydantic import PrivateAttr

from .backends import (
    DiscordAdapterManager,
    DiscordMessage as RawDiscordMessage,
    Presence,
    SlackAdapterManager,
    SlackMessage as RawSlackMessage,
    SymphonyAdapter,
    SymphonyMessage as RawSymphonyMessage,
)
from .bot_config import BotConfig
from .commands import (
    BaseCommand,
    BaseCommandModel,
    HelpCommand,
    ScheduleCommand,
    StatusCommand,
)
from .gateway import GatewayChannels, GatewayModule
from .structs import (
    BotCommand,
    CommandVariant,
    Message,
    User,
)
from .utils import Backend

log = getLogger(__name__)

SLACK_ENTITY_REGEX = re.compile("<@.+?>")
DISCORD_ENTITY_REGEX = re.compile("<@.+?>")

__all__ = ("Bot",)


class Bot(GatewayModule):
    config: BotConfig

    # FIXME do via hydra
    # commands: List[BaseCommandModel]
    _command_models: List[BaseCommandModel] = PrivateAttr(default_factory=list)
    _commands: Dict[str, BaseCommand] = PrivateAttr(default_factory=dict)

    _configs: Dict[Backend, dict] = PrivateAttr(default_factory=dict)  # convenience for lookups by name
    _adapters: Dict[Backend, object] = PrivateAttr(default_factory=dict)
    _scheduled = PrivateAttr(default_factory=dict)
    _authorized_users: Dict[Backend, Set[str]] = PrivateAttr(default_factory=dict)
    _thread: Optional[threading.Thread] = PrivateAttr(None)
    _lock: threading.Lock = PrivateAttr(default_factory=threading.Lock)

    def connect(self, channels: GatewayChannels) -> None:
        if self.config.discord_config:
            if DiscordAdapterManager is None:
                raise ImportError("Discord adapter not installed. Please install csp-adapter-discord.")
            self._configs["discord"] = self.config.discord_config
            self._adapters["discord"] = DiscordAdapterManager(self.config.discord_config.adapter_config)
        if self.config.slack_config:
            if SlackAdapterManager is None:
                raise ImportError("Slack adapter not installed. Please install csp-adapter-slack.")
            self._configs["slack"] = self.config.slack_config
            self._adapters["slack"] = SlackAdapterManager(self.config.slack_config.adapter_config)
        if self.config.symphony_config:
            if SymphonyAdapter is None:
                raise ImportError("Symphony adapter not installed. Please install csp-adapter-symphony.")
            self._configs["symphony"] = self.config.symphony_config
            self._adapters["symphony"] = SymphonyAdapter(self.config.symphony_config.adapter_config)

        # Get raw messages from adapter
        messages_in = csp.null_ts(Message)
        for adapter_type, adapter in self._adapters.items():
            unrolled_raw_msgs = csp.unroll(adapter.subscribe(**self._configs[adapter_type].adapter_kwargs()))
            processed_messages = self.raw_message_to_message(adapter_type, unrolled_raw_msgs)
            messages_in = csp.flatten([messages_in, processed_messages])
            # messages.append(self.raw_message_to_message(adapter_type, csp.unroll(adapter.subscribe(**self._configs[adapter_type].adapter_kwargs()))))

        # messages_in = csp.flatten(messages)

        # Echo to channel
        channels.set_channel(GatewayChannels.messages_in, messages_in)

        # Extract bot commands from raw feed
        new_commands_and_authorization_rejections = self.message_to_bot_commands(messages_in)
        bot_commands = csp.unroll(new_commands_and_authorization_rejections.bot_commands)
        channels.set_channel(GatewayChannels.commands, bot_commands)

        # Process bot commands and get responses/secondary commands
        messages_and_commands = self.bot_command_handler(channels.get_channel(GatewayChannels.commands))
        messages_out = csp.flatten([csp.unroll(messages_and_commands.messages), new_commands_and_authorization_rejections.unauthorized_message])

        # Echo to channel
        channels.set_channel(GatewayChannels.messages_out, messages_out)

        # loopback commands to command channels
        bot_commands_to_loopback = csp.unroll(messages_and_commands.commands)
        channels.set_channel(GatewayChannels.commands, bot_commands_to_loopback)

        # Process messages back to raw messages
        raw_messages_out = self.message_to_raw_message(messages_out)

        # And publish back to adapter
        for adapter_type, adapter in self._adapters.items():
            adapter.publish(msg=getattr(raw_messages_out, adapter_type))

        # TODO generalize presence
        if self._configs.get("symphony") and self._configs["symphony"].set_presence_seconds:
            self._adapters["symphony"].publish_presence(
                csp.timer(timedelta(seconds=self._configs["symphony"].set_presence_seconds), Presence.AVAILABLE)
            )

        # Update user access
        if self._configs.get("discord") and self._configs["discord"].user_access_channels:
            log.warning("Slack user access is not fully implemented")
        if self._configs.get("slack") and self._configs["slack"].user_access_channels:
            log.warning("Slack user access is not fully implemented")
        if self._configs.get("symphony") and self._configs["symphony"].user_access_channels:
            # We want the first query to happen before starting the graph.
            # This way, if the query fails for some reason
            # we will raise and not start up the csp.graph,
            # avoiding any issue of unauthorized user access.
            self._update_user_access("symphony")
            if self._configs["symphony"].query_user_access_channels_seconds:
                self._thread = threading.Thread(target=self._update_user_access_loop, args=("symphony",), daemon=True)
                self._thread.start()

    def _update_user_access(self, adapter_type: str):
        if adapter_type != "symphony":
            raise NotImplementedError("Only Symphony is supported for user access for now")
        users: Set[str] = set()
        for channel_name in self._configs[adapter_type].user_access_channels:
            user_list = self._configs[adapter_type].adapter_config.get_user_ids_in_room(room_name=channel_name)
            users.update(user_list)
        with self._lock:
            self._authorized_users["symphony"] = users

    def _update_user_access_loop(self, adapter_type: str):
        if adapter_type != "symphony":
            raise NotImplementedError("Only Symphony is supported for user access for now")
        while True:
            # We start with the sleep first since our first call occurs
            # outside of this loop
            time.sleep(self._configs[adapter_type].query_user_access_channels_seconds)
            try:
                self._update_user_access("symphony'")
            except Exception:
                log.exception(f"Error attempting to update user access for {adapter_type}")

    def load_commands(self, command_models: List[BaseCommandModel]):
        for command_model in command_models:
            try:
                # Instantiate to ensure completion
                command = command_model.command()
            except TypeError as e:
                log.critical(f"Incomplete command type - ensure you've implemented all abstract methods: {command_model.command}")
                raise e

            # Register by name
            command_str = command.command()
            if command_str in self._commands:
                raise Exception(f"Command already registered: {command_str}\n\t{command}\n\t{self._commands[command_str]}")

            # keep track of model and command
            self._commands[command_str] = command
            # don't really care about this as its just a bridge to hydra
            self._command_models.append(command_model)

    #############
    # CSP Nodes #
    #############
    @csp.node
    def raw_message_to_message(self, adapter_type: str, raw_message: ts[Any]) -> ts[Message]:
        return Message.from_raw_message(adapter_type, raw_message)

    @csp.node
    def message_to_raw_message(self, message: ts[Message]) -> Outputs(
        discord=ts[RawDiscordMessage], slack=ts[RawSlackMessage], symphony=ts[RawSymphonyMessage]
    ):
        if message.backend == "symphony":
            csp.output(symphony=message.to_raw_message("symphony"))
        elif message.backend == "slack":
            csp.output(slack=message.to_raw_message("slack"))
        elif message.backend == "discord":
            csp.output(discord=message.to_raw_message("discord"))
        else:
            raise NotImplementedError(f"Message type not supported: {message.backend}")

    @csp.node
    def message_to_bot_commands(self, message: ts[Message]) -> Outputs(bot_commands=ts[[BotCommand]], unauthorized_message=ts[Message]):
        if csp.ticked(message):
            is_msg_to_bot = False
            try:
                is_msg_to_bot, channel, text, entities = self.is_msg_to_bot(message)
                if not is_msg_to_bot:
                    # We intentionally avoid logging the message itself
                    # for security concerns.
                    log.info("Ignoring message (not to bot)")
                else:
                    if not self.is_authorized(message):
                        if self._configs[message.backend].unauthorized_msg:
                            channel = message.channel if message.channel != "IM" else message.user
                            unauthorized_message = Message(
                                msg=self._configs[message.backend].unauthorized_msg, channel=channel, source=message.backend
                            )
                            csp.output(unauthorized_message=unauthorized_message)
                    else:
                        bot_commands = self.extract_bot_commands(message, channel, text, entities)
                        if bot_commands:
                            if not isinstance(bot_commands, list):
                                bot_commands = [bot_commands]
                            csp.output(bot_commands=bot_commands)
            except KeyboardInterrupt:
                raise
            except Exception:
                # Ignore
                if is_msg_to_bot:
                    log.exception(f"Error processing message: {message}")
                else:
                    log.exception("Error processing message (not to bot)")

    @csp.node
    def bot_command_handler(self, command: ts[BotCommand]) -> Outputs(messages=ts[[Message]], commands=ts[[BotCommand]]):
        with csp.alarms():
            a_scheduled_command: ts[BotCommand] = csp.alarm(BotCommand)
            a_ratelimit: ts[bool] = csp.alarm(bool)
        with csp.state():
            s_buffer = []
            s_buffer_last = []
            s_commands_to_process = []

        with csp.start():
            csp.schedule_alarm(a_ratelimit, timedelta(seconds=self.config.ratelimit_seconds), True)

        if csp.ticked(a_scheduled_command):
            # check if its still scheduled, or if its been cancelled
            if a_scheduled_command.id in self._scheduled:
                # if its still scheduled, then lets run it
                s_commands_to_process.append(a_scheduled_command)

                # reschedule if its an interval command
                if hasattr(a_scheduled_command, "schedule"):
                    now = csp.now()
                    next_time = croniter(a_scheduled_command.schedule, now).get_next(datetime)
                    if next_time >= now:
                        self._scheduled[a_scheduled_command.id] = a_scheduled_command
                        csp.schedule_alarm(a_scheduled_command, next_time, a_scheduled_command)
                    else:
                        log.warning(f"Scheduled time in past: current-time: {now} schedule time: {next_time}")
                else:
                    # remove from schedule if it was a delayed command
                    self._scheduled.pop(a_scheduled_command.id, None)

        if csp.ticked(command):
            now = csp.now()
            if hasattr(command, "delay") and command.delay >= now:
                self._scheduled[command.id] = command
                csp.schedule_alarm(a_scheduled_command, command.delay, command)
            elif hasattr(command, "schedule"):
                next_time = croniter(command.schedule, now).get_next(datetime)
                if next_time >= now:
                    self._scheduled[command.id] = command
                    csp.schedule_alarm(a_scheduled_command, next_time, command)
                else:
                    log.warning(f"Scheduled time in past: current-time: {now} schedule time: {next_time}")
            else:
                s_commands_to_process.append(command)

        if csp.ticked(command) or csp.ticked(a_scheduled_command):
            commands_to_process_next_cycle = []
            for command_to_process in s_commands_to_process:
                # this returns either another bot command, or a message
                command_or_message_or_none = self.run_bot_command(command_to_process)

                if command_or_message_or_none:
                    # promote to list
                    if not isinstance(command_or_message_or_none, list):
                        command_or_message_or_none = [command_or_message_or_none]

                    for command_or_message in command_or_message_or_none:
                        if isinstance(command_or_message, Message):
                            # if its a message, emit it
                            s_buffer.append(command_or_message)
                        elif isinstance(command_or_message, BotCommand):
                            # reprocess it next cycle
                            commands_to_process_next_cycle.append(command_or_message)
            if commands_to_process_next_cycle:
                csp.output(commands=commands_to_process_next_cycle)

            # reinitialize state
            s_commands_to_process = []

        if csp.ticked(a_ratelimit):
            if len(s_buffer) > 0:
                # deduplicate messages to avoid spamming
                # first, remove duplicates directly
                s_buffer = set(s_buffer)
                # now intersect with previous tick to avoid spam
                s_buffer = s_buffer - set(s_buffer_last)
                # convert back to list
                s_buffer = list(s_buffer)

                # output
                csp.output(messages=s_buffer)

                # store this round in _last
                s_buffer_last = s_buffer.copy()

                # and reset for next
                s_buffer = []

            csp.schedule_alarm(a_ratelimit, timedelta(seconds=self.config.ratelimit_seconds), True)

    ##############
    # Processors #
    ##############
    def bot_commands_from_command_string(self, tokens: List[str], message: Message, channel: str, entity_map: Dict[str, Tuple[str, str]] = None):
        # Check malformed, this should never happen
        if len(tokens) == 0:
            # TODO malformed
            log.critical(f"Malformed command: {message}")
            return

        command = tokens[0].replace("/", "", 1)
        if command not in self._commands:
            # TODO print help w/ unrecognized command
            log.critical(f"Unrecognized/unregistered command: {command} - {message}")
            return

        # now interrogate the command string to align
        # with these important bits
        command_args = []
        target_tags = []
        target_channel = ""
        skip_next = False
        for i, token in enumerate(tokens):
            # this is the command, skip
            if i == 0:
                continue

            # this has been processed in a prior step
            if skip_next:
                skip_next = False
                continue

            # TODO: remove, deprecated
            if token == "/room":
                # /room should be followed by room name
                # room name with special characters must be surrounded with double quotes
                # ROOM NAMES WITH DOUBLE QUOTES IN THEM ARE NOT ALLOWED
                if i + 1 >= len(tokens) or tokens[i + 1].startswith("@"):
                    # malformed
                    log.critical(f"Malformed room name: {message}")
                else:
                    # grab the channel
                    target_channel = tokens[i + 1]
                    skip_next = True
                    continue

            if token == "/channel":
                # /channel should be followed by channel name
                # channel name with special characters must be surrounded with double quotes
                # CHANNEL NAMES WITH DOUBLE QUOTES IN THEM ARE NOT ALLOWED
                if i + 1 >= len(tokens) or tokens[i + 1].startswith("@"):
                    # malformed
                    log.critical(f"Malformed channel name: {message}")
                else:
                    # grab the channel
                    target_channel = tokens[i + 1]
                    skip_next = True
                    continue

            # entity detection
            if entity_map and token in entity_map:
                # symphony and slack handle tagging opposite
                if message.backend == "symphony":
                    name, id = entity_map[token]
                elif message.backend == "slack":
                    id, name = entity_map[token]
                elif message.backend == "discord":
                    name, id = entity_map[token]
                target_tags.append(User(name=name, id=id, backend=message.backend))
                continue

            command_args.append(token)

        # if target room hasnt been set, reply in room message was sent
        if target_channel == "":
            target_channel = channel
        return command, command_args, target_channel, target_tags

    def _get_bot_tag(self, backend: str) -> str:
        # TODO: normalize across adapters
        if backend == "slack":
            return self._adapters[backend]._get_user_from_name(self._configs[backend].bot_name)
        return self._configs[backend].bot_name

    def extract_bot_commands(self, message: Message, channel: str, text: str, entities: List[Tag]) -> Optional[Union[List[BotCommand], BotCommand]]:
        try:
            # allow @<bot name> /<cmd>
            if (
                text.startswith("/")
                or text.startswith(f"@{self._get_bot_tag(message.backend)} /")
                or text.startswith(f"<@{self._get_bot_tag(message.backend)}> /")
            ):
                # most names and tags will have spaces, so before we tokenize lets replace those
                entity_map: Dict[str, Tuple[str, str]] = {}
                # entity_map is mapping of entity placeholder to name and user id
                # e.g. @CSP Bot /command @Tim Paine
                #      ENTITY_0 -> ("@CSP Bot", "123456789")
                #      ENTITY_1 -> ("@Tim Paine", "987654321")
                for i, entity in enumerate(entities):
                    entity_placeholder = f"ENTITY_{i}"

                    if message.backend == "symphony":
                        text = text.replace(entity, entity_placeholder, 1)
                    elif message.backend == "slack":
                        text = text.replace(f"<{entity}>", entity_placeholder, 1)
                    elif message.backend == "discord":
                        text = text.replace(f"<{entity}>", entity_placeholder, 1)

                    # NOTE: in symphony
                    entity_map[entity_placeholder] = (entity, message.tags[i])

                tokens = next(reader(StringIO(text), delimiter=" ", quotechar='"', skipinitialspace=True))

                if tokens[0] in entity_map and entity_map[tokens[0]][0] == f"@{self._get_bot_tag(message.backend)}":
                    # remove initial bot directive
                    tokens = tokens[1:]

                ret = self.bot_commands_from_command_string(tokens, message, channel, entity_map)
                if not ret:
                    return
                command, command_args, target_channel, target_tags = ret

                # determine the command's supported backends and skip if unsupported
                backends: Backend = self._commands[command].backends()
                if backends and message.backend not in backends:
                    log.warning(f"Command {command} not supported on backend {message.backend}")
                    return

                variant: CommandVariant = self._commands[command].kind()

                # determine the command variant
                variant: CommandVariant = self._commands[command].kind()

                # parse out the required info from the command
                command_instance = BotCommand(
                    command=command,
                    args=tuple(command_args),
                    source=User(name=message.user, id=message.user_id, backend=message.backend),
                    targets=tuple(target_tags),
                    channel=target_channel,
                    backend=message.backend,
                    variant=variant,
                    message=message,
                )

                command_runner = self._commands[command]

                # TODO generalize by interrogating the command signature
                if isinstance(command_runner, ScheduleCommand):
                    # Special command, gets access to schedule of commands
                    return command_runner.preexecute(command_instance, self._scheduled, self)
                elif isinstance(command_runner, StatusCommand):
                    # Special command, gets access to status of commands
                    return command_runner.preexecute(command_instance, self)
                return command_runner.preexecute(command_instance)
            else:
                log.info(f"Defaulting to help command from message to bot with no command: {message}")
                command_runner = self._commands["help"]
                command_instance = BotCommand(
                    command="help",
                    args=tuple(),
                    source=User(name=message.user, id=message.user_id, backend=message.backend),
                    channel=channel,
                    backend=message.backend,
                    variant=command_runner.kind(),
                    message=message,
                )
                return command_runner.preexecute(command_instance)

        except KeyboardInterrupt:
            raise
        except Exception:
            # Ignore
            # NOTE: message itself may be malformed!
            try:
                log.exception(f"Error processing message: {message}")
            except Exception:
                log.exception("Error processing message (could not log message itself)")

    def run_bot_command(self, command_instance: BotCommand) -> Optional[Union[List[Message], List[BotCommand]]]:
        # grab the important bits of the command
        command_runner: BaseCommand = self._commands[command_instance.command]
        # num_recipients: int = command_runner.num_recipients()

        # execute the command to get a response
        try:
            if isinstance(command_runner, HelpCommand):
                # Special command, gets access to all other commands
                responses = command_runner.execute(command_instance, MappingProxyType(self._commands))
            elif isinstance(command_runner, ScheduleCommand):
                # Special command, gets access to schedule of commands
                responses = command_runner.execute(command_instance, self._scheduled)
            else:
                # normal command
                responses = command_runner.execute(command_instance)
        except BaseException:
            log.exception(f"Error executing command for msg: {command_instance.message}")
            return

        if not isinstance(responses, list):
            # convert to list
            responses = [responses]

        # remap all IM rooms to the user id so that bot
        # can DM correctly
        if responses:
            for response in responses:
                if isinstance(response, Message):
                    # replace "IM" convenience with actual user
                    if response.channel == "IM":
                        response.channel = command_instance.message.user
            return responses

    ###########
    # Helpers #
    ###########
    @staticmethod
    def parse_msg(msg: Message):
        if msg.backend == "symphony":
            soup = BeautifulSoup(msg.msg, features="html.parser")
            text = soup.get_text()
            entities = [e.text for e in soup.find_all("span", class_="entity")]

            # clean up a bit
            text = text.strip()
            while "  " in text:
                text = text.replace("  ", " ")
        elif msg.backend == "slack":
            text = msg.msg
            # NOTE: tag is like `<@USER_ID>` so prune to match canonical `@USER_ID`
            entities = [m[1:-1] for m in SLACK_ENTITY_REGEX.findall(text)]
        elif msg.backend == "discord":
            text = msg.msg
            # NOTE: tag is like `<@USER_ID>` so prune to match canonical `@USER_ID`
            entities = [m[1:-1] for m in DISCORD_ENTITY_REGEX.findall(text)]
        return text, entities

    def is_msg_to_bot(self, msg: Message) -> Tuple[bool, str, str, List[Tag]]:
        text, entities = Bot.parse_msg(msg)

        # remove content that is in the reply
        if msg.backend == "symphony":
            text = text.rsplit("_———————————", 1)[-1]

        # NOTE: return is:
        # is_msg_to_bot, channel, text, entities
        # if its a DM to bot, the channel will be the user's name
        # if the bot is not tagged, first argument is false so ignore second arg
        bot_name = self._configs[msg.backend].bot_name
        bot_tag_to_find = self._get_bot_tag(msg.backend)
        bot_tag = f"@{bot_tag_to_find}" in text

        if bot_tag:
            return True, msg.channel, text, entities
        elif msg.channel == "IM" and msg.user != bot_name:
            return True, msg.user, text, entities
        return False, "", text, entities

    def is_authorized(self, msg: Message) -> bool:
        if msg.backend == "symphony":
            if not self.config.symphony_config.user_access_channels:
                return True
            with self._lock:
                res = msg.user_id in self._authorized_users[msg.backend]
            return res
        elif msg.backend == "slack":
            # TODO implement
            return True
        elif msg.backend == "discord":
            # TODO implement
            return True
