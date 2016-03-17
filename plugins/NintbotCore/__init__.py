import traceback
from NintbotForDiscord.Enums import EventTypes
from NintbotForDiscord.Plugin import BasePlugin
from NintbotForDiscord.Permissions import create_match_any_permission_group, Permission
from NintbotForDiscord.Permissions.Special import Owner
from NintbotForDiscord.Permissions.Text import ManageMessages
from discord.errors import HTTPException, NotFound
from discord import ChannelType, Status, Game
import os
import json
import re

__author__ = 'Riley Flynn (nint8835)'

INFO_STRING = """```Nintbot version {}
Developed by nint8835
Currently connected to {} servers, with {} channels ({} text, {} voice) and {} users ({} of which are online).
{} plugins currently installed.```"""


class Plugin(BasePlugin):
    def __init__(self, bot_instance, plugin_data, folder):
        super(Plugin, self).__init__(bot_instance, plugin_data, folder)
        self.admin = create_match_any_permission_group([Owner(self.bot), ManageMessages()])
        self.bot.register_handler(EventTypes.CommandSent, self.on_command, self)
        self.bot.register_handler(EventTypes.OnReady, self.on_ready, self)

        self.bot.CommandRegistry.register_command("invite",
                                                  "Makes the bot join a server using an invite link.",
                                                  Permission(),
                                                  plugin_data)
        self.bot.CommandRegistry.register_command("info",
                                                  "Gets general information about the bot.",
                                                  Permission(),
                                                  plugin_data)
        self.bot.CommandRegistry.register_command("debug",
                                                  "Runs Python code to test features.",
                                                  Owner(self.bot),
                                                  plugin_data)
        self.bot.CommandRegistry.register_command("purge",
                                                  "Purges all messages for a user.",
                                                  self.admin,
                                                  plugin_data)
        self.bot.CommandRegistry.register_command("private_messages",
                                                  "Checks the private messages the bot has received.",
                                                  self.admin,
                                                  plugin_data)
        self.bot.CommandRegistry.register_command("plugins",
                                                  "Views the currently installed plugins.",
                                                  Permission(),
                                                  plugin_data)
        self.bot.CommandRegistry.register_command("purgebot",
                                                  "Deletes all of the bot's messages from the channel.",
                                                  self.admin,
                                                  plugin_data)
        self.bot.CommandRegistry.register_command("regexpurge",
                                                  "Deletes messages filtered using a regular expression.",
                                                  self.admin,
                                                  plugin_data)
        self.bot.CommandRegistry.register_command("stop",
                                                  "Stops the bot.",
                                                  self.admin,
                                                  plugin_data)

        with open(os.path.join(folder, "config.json")) as f:
            self.config = json.load(f)

    def member_is_admin(self, member):
        try:
            for role in member.roles:
                if role.permissions.manage_messages:
                    return True
        except:
            pass
        if member.id == self.config["owner_id"]:
            return True

        return False

    def get_all_channels(self):
        channels = []
        for server in self.bot.servers:
            channels += server.channels
        return channels

    def get_all_text_channels(self):
        channels = []
        for server in self.bot.servers:
            channels += [channel for channel in server.channels if channel.type == ChannelType.text]
        return channels

    def get_all_voice_channels(self):
        channels = []
        for server in self.bot.servers:
            channels += [channel for channel in server.channels if channel.type == ChannelType.voice]
        return channels

    def get_all_users(self):
        users = []
        for server in self.bot.servers:
            for user in server.members:
                if not any([user.id == i.id for i in users]):
                    users.append(user)
        return users

    def get_all_online_users(self):
        users = []
        for user in self.get_all_users():
            if user.status == Status.online or user.status == Status.idle:
                users.append(user)
        return users

    def get_all_roles(self):
        roles = []
        for server in self.bot.servers:
            for role in server.roles:
                roles.append(role)
        return roles

    async def on_command(self, args):
        if args["command_args"][0] == "invite":
            await self.command_invite(args)

        elif args["command_args"][0] == "info":
            await self.command_info(args)

        elif args["command_args"][0] == "debug":
            await self.command_debug(args)

        elif args["command_args"][0] == "purge":
            await self.command_purge(args)

        elif args["command_args"][0] == "private_messages" and self.admin.has_permission(args["author"]):
            await self.command_private_messages(args)

        elif args["command_args"][0] == "plugins":
            await self.command_plugins(args)

        elif args["command_args"][0] == "purgebot" and self.admin.has_permission(args["author"]):
            await self.command_purgebot(args)

        elif args["command_args"][0] == "regexpurge":
            await self.command_regexpurge(args)

        elif args["command_args"][0] == "stop" and self.admin.has_permission(args["author"]):
            await self.bot.logout()

    async def command_invite(self, args):
        print(args["command_args"][1])
        if args["command_args"][1].startswith("https://discord.gg/"):
            try:
                await self.bot.accept_invite(args["command_args"][1])
            except (NotFound, HTTPException):
                if args["channel"].is_private:
                    if self.config["send_error_feedback_to_private_messages"]:
                        await self.bot.send_message(args["channel"],
                                                    ":no_entry_sign: The invite link you provided is invalid.")
                else:
                    if self.config["send_error_feedback_to_channels"]:
                        await self.bot.send_message(args["channel"],
                                                    ":no_entry_sign: The invite link you provided is invalid.")

    async def command_info(self, args):
        await self.bot.send_message(args["channel"],
                                    INFO_STRING.format(self.bot.VERSION,
                                                       len(self.bot.servers),
                                                       len(self.get_all_channels()),
                                                       len(self.get_all_text_channels()),
                                                       len(self.get_all_voice_channels()),
                                                       len(self.get_all_users()),
                                                       len(self.get_all_online_users()),
                                                       len(self.bot.PluginManager.plugins)))

    async def command_debug(self, args):
        if self.config["enable_debug"] and Owner(self.bot).has_permission(args["author"]):
            try:
                results = eval(" ".join(args["unsplit_args"].split(" ")[1:]))
            except:
                results = traceback.format_exc(5)
            await self.bot.send_message(args["channel"], "```python\n{}```".format(results))

    async def command_purge(self, args):
        if len(args["command_args"]) == 2:
            args["command_args"][2] = 100
        if self.admin.has_permission(args["author"]):
            async for message in self.bot.logs_from(args["channel"], limit = int(args["command_args"][2])):
                if message.author.name == args["command_args"][1]:
                    await self.bot.delete_message(message)
                elif args["command_args"][1] == "ALL":
                    await self.bot.delete_message(message)

    async def command_regexpurge(self, args):
        if len(args["command_args"]) == 2:
            args["command_args"][2] = 100
        if self.admin.has_permission(args["author"]):
            regex = re.compile(args["command_args"][1])
            async for message in self.bot.logs_from(args["channel"], limit = int(args["command_args"][2])):
                if regex.match(message.content):
                    await self.bot.delete_message(message)

    async def command_private_messages(self, args):
        if len(args["command_args"]) == 1:
            message = "```The bot has private messages to or from the following users:\n{}```".format(
                "\n".join([channel.user.name for channel in self.bot.private_channels]))
            await self.bot.send_message(args["channel"], message)
        if len(args["command_args"]) > 1:
            user_name = " ".join(args["command_args"][1:])
            try:
                logs = []
                async for i in self.bot.logs_from([channel for channel in self.bot.private_channels if channel.user.name == user_name][0],limit = 5):
                    logs.append(i)
                await self.bot.send_message(args["channel"],
                                            "```Last 5 private messages with {}\n{}```".format(user_name, "\n".join(
                                                    ["{}: {}".format(log.author.name, log.content) for log in logs])))
            except:
                traceback.print_exc(5)

    async def command_plugins(self, args):
        # HORRIBLE CODE ALERT
        # I'll clean it up later - Riley Flynn, ALWAYS
        # It never gets done
        await self.bot.send_message(args["channel"],
                                    "```Installed plugins:\n{}```".format("\n".join(["{} version {} by {}".format(
                                            plugin["info"]["plugin_name"], plugin["info"]["plugin_version"],
                                            plugin["info"]["plugin_developer"]) for plugin in
                                                                                     self.bot.PluginManager.plugins])))

    async def command_purgebot(self, args):
        async for message in self.bot.logs_from(args["channel"], limit = 100):
            if message.author.id == self.bot.user.id:
                await self.bot.delete_message(message)

    async def on_ready(self, args):
        await self.bot.change_status(game = Game(name = "Nintbot V{}".format(self.bot.VERSION)))
