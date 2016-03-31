import discord
import asyncio
import shlex
import logging

from .Plugin import BasePlugin
from .EventManager import EventManager
from .PluginManager import PluginManager
from .Enums import EventTypes
from .CommandRegistry import CommandRegistry
from .TokenClient import TokenClient
from .Scheduler import Scheduler
from . import __version__

__author__ = 'Riley Flynn (nint8835)'


class Bot(TokenClient):

    def __init__(self, config: dict, loop: asyncio.BaseEventLoop = None):
        super(Bot, self).__init__(loop = loop)
        self.VERSION = __version__
        self.config = config
        self.logger = logging.getLogger("NintbotForDiscord")

        try:
            log_level = getattr(logging, self.config["log_level"])
        except AttributeError:
            log_level = logging.INFO

        logging.basicConfig(format="{%(asctime)s} (%(name)s) [%(levelname)s]: %(message)s",
                            datefmt="%x, %X",
                            level=log_level)
        self.logger.debug("Creating EventManager...")
        self.EventManager = EventManager(self)
        self.logger.debug("Done.")
        self.logger.debug("Creating PluginManager...")
        self.PluginManager = PluginManager(self)
        self.logger.debug("Done.")
        self.logger.debug("Creating CommadRegistry...")
        self.CommandRegistry = CommandRegistry(self)
        self.logger.debug("Done")
        self.logger.debug("Creating Scheduled...")
        self.Scheduler = Scheduler(self)
        self.logger.debug("Done")
        self.logger.debug("Loading plugins...")
        self.PluginManager.load_plugins()
        self.logger.debug("Done.")
        self.logger.debug("Starting bot...")
        logging.getLogger("discord").setLevel(logging.ERROR)
        logging.getLogger("websockets").setLevel(logging.ERROR)
        self.email = self.config["email"]
        self.run(config["token"])

    def register_handler(self, eventtype: EventTypes, handler, plugin: BasePlugin):
        self.EventManager.register_handler(eventtype, handler, plugin)

    async def on_message(self, message: discord.Message):
        await self.log_message(message)
        if message.channel.is_private or message.server.id not in self.config["blacklisted_servers"]:
            await self.EventManager.dispatch_event(EventTypes.Message,
                                                   message = message,
                                                   author = message.author,
                                                   channel = message.channel)
            if message.channel.is_private:
                await self.EventManager.dispatch_event(EventTypes.PrivateMessage,
                                                       message = message,
                                                       author = message.author,
                                                       channel = message.channel)
            else:
                await self.EventManager.dispatch_event(EventTypes.ChannelMessage,
                                                       message = message,
                                                       author = message.author,
                                                       channel = message.channel)

            if message.content.startswith(self.config["command_prefix"]):
                command_str = message.content.lstrip(self.config["command_prefix"])
                try:
                    args = shlex.split(command_str)
                except ValueError:
                    self.logger.warning("Failed to process arguments for message '{}' using shlex, falling back to processing using spaces.".format(message.content))
                    args = command_str.split(" ")
                await self.EventManager.dispatch_event(EventTypes.CommandSent,
                                                       command_args = args,
                                                       unsplit_args = command_str,
                                                       message = message,
                                                       author = message.author,
                                                       channel = message.channel)

    async def on_message_delete(self, message):
        if message.channel.is_private or message.server.id not in self.config["blacklisted_servers"]:
            await self.EventManager.dispatch_event(EventTypes.MessageDeleted,
                                                   message = message,
                                                   author = message.author,
                                                   channel = message.channel)

            if message.channel.is_private:
                await self.EventManager.dispatch_event(EventTypes.PrivateMessageDeleted,
                                                       message = message,
                                                       author = message.author,
                                                       channel = message.channel)

            else:
                await self.EventManager.dispatch_event(EventTypes.ChannelMessageDeleted,
                                                       message = message,
                                                       author = message.author,
                                                       channel = message.channel)

    async def on_message_edit(self, before, after):
        if before.channel.is_private or before.server.id not in self.config["blacklisted_servers"]:
            await self.EventManager.dispatch_event(EventTypes.MessageEdited,
                                                   message_before = before,
                                                   message_after = after,
                                                   author = after.author,
                                                   channel = after.channel)

            if after.channel.is_private:
                await self.EventManager.dispatch_event(EventTypes.PrivateMessageEdited,
                                                       message_before = before,
                                                       message_after = after,
                                                       author = after.author,
                                                       channel = after.channel)

            else:
                await self.EventManager.dispatch_event(EventTypes.PrivateMessageEdited,
                                                       message_before = before,
                                                       message_after = after,
                                                       author = after.author,
                                                       channel = after.channel)

    async def on_channel_delete(self, channel):
        if channel.is_private or channel.server.id not in self.config["blacklisted_servers"]:
            await self.EventManager.dispatch_event(EventTypes.ChannelDeleted,
                                                   channel = channel,
                                                   server = channel.server)

    async def on_channel_create(self, channel):
        if channel.is_private or channel.server.id not in self.config["blacklisted_servers"]:
            if not channel.is_private:
                await self.EventManager.dispatch_event(EventTypes.ChannelCreated,
                                                       channel = channel,
                                                       server = channel.server)
            else:
                await self.EventManager.dispatch_event(EventTypes.ChannelCreated,
                                                       channel = channel)

    async def on_channel_update(self, before, after):
        if before.is_private or before.server.id not in self.config["blacklisted_servers"]:
            await self.EventManager.dispatch_event(EventTypes.ChannelUpdated,
                                                   channel_before = before,
                                                   channel_after = after,
                                                   server = after.server)

    async def on_member_join(self, member):
        if member.server.id not in self.config["blacklisted_servers"]:
            await self.EventManager.dispatch_event(EventTypes.MemberJoined,
                                                   member = member,
                                                   server = member.server)

    async def on_member_left(self, member):
        if member.server.id not in self.config["blacklisted_servers"]:
            await self.EventManager.dispatch_event(EventTypes.MemberLeft,
                                                   member = member,
                                                   server = member.server)

    async def on_member_update(self, before, after):
        if before.server.id not in self.config["blacklisted_servers"]:
            await self.EventManager.dispatch_event(EventTypes.MemberUpdated,
                                                   member_before = before,
                                                   member_after = after,
                                                   server = after.server)

    async def on_member_ban(self, member):
        if member.server.id not in self.config["blacklisted_servers"]:
            await self.EventManager.dispatch_event(EventTypes.MemberBanned,
                                                   member = member,
                                                   server = member.server)

    async def on_member_unbanned(self, server, user):
        if server.id not in self.config["blacklisted_servers"]:
            await self.EventManager.dispatch_event(EventTypes.MemberUnbanned,
                                                   server = server,
                                                   user = user)

    async def on_voice_state_update(self, before, after):
        if before.server.id not in self.config["blacklisted_servers"]:
            await self.EventManager.dispatch_event(EventTypes.MemberVoiceStateUpdated,
                                                   member_before = before,
                                                   member_after = after)

    async def on_typing(self, channel, user, when):
        if channel.is_private or channel.server.id not in self.config["blacklisted_servers"]:
            await self.EventManager.dispatch_event(EventTypes.MemberTyping,
                                                   channel = channel,
                                                   user = user,
                                                   when = when)

    async def on_server_join(self, server):
        if server.id not in self.config["blacklisted_servers"]:
            await self.EventManager.dispatch_event(EventTypes.ServerJoined,
                                                   server = server)

    async def on_server_remove(self, server):
        if server.id not in self.config["blacklisted_servers"]:
            await self.EventManager.dispatch_event(EventTypes.ServerLeft,
                                                   server = server)

    async def on_server_update(self, before, after):
        if before.id not in self.config["blacklisted_servers"]:
            await self.EventManager.dispatch_event(EventTypes.ServerUpdated,
                                                   server_before = before,
                                                   server_after = after)

    async def on_server_available(self, server):
        if server.id not in self.config["blacklisted_servers"]:
            await self.EventManager.dispatch_event(EventTypes.ServerAvailable,
                                                   server = server)

    async def on_server_unavailable(self, server):
        if server.id not in self.config["blacklisted_servers"]:
            await self.EventManager.dispatch_event(EventTypes.ServerUnavailable,
                                                   server = server)

    async def on_server_role_create(self, server, role):
        if server.id not in self.config["blacklisted_servers"]:
            await self.EventManager.dispatch_event(EventTypes.ServerRoleCreated,
                                                   server = server,
                                                   role = role)

    async def on_server_role_delete(self, server, role):
        if server.id not in self.config["blacklisted_servers"]:
            await self.EventManager.dispatch_event(EventTypes.ServerRoleDeleted,
                                                   server = server,
                                                   role = role)

    async def on_server_role_update(self, before, after):
        if before.id not in self.config["blacklisted_servers"]:
            await self.EventManager.dispatch_event(EventTypes.ServerRoleUpdated,
                                                   role_before = before,
                                                   role_after = after,
                                                   server = [server for server in self.servers if after in server.roles][0])

    async def on_ready(self):
        await self.EventManager.dispatch_event(EventTypes.OnReady)

    async def log_message(self, message):
        self.logger.info("{} ({}): {}".format(message.author.name, message.author.id, message.content))
