from NintbotForDiscord.Enums import EventTypes
from NintbotForDiscord.Events import CommandSentEvent
from NintbotForDiscord.Permissions.General import ManageServer, ManageRoles, Administrator
from NintbotForDiscord.Plugin import BasePlugin
from NintbotForDiscord.Permissions import create_match_any_permission_group, Permission
from NintbotForDiscord.Permissions.Special import Owner
from NintbotForDiscord.Permissions.Text import ManageMessages

from discord import ChannelType, Status, Game

import traceback
import math
import os
import json
import re
import time
import psutil

from NintbotForDiscord.ScheduledTask import GameUpdateScheduledTask

__author__ = 'Riley Flynn (nint8835)'

INFO_STRING = """```Nintbot version {}
Developed by nint8835
Currently connected to {} servers, with {} channels ({} text, {} voice) and {} users ({} of which are online).
{} plugins currently installed.
The interpreter is currently using {}MB of ram.```"""

USER_INFO_STRING = """```Username: {}
ID: {}
Discriminator: {}
Avatar: {}
Created: {}
Roles: {}
```"""

SERVER_INFO_STRING = """```Server name: {}
Roles:
    {}
Region: {}
Members: {}
Channels:
    {}
Icon: {}
ID: {}
Owner: {}
Created at: {}
```"""


def ram_usage_in_mb():
    process = psutil.Process(os.getpid())
    mem = process.memory_info()[0] / float(2 ** 20)
    return mem


class Plugin(BasePlugin):
    def __init__(self, manifest, bot_instance):
        super(Plugin, self).__init__(manifest, bot_instance)
        self.started_time = 0
        self.admin = create_match_any_permission_group([Owner(self.bot), ManageRoles()])
        self.superadmin = create_match_any_permission_group([Owner(self.bot), Administrator()])
        self.bot.register_handler(EventTypes.CLIENT_READY, self.on_ready, self)

        self.bot.CommandRegistry.register_command("info",
                                                  "Gets general information about the bot.",
                                                  Permission(),
                                                  self,
                                                  self.command_info)
        self.bot.CommandRegistry.register_command("debug",
                                                  "Runs Python code to test features.",
                                                  Owner(self.bot),
                                                  self,
                                                  self.command_debug)
        self.bot.CommandRegistry.register_command("plugins",
                                                  "Views the currently installed plugins.",
                                                  Permission(),
                                                  self,
                                                  self.command_plugins)
        self.bot.CommandRegistry.register_command("stop",
                                                  "Stops the bot.",
                                                  Owner(self.bot),
                                                  self,
                                                  self.command_stop)
        self.bot.CommandRegistry.register_command("uptime",
                                                  "Displays the bot's uptime.",
                                                  Permission(),
                                                  self,
                                                  self.command_uptime)
        self.bot.CommandRegistry.register_command("commands",
                                                  "Displays what commands you have access to.",
                                                  Permission(),
                                                  self,
                                                  self.command_commands)
        self.bot.CommandRegistry.register_command("userinfo",
                                                  "Displays info about a certain user.",
                                                  Permission(),
                                                  self,
                                                  self.command_userinfo)
        self.bot.CommandRegistry.register_command("invitebot",
                                                  "Posts the invite link for the bot.",
                                                  Permission(),
                                                  self,
                                                  self.command_invitelink)
        self.bot.CommandRegistry.register_command("server",
                                                  "Gets information for the server.",
                                                  self.superadmin,
                                                  self,
                                                  self.command_server)
        self.bot.CommandRegistry.register_command("resetgame",
                                                  "Resets the currently played game to the default one.",
                                                  Owner(self.bot),
                                                  self,
                                                  self.command_resetgame)
        self.bot.CommandRegistry.register_command("users",
                                                  "Gets the total user count for the server.",
                                                  Permission(),
                                                  self,
                                                  self.command_users)

        with open(os.path.join(self.manifest["path"], "config.json")) as f:
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

    async def command_info(self, args):
        await args.channel.send(INFO_STRING.format(self.bot.VERSION,
                                                   len(self.bot.servers),
                                                   len(self.get_all_channels()),
                                                   len(self.get_all_text_channels()),
                                                   len(self.get_all_voice_channels()),
                                                   len(self.get_all_users()),
                                                   len(self.get_all_online_users()),
                                                   len(self.bot.PluginManager.get_all_manifests()),
                                                   ram_usage_in_mb()))

    async def command_debug(self, args):
        if self.config["enable_debug"] and Owner(self.bot).has_permission(args["author"]):
            try:
                results = eval(args["content"].split(self.bot.config["command_prefix"]+"debug ")[1])
            except:
                results = traceback.format_exc(5)
            await args.channel.send("```python\n{}```".format(results))

    async def command_plugins(self, args: CommandSentEvent):
        message = "```\n"
        for manifest in self.bot.PluginManager.get_all_manifests():
            message += f"{manifest.get('name', 'Unnamed Plugin')}\n"
            message += f"\tVersion: {manifest.get('version', 'Unspecified version')}\n"
            message += f"\tDeveloper: {manifest.get('developer', 'Unspecified developer')}\n"
            message += f"\tDependencies: {', '.join(manifest.get('dependencies', []))}\n"
            message += f"\tPath: {manifest.get('path')}\n"
        message += "```"
        await args.channel.send(message)

    async def command_uptime(self, args):
        time_diff = time.time() - self.started_time
        minutes, seconds = divmod(time_diff, 60)
        minutes = int(math.floor(minutes))
        seconds = int(math.floor(seconds))
        hours, minutes = divmod(minutes, 60)
        hours = int(math.floor(hours))
        minutes = int(math.floor(minutes))
        days, hours = divmod(hours, 24)
        hours = int(math.floor(hours))
        days = int(math.floor(days))
        await args.channel.send("The bot has been up for {} days, {} hours, {} minutes, and {} seconds.".format(days, hours, minutes, seconds))

    async def command_commands(self, args):
        message_str = ""
        for command in self.bot.CommandRegistry.get_available_commands_for_user(args["author"]):
            if message_str == "":
                message_str += "```"
            if len(message_str) + len("{}{}: {}\n".format(self.bot.config["command_prefix"], command["command"], command["description"])) >= 1997:
                await args.author.send(message_str + "```")
                message_str = "```"
            message_str += "{}{}: {}\n".format(self.bot.config["command_prefix"], command["command"], command["description"])
        if message_str != "":
            await args.author.send(message_str + "```")

    async def command_userinfo(self, args):
        if len(args["command_args"]) >= 2:
            users = [user for user in args["channel"].server.members if user.name == " ".join(args["command_args"][1:])]
            for user in users:
                args.channel.send(USER_INFO_STRING.format(user.name,
                                                          user.id,
                                                          user.discriminator,
                                                          user.avatar_url,
                                                          user.created_at,
                                                          ", ".join([role.name for role in user.roles if role.name != "@everyone"])))

    async def command_stop(self, args):
        await self.bot.logout()

    async def command_invitelink(self, args):
        await args.channel.send("Invite the bot to your server using the following link: https://discordapp.com/oauth2/authorize?&client_id={}&scope=bot".format(self.bot.config["app_id"]))

    async def command_server(self, args):
        await args.channel.send(SERVER_INFO_STRING.format(args["channel"].server.name,
                                                          "\n\t".join([role.name for role in args["channel"].server.roles if role.name != "@everyone"]),
                                                          args["channel"].server.region,
                                                          args["channel"].server.member_count,
                                                          "\n\t".join(["{} ({})".format(channel.name, channel.type) for channel in args["channel"].server.channels]),
                                                          args["channel"].server.icon_url,
                                                          args["channel"].server.id,
                                                          args["channel"].server.owner.name,
                                                          args["channel"].server.created_at))

    async def command_resetgame(self, args):
        self.bot.Scheduler.add_task(GameUpdateScheduledTask("Nintbot V{}".format(self.bot.VERSION), self.bot, 10),
                                    self)

    async def on_ready(self, args):
        self.bot.Scheduler.add_task(GameUpdateScheduledTask("Nintbot V{}".format(self.bot.VERSION), self.bot, 10),
                                    self)
        self.started_time = time.time()

    async def command_users(self, args):
        if not args["channel"].is_private:
            await args.channel.send("There are {} members in this server.".format(args["channel"].server.member_count))
